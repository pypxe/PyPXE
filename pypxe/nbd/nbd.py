import logging
import socket
import struct
import threading
import sys
import os
import io
import writes

class NBD:
    def __init__(self, **serverSettings):
        self.bd = serverSettings.get('blockdevice', '')
        self.write = serverSettings.get('write', False) #w?
        self.cow = serverSettings.get('cow', True) # COW is the safe default
        self.inmem = serverSettings.get('inmem', False)
        self.copytoram = serverSettings.get('copytoram', False)
        self.ip = serverSettings.get('ip', '0.0.0.0')
        self.port = serverSettings.get('port', 10809)
        self.mode_debug = serverSettings.get('mode_debug', False) #debug mode
        self.logger =  serverSettings.get('logger', None)

        # setup logger
        if self.logger == None:
            self.logger = logging.getLogger("NBD")
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s %(name)s [%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.logger.debug('NOTICE: NBD server started in debug mode. NBD server is using the following:')
        self.logger.debug('  NBD Server IP: {}'.format(self.ip))
        self.logger.debug('  NBD Server Port: {}'.format(self.port))
        self.logger.debug('  NBD Block Device: {}'.format(self.bd))
        self.logger.debug('  NBD Block Device Writes: {}'.format(self.write))
        self.logger.debug('  NBD Block Write Method: {} ({})'.format("Copy-On-Write" if self.cow else "File", "Memory" if self.inmem else "Disk"))

        if self.mode_debug:
            self.logger.setLevel(logging.DEBUG)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))
        self.sock.listen(4)

        # if we have COW on, we write elsewhere so we don't need write ability
        self.openbd = open(self.bd, 'r+b' if self.write and not self.cow else 'rb')
        # go to EOF
        self.openbd.seek(0, 2)
        # we need this when clients mount us
        self.bdsize = self.openbd.tell()
        # go back to start
        self.openbd.seek(0)
        if self.copytoram and self.cow:
            self.logger.info('Starting copying %s to RAM', self.bd)
            self.openbd = io.BytesIO(self.openbd.read())
            self.logger.info('Finished copying %s to RAM', self.bd)


    def sendreply(self, conn, addr, code, data):
        '''Send a reply with magic. only used for error codes'''
        reply = struct.pack("!Q", 0x3e889045565a9)
        reply += struct.pack("!I", code)
        reply += struct.pack("!I", len(data))
        reply += data
        conn.send(reply)

    def handshake(self, conn, addr):
        '''Initiate the connection. Server sends first.'''
        # Mostly taken from https://github.com/yoe/nbd/blob/master/nbd-server.c
        conn.send('NBDMAGIC')
        # 0x49484156454F5054
        conn.send('IHAVEOPT')
        # NBD_FLAG_FIXED_NEWSTYLE | NBD_FLAG_NO_ZEROES
        conn.send(struct.pack("!H", 3))

        [cflags] = struct.unpack("!I", conn.recv(4))

        op = 0
        while op != 1: # NBD_OPT_EXPORT_NAME
            [magic] = struct.unpack("!Q", conn.recv(8))
            [op] = struct.unpack("!I", conn.recv(4))
            if op != 1:
                # NBD_REP_ERR_UNSUP
                self.sendreply(conn, addr, 2**31+1, '')

        [namelen] = struct.unpack("!I", conn.recv(4))
        name = conn.recv(namelen)
        if name != self.bd:
            conn.close()
            return 1

        self.logger.debug('Received request for %s from %s', name, addr)

        # size of export
        exportinfo = struct.pack('!Q', self.bdsize)
        flags = (0 if self.write else 2) # readonly?
        exportinfo += struct.pack('!H', flags)
        exportinfo += "\x00"*(0 if (cflags&2) else 124)
        conn.send(exportinfo)

    def handleClient(self, conn, addr, seeklock):
        '''Handle all client actions, R/W/Disconnect'''
        ret = self.handshake(conn, addr)
        if ret: return # client did something wrong, so we closed them

        FS = writes.write(self.cow, self.inmem)(addr, self.openbd, self.logger, seeklock)

        while True:
            conn.recv(4)
            [opcode, handle, offset, length] = struct.unpack("!IQQI", conn.recv(24, socket.MSG_WAITALL))
            if opcode not in (0, 1, 2):
                # NBD_REP_ERR_UNSUP
                self.sendreply(conn, addr, 2**31+1, '')
                continue
            if opcode == 0: # READ
                data = FS.read(offset, length)

                response = struct.pack("!I", 0x67446698)
                response += struct.pack("!I", 0) # error
                response += struct.pack("!Q", handle)
                conn.send(response)
                conn.send(data)

            elif opcode == 1: # WRITE
                # WAIT because if there's any lag at all we don't get the whole
                # thing, we don't write the whole thing, and then we break
                # trying to parse the rest of the data
                data = conn.recv(length, socket.MSG_WAITALL)
                FS.write(offset, data)

                response = struct.pack("!I", 0x67446698)
                response += struct.pack("!I", 0) # error
                response += struct.pack("!Q", handle)
                conn.send(response)

            elif opcode == 2: # DISCONNECT
                # delete COW diff
                conn.close()
                self.logger.debug('%s disconnected', addr)
                return

    def listen(self):
        '''This method is the main loop that listens for requests'''
        seeklock = threading.Lock()
        cowfiles = []
        while True:
            try:
                conn, addr = self.sock.accept()
                # Split off on a thread. Allows us to handle multiple clients
                dispatch = threading.Thread(target = self.handleClient, args = (conn, addr, seeklock))
                # clients don't necessarily close the TCP connection
                # so we use this to kill the program on Ctrl-c
                dispatch.daemon = True
                dispatch.start()
                # this is for the cleanup at the end. Will need clarifying
                # if MemCOW
                if self.cow and not self.inmem:
                    cowfiles.append('PyPXE_NBD_COW_%s_%s' % addr)
            except KeyboardInterrupt:
                map(os.remove, cowfiles)
                return
