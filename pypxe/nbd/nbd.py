import logging
import socket
import struct
import threading
import sys
import os
import io
import writes
from pypxe import helpers

class NBD:
    def __init__(self, **server_settings):
        self.bd = server_settings.get('block_device', '')
        self.netboot_directory = server_settings.get('netboot_directory', '.')
        self.write = server_settings.get('write', False) # write?
        self.cow = server_settings.get('cow', True) # COW is the safe default
        self.in_mem = server_settings.get('in_mem', False)
        self.copy_to_ram = server_settings.get('copy_to_ram', False)
        self.ip = server_settings.get('ip', '0.0.0.0')
        self.port = int(server_settings.get('port', 10809))
        self.mode_debug = server_settings.get('mode_debug', False) # debug mode
        self.mode_verbose = server_settings.get('mode_verbose', False) # debug mode
        self.logger =  server_settings.get('logger', None)

        # setup logger
        if self.logger == None:
            self.logger = logging.getLogger('NBD')
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s %(name)s [%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        if self.mode_debug:
            self.logger.setLevel(logging.DEBUG)
        elif self.mode_verbose:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.WARN)

        self.logger.debug('NOTICE: NBD server started in debug mode. NBD server is using the following:')
        self.logger.info('Server IP: {0}'.format(self.ip))
        self.logger.info('Server Port: {0}'.format(self.port))
        self.logger.info('Block Device: {0}'.format(self.bd))
        self.logger.info('Block Device Writes: {0}'.format(self.write))
        self.logger.info('Block Write Method: {0} ({1})'.format("Copy-On-Write" if self.cow else 'File', 'Memory' if self.in_mem else 'Disk'))

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))
        self.sock.listen(4)

        # if we have COW on, we write elsewhere so we don't need write ability
        self.openbd = open(helpers.normalize_path(self.netboot_directory, self.bd), 'r+b' if self.write and not self.cow else 'rb')

        # go to EOF
        self.openbd.seek(0, 2)

        # we need this when clients mount us
        self.bdsize = self.openbd.tell()

        # go back to start
        self.openbd.seek(0)

        if self.copy_to_ram and self.cow:
            self.logger.info('Starting copying {0} to RAM'.format(self.bd))
            self.openbd = io.BytesIO(self.openbd.read())
            self.logger.info('Finished copying {0} to RAM'.format(self.bd))

    def send_reply(self, conn, addr, code, data):
        '''Send a reply with magic, only used for error codes.'''
        reply = struct.pack('!Q', 0x3e889045565a9)
        reply += struct.pack('!I', code)
        reply += struct.pack('!I', len(data))
        reply += data
        conn.send(reply)

    def handshake(self, conn, addr):
        '''Initiate the connection, server sends first.'''
        # mostly taken from https://github.com/yoe/nbd/blob/master/nbd-server.c
        conn.send('NBDMAGIC')

        # 0x49484156454F5054
        conn.send('IHAVEOPT')

        # NBD_FLAG_FIXED_NEWSTYLE | NBD_FLAG_NO_ZEROES
        conn.send(struct.pack('!H', 3))
        [cflags] = struct.unpack('!I', conn.recv(4))
        op = 0

        while op != 1: # NBD_OPT_EXPORT_NAME
            [magic] = struct.unpack("!Q", conn.recv(8))
            [op] = struct.unpack("!I", conn.recv(4))
            if op != 1:
                # NBD_REP_ERR_UNSUP
                self.send_reply(conn, addr, 2 ** 31 + 1, '')
        [namelen] = struct.unpack('!I', conn.recv(4))
        name = conn.recv(namelen)

        if name != self.bd:
            self.logger.debug('Blockdevice names do not match {0} != {1}'.format(self.bd, name))
            conn.close()
            return 1

        self.logger.info('Received request for {0} from {1}'.format(name, addr))
        exportinfo = struct.pack('!Q', self.bdsize) # size of export
        flags = (0 if self.write else 2) # readonly?
        exportinfo += struct.pack('!H', flags)
        exportinfo += chr(0) * (0 if (cflags & 2) else 124)
        conn.send(exportinfo)

    def handle_client(self, conn, addr, seeklock):
        '''Handle all client actions, R/W/Disconnect'''
        ret = self.handshake(conn, addr)
        if ret: return # client did something wrong, so we closed them
        FS = writes.write(self.cow, self.in_mem)(addr, self.openbd, self.logger, seeklock)

        while True:
            conn.recv(4)
            try:
                [opcode, handle, offset, length] = struct.unpack('!IQQI', conn.recv(24, socket.MSG_WAITALL))
            except struct.error:
                # client sent us something malformed, or gave up (module not loaded)
                continue

            if opcode not in (0, 1, 2):
                # NBD_REP_ERR_UNSUP
                self.send_reply(conn, addr, 2 ** 31 + 1, '')
                continue

            if opcode == 0: # READ
                data = FS.read(offset, length)
                response = struct.pack('!I', 0x67446698)
                response += struct.pack('!I', 0) # error
                response += struct.pack('!Q', handle)
                conn.send(response)
                conn.send(data)

            elif opcode == 1: # WRITE
                # WAIT because if there's any lag at all we don't get the whole
                # thing, we don't write the whole thing, and then we break
                # trying to parse the rest of the data
                data = conn.recv(length, socket.MSG_WAITALL)
                FS.write(offset, data)
                response = struct.pack('!I', 0x67446698)
                response += struct.pack('!I', 0) # error
                response += struct.pack('!Q', handle)
                conn.send(response)

            elif opcode == 2: # DISCONNECT
                conn.close() # delete COW diff
                self.logger.info('{0} disconnected'.format(addr))
                return

    def listen(self):
        '''This method is the main loop that listens for requests.'''
        seeklock = threading.Lock()
        cowfiles = []

        while True:
            try:
                conn, addr = self.sock.accept()

                # split off on a thread, allows us to handle multiple clients
                dispatch = threading.Thread(target = self.handle_client, args = (conn, addr, seeklock))

                # clients don't necessarily close the TCP connection
                # so we use this to kill the program on ctrl-c
                dispatch.daemon = True
                dispatch.start()

                # this is for the cleanup at the end. Will need clarifying
                # if MemCOW
                if self.cow and not self.in_mem:
                    cowfiles.append('PyPXE_NBD_COW_{addr[0]}_{addr[1]}'.format(addr = addr))
            except KeyboardInterrupt:
                map(os.remove, cowfiles)
                return
