import rpcbind
import logging
from pypxe import helpers
import socket
import threading
import time
import struct
import hashlib
import programs
import StringIO
import os

class RPC(rpcbind.RPCBase):
    MOUNT_PROC = programs.RPC.MOUNT_PROC

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

    class IPPROTO:
        IPPROTO_TCP4 = 6
        IPPROTO_UDP4 = 17

class MOUNT(rpcbind.RPCBIND):
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

    def MNT(self, body = None, **arguments):
        if arguments["auth_type"] != RPC.auth_flavor.AUTH_UNIX:
            self.makeRPCHeader(struct.pack("!I", int(True)), RPC.reply_stat.MSG_DENIED, RPC.reject_stat.AUTH_ERROR, **arguments)

        [length] = struct.unpack("!I", body.read(4))
        path = body.read(length)
        body.read((4 - (length % 4))&~4)

        filehandles = self.server_settings["filehandles"]
        if path not in filehandles:
            if len(filehandles) == 1 and path == "/":
                filehandles["/"] = filehandles[filehandles.keys()[0]]
            else:
                resp = struct.pack("!I", RPC.mountstat3.MNT3ERR_NOENT)
                return self.makeRPCHeader(resp, RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)

        self.logger.debug("Received MNT for {0} from {1} by uid:{2}".format(path, arguments["addr"], arguments["uid"]))
        # IP WHITELISTING GOES HERE PROBABLY
        # use sha256 because it's 64 bytes, no collisions etc
        resp = struct.pack("!I", RPC.mountstat3.MNT3_OK)
        resp += struct.pack("!I", 64)
        resp += filehandles[path]
        resp += struct.pack("!I", 1)
        resp += struct.pack("!I", RPC.auth_flavor.AUTH_UNIX)
        self.makeRPCHeader(resp, RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)

    def DUMP(self, **arguments):
        pass

    def UMNT(self, body = None, **arguments):
        [length] = struct.unpack("!I", body.read(4))
        path = body.read(length)
        body.read((4 - (length % 4))&~4)
        self.logger.debug("Received UMNT for {0} from {1} by uid:{2}".format(path, arguments["addr"], arguments["uid"]))
        self.makeRPCHeader("", RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)

    def UMNTALL(self, **arguments):
        pass
    def EXPORT(self, **arguments):
        pass

class MOUNTD(rpcbind.DAEMON):
    def __init__(self, **server_settings):
        self.logger = server_settings.get('logger', None)

        # caches
        self.nfsroot = os.path.abspath(server_settings.get('nfsroot', 'nfsroot'))
        self.filehandles = {self.nfsroot: hashlib.sha256(self.nfsroot).hexdigest()}

        server_settings["rpcnumber"] = 100005
        server_settings["programs"] = {server_settings["rpcnumber"]: programs.programs[server_settings["rpcnumber"]]}
        server_settings["filehandles"] = self.filehandles

        self.port = server_settings.get("port", 635)
        # address can be passed to here from cli, and also to portmapper for bind addr
        self.addr = ""
        # prog, vers, proto, port

        self.createTCP4Thread(MOUNT, server_settings)
        self.createUDP4Thread(MOUNT, server_settings)

    def listen(self):
        self.TCP4.start()
        self.UDP4.start()
        while all(map(lambda x: x.isAlive(), [self.TCP4, self.UDP4])):
            time.sleep(1)
