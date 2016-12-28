import rpcbind
import logging
from pypxe import helpers
import socket
import threading
import time
import struct
import hashlib

"""
import ctypes
libc = ctypes.CDLL("libc.so.6")
# On success (all requested permissions granted), zero is returned.
os.euidaccess = lambda *args: not bool(libc.euidaccess(*args))
os.euidaccess.__doc__ = "int euidaccess(const char *pathname, int mode);"
"""


class RPC(rpcbind.RPCBase):
    class NFS_PROC:
        NFSPROC3_NULL        = 0
        NFSPROC3_GETATTR     = 1
        NFSPROC3_SETATTR     = 2
        NFSPROC3_LOOKUP      = 3
        NFSPROC3_ACCESS      = 4
        NFSPROC3_READLINK    = 5
        NFSPROC3_READ        = 6
        NFSPROC3_WRITE       = 7
        NFSPROC3_CREATE      = 8
        NFSPROC3_MKDIR       = 9
        NFSPROC3_SYMLINK     = 10
        NFSPROC3_MKNOD       = 11
        NFSPROC3_REMOVE      = 12
        NFSPROC3_RMDIR       = 13
        NFSPROC3_RENAME      = 14
        NFSPROC3_LINK        = 15
        NFSPROC3_READDIR     = 16
        NFSPROC3_READDIRPLUS = 17
        NFSPROC3_FSSTAT      = 18
        NFSPROC3_FSINFO      = 19
        NFSPROC3_PATHCONF    = 20
        NFSPROC3_COMMIT      = 21

    class nfsstat3:
        NFS3_OK             = 0
        NFS3ERR_PERM        = 1
        NFS3ERR_NOENT       = 2
        NFS3ERR_IO          = 5
        NFS3ERR_NXIO        = 6
        NFS3ERR_ACCES       = 13
        NFS3ERR_EXIST       = 17
        NFS3ERR_XDEV        = 18
        NFS3ERR_NODEV       = 19
        NFS3ERR_NOTDIR      = 20
        NFS3ERR_ISDIR       = 21
        NFS3ERR_INVAL       = 22
        NFS3ERR_FBIG        = 27
        NFS3ERR_NOSPC       = 28
        NFS3ERR_ROFS        = 30
        NFS3ERR_MLINK       = 31
        NFS3ERR_NAMETOOLONG = 63
        NFS3ERR_NOTEMPTY    = 66
        NFS3ERR_DQUOT       = 69
        NFS3ERR_STALE       = 70
        NFS3ERR_REMOTE      = 71
        NFS3ERR_BADHANDLE   = 10001
        NFS3ERR_NOT_SYNC    = 10002
        NFS3ERR_BAD_COOKIE  = 10003
        NFS3ERR_NOTSUPP     = 10004
        NFS3ERR_TOOSMALL    = 10005
        NFS3ERR_SERVERFAULT = 10006
        NFS3ERR_BADTYPE     = 10007
        NFS3ERR_JUKEBOX     = 10008

class NFS(rpcbind.RPCBIND):
    def __init__(self, **server_settings):
        # should be swappable for real rpcbind
        self.mode_verbose = server_settings.get('mode_verbose', False) # verbose mode
        self.mode_debug = server_settings.get('mode_debug', False) # debug mode
        self.logger = server_settings.get('logger', None)

        # setup logger
        if self.logger == None:
            self.logger = logging.getLogger('NFS.{0}'.format(self.PROTO))
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
        PORTMAPPERPROCS = {
            RPC.NFS_PROC.NFSPROC3_NULL: self.NULL,
            RPC.NFS_PROC.NFSPROC3_GETATTR: self.GETATTR,
            RPC.NFS_PROC.NFSPROC3_SETATTR: self.SETATTR,
            RPC.NFS_PROC.NFSPROC3_LOOKUP: self.LOOKUP,
            RPC.NFS_PROC.NFSPROC3_ACCESS: self.ACCESS,
            RPC.NFS_PROC.NFSPROC3_READLINK: self.READLINK,
            RPC.NFS_PROC.NFSPROC3_READ: self.READ,
            RPC.NFS_PROC.NFSPROC3_WRITE: self.WRITE,
            RPC.NFS_PROC.NFSPROC3_CREATE: self.CREATE,
            RPC.NFS_PROC.NFSPROC3_MKDIR: self.MKDIR,
            RPC.NFS_PROC.NFSPROC3_SYMLINK: self.SYMLINK,
            RPC.NFS_PROC.NFSPROC3_MKNOD: self.MKNOD,
            RPC.NFS_PROC.NFSPROC3_REMOVE: self.REMOVE,
            RPC.NFS_PROC.NFSPROC3_RMDIR: self.RMDIR,
            RPC.NFS_PROC.NFSPROC3_RENAME: self.RENAME,
            RPC.NFS_PROC.NFSPROC3_LINK: self.LINK,
            RPC.NFS_PROC.NFSPROC3_READDIR: self.READDIR,
            RPC.NFS_PROC.NFSPROC3_READDIRPLUS: self.READDIRPLUS,
            RPC.NFS_PROC.NFSPROC3_FSSTAT: self.FSSTAT,
            RPC.NFS_PROC.NFSPROC3_FSINFO: self.FSINFO,
            RPC.NFS_PROC.NFSPROC3_PATHCONF: self.PATHCONF,
            RPC.NFS_PROC.NFSPROC3_COMMIT: self.COMMIT,
        }
        PORTMAPPERPROCS[arguments["proc"]](**arguments)

    def NULL(self, **arguments):
        self.makeRPCHeader("", RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)
    def GETATTR(self, **arguments):
        self.logger.debug("GETATTR")
        pass
    def SETATTR(self, **arguments):
        self.logger.debug("SETATTR")
        pass
    def LOOKUP(self, **arguments):
        self.logger.debug("LOOKUP")
        pass
    def ACCESS(self, **arguments):
        self.logger.debug("ACCESS")
        pass
    def READLINK(self, **arguments):
        self.logger.debug("READLINK")
        pass
    def READ(self, **arguments):
        self.logger.debug("READ")
        pass
    def WRITE(self, **arguments):
        self.logger.debug("WRITE")
        pass
    def CREATE(self, **arguments):
        self.logger.debug("CREATE")
        pass
    def MKDIR(self, **arguments):
        self.logger.debug("MKDIR")
        pass
    def SYMLINK(self, **arguments):
        self.logger.debug("SYMLINK")
        pass
    def MKNOD(self, **arguments):
        self.logger.debug("MKNOD")
        pass
    def REMOVE(self, **arguments):
        self.logger.debug("REMOVE")
        pass
    def RMDIR(self, **arguments):
        self.logger.debug("RMDIR")
        pass
    def RENAME(self, **arguments):
        self.logger.debug("RENAME")
        pass
    def LINK(self, **arguments):
        self.logger.debug("LINK")
        pass
    def READDIR(self, **arguments):
        self.logger.debug("READDIR")
        pass
    def READDIRPLUS(self, **arguments):
        self.logger.debug("READDIRPLUS")
        pass
    def FSSTAT(self, **arguments):
        self.logger.debug("FSSTAT")
        pass
    def FSINFO(self, **arguments):
        self.logger.debug("FSINFO")
        pass
    def PATHCONF(self, **arguments):
        self.logger.debug("PATHCONF")
        pass
    def COMMIT(self, **arguments):
        self.logger.debug("COMMIT")
        pass

class NFSDTCP(NFS):
    def __init__(self, **server_settings):
        NFS.__init__(self, **server_settings)
        self.PROTO = "TCP"
        self.keepalive = True
        # find out what port it should be listening on
        rpcnumber = 100003
        server_settings["pipelock"].acquire()
        server_settings["pipe"].send(rpcnumber)
        self.programs = {rpcnumber: server_settings["pipe"].recv()}
        server_settings["pipelock"].release()

        self.logger.debug("Received program settings from PORTMAPPER")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.programs[rpcnumber]["address"], self.programs[rpcnumber]["port"]))
        self.sock.listen(4)

class NFSD:
    def __init__(self, **server_settings):
        self.logger = server_settings.get('logger', None)
        tcp_settings = server_settings
        tcp_settings["logger"] = helpers.get_child_logger(self.logger, "TCP")
        TCP = NFSDTCP(**tcp_settings)

        self.TCP = threading.Thread(target = TCP.listen)
        self.TCP.daemon = True

    def listen(self):
        self.TCP.start()
        while all(map(lambda x: x.isAlive(), [self.TCP])):
            time.sleep(1)
