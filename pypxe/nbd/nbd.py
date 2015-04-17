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


    def handshake(self, conn, addr):
        handshake = 'NBDMAGIC'
        conn.send(handshake)
        # 0x49484156454F5054
        handshake = 'IHAVEOPT'
        # fixed newstyle and nozeros
        handshake += struct.pack("!H", 3)
        conn.send(handshake)

    def exportMount(self, conn, addr):
        [flags] = struct.unpack("!I", conn.recv(4))
        newstyle = flags & 1
        nozero = flags & 2
        # magic
        conn.recv(8)
        [option] = struct.unpack("!I", conn.recv(4))
        if option != 1:
            #Isn't a NBD_OPT_EXPORT_NAME
            conn.close()
            return 1

        [exportlen] = struct.unpack("!I", conn.recv(4))
        export = conn.recv(exportlen)
        if export != self.bd:
            conn.close()
            return 1

        self.logger.debug('Received request for %s from %s', export, addr)

        # size of export
        exportinfo = struct.pack('!Q', self.bdsize)
        flags = 1 # has flags
        flags |= 1 << (self.mode == 'r') # readonly?
        exportinfo += struct.pack('!H', flags)
        exportinfo += "\x00"*(0 if nozero else 124)
        conn.send(exportinfo)

    def handleClient(self, conn, addr):
        self.handshake(conn, addr)
        ret = self.exportMount(conn, addr)
        if ret: return # client did something wrong, so we closed them

        while True:
            # atrocious. but works.
            while not conn.recv(4): pass
            [opcode, handle, offset, length] = struct.unpack("!IQQI", conn.recv(24))
            if opcode not in (0, 1, 2):
                # NBD_REP_ERR_UNSUP
                response = struct.pack("!I", 0x67446698)
                response += struct.pack("!I", opcode)
                response += struct.pack("!I", 2**31 + 1) # NBD_REP_ERR_UNSUP
                response += struct.pack("!I", 0) # length
                conn.send(response)
            if opcode == 0: # READ
                self.openbd.seek(offset)
                data = self.openbd.read(length)
                response = struct.pack("!I", 0x67446698)
                response += struct.pack("!I", 0) # error
                response += struct.pack("!Q", handle)
                response += data
                conn.send(response)
                self.logger.debug('%s read %d bytes from %s', addr, length, hex(offset))
            elif opcode == 1: # WRITE
                data = conn.recv(length)
                self.logger.debug('%s wrote %d bytes from %s', addr, length, hex(offset))
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
