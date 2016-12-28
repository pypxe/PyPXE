import rpcbind
import logging
from pypxe import helpers
import socket
import threading
import time
import struct
import hashlib

class RPC(rpcbind.RPCBase):
    class MOUNT_PROC:
        NULL    = 0
        MNT     = 1
        DUMP    = 2
        UMNT    = 3
        UMNTALL = 4
        EXPORT  = 5

    class mountstat3:
        MNT3_OK = 0                 # no error
        MNT3ERR_PERM = 1            # Not owner
        MNT3ERR_NOENT = 2           # No such file or directory
        MNT3ERR_IO = 5              # I/O error
        MNT3ERR_ACCES = 13          # Permission denied
        MNT3ERR_NOTDIR = 20         # Not a directory
        MNT3ERR_INVAL = 22          # Invalid argument
        MNT3ERR_NAMETOOLONG = 63    # Filename too long
        MNT3ERR_NOTSUPP = 10004     # Operation not supported
        MNT3ERR_SERVERFAULT = 10006 # A failure on the server

class MOUNT(rpcbind.RPCBIND):
    def __init__(self, **server_settings):
        # should be swappable for real rpcbind
        self.mode_verbose = server_settings.get('mode_verbose', False) # verbose mode
        self.mode_debug = server_settings.get('mode_debug', False) # debug mode
        self.logger = server_settings.get('logger', None)

        # setup logger
        if self.logger == None:
            self.logger = logging.getLogger('MOUNT.{0}'.format(self.PROTO))
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        if self.mode_debug:
            self.logger.setLevel(logging.DEBUG)
        elif self.mode_verbose:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.WARN)

        self.logger.info("Started")

    def process(self, **arguments):
        MOUNT_PROCS = {
            RPC.MOUNT_PROC.NULL: self.NULL,
            RPC.MOUNT_PROC.MNT: self.MNT,
            RPC.MOUNT_PROC.DUMP: self.DUMP,
            RPC.MOUNT_PROC.UMNT: self.UMNT,
            RPC.MOUNT_PROC.UMNTALL: self.UMNTALL,
            RPC.MOUNT_PROC.EXPORT: self.EXPORT
        }
        MOUNT_PROCS[arguments["proc"]](**arguments)

    def NULL(self, **arguments):
        self.makeRPCHeader("", RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)

    def MNT(self, **arguments):
        body = arguments["body"]
        [length] = struct.unpack("!I", body.read(4))
        path = body.read(length)
        padding  = 4 - (length % 4)
        if padding != 4:
            body.read(padding)
        self.logger.debug("Received MNT for {0} from {1}".format(path, arguments["addr"]))
        # IP WHITELISTING GOES HERE PROBABLY
        # use sha256 because it's 64 bytes, no collisions etc
        resp = struct.pack("!I", RPC.mountstat3.MNT3_OK)
        resp += struct.pack("!I", 64)
        resp += hashlib.sha256(path).hexdigest()
        resp += struct.pack("!I", 1)
        resp += struct.pack("!I", RPC.auth_flavor.AUTH_UNIX)
        self.makeRPCHeader(resp, RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)

    def DUMP(self, **arguments):
        pass
    def UMNT(self, **arguments):
        pass
    def UMNTALL(self, **arguments):
        pass
    def EXPORT(self, **arguments):
        pass

class MOUNTDTCP(MOUNT):
    def __init__(self, **server_settings):
        MOUNT.__init__(self, **server_settings)
        self.PROTO = "TCP"
        # find out what port it should be listening on
        rpcnumber = 100005
        server_settings["pipelock"].acquire()
        server_settings["pipe"].send(rpcnumber)
        self.programs = {rpcnumber: server_settings["pipe"].recv()}
        server_settings["pipelock"].release()

        self.logger.debug("Received program settings from PORTMAPPER")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.programs[rpcnumber]["address"], self.programs[rpcnumber]["port"]))
        self.sock.listen(4)

class MOUNTDUDP(MOUNT):
    def __init__(self, **server_settings):
        MOUNT.__init__(self, **server_settings)
        self.PROTO = "UDP"
        rpcnumber = 100005
        server_settings["pipelock"].acquire()
        server_settings["pipe"].send(rpcnumber)
        self.programs = {rpcnumber: server_settings["pipe"].recv()}
        server_settings["pipelock"].release()

        self.logger.debug("Received program settings from PORTMAPPER")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.programs[rpcnumber]["address"], self.programs[rpcnumber]["port"]))

class MOUNTD:
    def __init__(self, **server_settings):
        self.logger = server_settings.get('logger', None)
        tcp_settings = server_settings
        tcp_settings["logger"] = helpers.get_child_logger(self.logger, "TCP")
        TCP = MOUNTDTCP(**tcp_settings)

        udp_settings = server_settings
        udp_settings["logger"] = helpers.get_child_logger(self.logger, "UDP")
        UDP = MOUNTDUDP(**udp_settings)

        self.TCP = threading.Thread(target = TCP.listen)
        self.TCP.daemon = True
        self.UDP = threading.Thread(target = UDP.listen)
        self.UDP.daemon = True

    def listen(self):
        self.TCP.start()
        self.UDP.start()
        while all(map(lambda x: x.isAlive(), [self.TCP, self.UDP])):
            time.sleep(1)
