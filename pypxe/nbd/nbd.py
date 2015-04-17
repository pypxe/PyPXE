import logging
import socket
import struct

class NBD:
    def __init__(self, **serverSettings):
        self.bd = serverSettings.get('blockdevice', '')
        self.mode = serverSettings.get('mode', 'r') #r/w
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

        if self.mode_debug:
            self.logger.setLevel(logging.DEBUG)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))
        self.sock.listen(1)

        self.openbd = open(self.bd, 'ra' if self.mode == 'w' else self.mode)
        # go to EOF
        self.openbd.seek(0, 2)
        self.bdsize = self.openbd.tell()
        # go back to start
        self.openbd.seek(0)

        self.logger.debug('NOTICE: NBD server started in debug mode. NBD server is using the following:')
        self.logger.debug('  NBD Server IP: {}'.format(self.ip))
        self.logger.debug('  NBD Server Port: {}'.format(self.port))
        self.logger.debug('  NBD Block Device: {}'.format(self.bd))

    def sendreply(self, conn, addr, code, data):
        reply = struct.pack("!Q", 0x3e889045565a9)
        reply += struct.pack("!I", code)
        reply += struct.pack("!I", len(data))
        reply += data
        conn.send(reply)

    def handshake(self, conn, addr):
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
        flags = int((self.mode == 'r')) # readonly?
        exportinfo += struct.pack('!H', flags)
        exportinfo += "\x00"*(0 if (cflags&2) else 124)
        conn.send(exportinfo)

    def handleClient(self, conn, addr):
        ret = self.handshake(conn, addr)
        if ret: return # client did something wrong, so we closed them

        while True:
            # atrocious. but works. MSG_WAITALL seems non-functional
            while not conn.recv(4): pass
            [opcode, handle, offset, length] = struct.unpack("!IQQI", conn.recv(24))
            if opcode not in (0, 1, 2):
                # NBD_REP_ERR_UNSUP
                self.sendreply(conn, addr, 2**31+1, '')
                continue
            if opcode == 0: # READ
                self.openbd.seek(offset)
                data = self.openbd.read(length)
                response = struct.pack("!I", 0x67446698)
                response += struct.pack("!I", 0) # error
                response += struct.pack("!Q", handle)
                conn.send(response)
                conn.send(data)
                self.logger.debug('%s read %d bytes from %s', addr, length, hex(offset))
            elif opcode == 1: # WRITE
                data = conn.recv(length)
                self.logger.debug('%s wrote %d bytes to %s', addr, length, hex(offset))
                pass
            elif opcode == 2: # DISCONNECT
                conn.close()
                self.logger.debug('%s disconnected', addr)
                return

    def listen(self):
        '''This method is the main loop that listens for requests'''
        while True:
            conn, addr = self.sock.accept()
            # should probably fork these
            self.handleClient(conn, addr)
