import rpcbind
import logging
from pypxe import helpers
import socket
import threading
import time
import struct
import hashlib
import programs
import os
import stat
import math
import ctypes
import multiprocessing

class RPC(rpcbind.RPCBase):
    NFS_PROC = programs.RPC.NFS_PROC

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

    class ftype3:
        NF3REG    = 1
        NF3DIR    = 2
        NF3BLK    = 3
        NF3CHR    = 4
        NF3LNK    = 5
        NF3SOCK   = 6
        NF3FIFO   = 7

    class IPPROTO:
        IPPROTO_TCP4 = 6
        IPPROTO_UDP4 = 17

    class ACCESS3:
        ACCESS3_READ    = 0x0001
        ACCESS3_LOOKUP  = 0x0002
        ACCESS3_MODIFY  = 0x0004
        ACCESS3_EXTEND  = 0x0008
        ACCESS3_DELETE  = 0x0010
        ACCESS3_EXECUTE = 0x0020

class dropprivs:
    def __init__(self, uid, gid, groups):
        self.uid = uid
        self.gid = gid
        self.groups = groups

        self.olduid = os.getuid()
        self.oldgid = os.getgid()
        self.oldgroups = os.getgroups()

    def __enter__(self):
        os.setgroups(self.groups)
        os.setegid(self.gid)
        os.seteuid(self.uid)

    def __exit__(self, type, value, traceback):
        os.seteuid(self.olduid)
        os.setegid(self.oldgid)
        os.setgroups(self.oldgroups)

# runas priv dropper via multiprocessing.Process, with a Pipe to send back the return value.
# usage example:
# @runas(1000, 100, (100,))
# def func(foo):
#   print "I am user 1000 in group 100"
#   return dostuff(foo)
def runas(uid, gid, groups, chroot = ""):
    def decorator(f):
        def g(*args, **kwargs):
            gpipe = kwargs["gpipe"]
            del kwargs["gpipe"]
            chroot = kwargs.get("chroot", "")
            del kwargs["chroot"]
            if chroot:
                os.chdir(chroot)
                os.chroot(".")
            with dropprivs(uid, gid, groups):
                gpipe.send(f(*args, **kwargs))
            gpipe.close()
        def h(*args, **kwargs):
            [gpipea, gpipeb] = multiprocessing.Pipe()
            kwargs["gpipe"] = gpipeb
            kwargs["chroot"] = chroot
            gthread = multiprocessing.Process(target = g, args = args, kwargs = kwargs)
            gthread.daemon = True
            gthread.start()
            gthread.join()
            return gpipea.recv()
        return h
    return decorator

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

        self.rpcnumber = 100003
        self.programs = {self.rpcnumber: programs.programs[self.rpcnumber]}

        self.logger.info("Started")

    def process(self, **arguments):
        # new thread starts here
        # use client sock, not main sock
        self.clientsock = arguments["sock"]
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
        retval = PORTMAPPERPROCS[arguments["proc"]](**arguments)
        if retval:
            [errno, args] = retval
            if errno == 0:
                pass
            elif errno == RPC.nfsstat3.NFS3ERR_ACCES:
                # send 1 obj_attributes
                self.sendnfsresponse(RPC.nfsstat3.NFS3ERR_ACCES, struct.pack("!I", 1) + self.getattr(args["path"]), **arguments)
            elif errno == RPC.nfsstat3.NFS3ERR_BADHANDLE:
                # send 1 obj_attributes
                self.sendnfsresponse(RPC.nfsstat3.NFS3ERR_BADHANDLE, struct.pack("!I", 1) + self.getattr(args["path"]), **arguments)

    def NULL(self, **arguments):
        self.makeRPCHeader("", RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)

    def GETATTR(self, body = None, **arguments):
        path = self.extractpath(body)
        if not path: return RPC.nfsstat3.NFS3ERR_BADHANDLE, {"path": path}
        self.logger.debug("GETATTR({0}) from {1}".format(path, arguments["addr"]))
        self.sendnfsresponseOK(self.getattr(path), **arguments)

    def SETATTR(self, **arguments):
        self.logger.debug("SETATTR from {0}".format(arguments["addr"]))
        pass
    def LOOKUP(self, **arguments):
        self.logger.debug("LOOKUP from {0}".format(arguments["addr"]))
        pass

    def ACCESS(self, body = None, **arguments):
        path = self.extractpath(body)
        if not path: return RPC.nfsstat3.NFS3ERR_BADHANDLE, {"path": path}
        self.logger.debug("ACCESS({0}) from {1}".format(path, arguments["addr"]))
        libc = ctypes.CDLL("libc.so.6")
        # On success (all requested permissions granted), zero is returned.
        # normal os.access does not take into account euid
        os.euidaccess = lambda *args: not bool(libc.euidaccess(*args))
        os.euidaccess.__doc__ = "int euidaccess(const char *pathname, int mode);"

        [nfsmode] = struct.unpack("!I", body.read(4))
        mode = 0

        mappings = {
                # nfs in and out to access() in
                RPC.ACCESS3.ACCESS3_READ:    0x4,
                RPC.ACCESS3.ACCESS3_LOOKUP:  0x1,
                RPC.ACCESS3.ACCESS3_MODIFY:  0x2,
                RPC.ACCESS3.ACCESS3_EXTEND:  0x2,
                RPC.ACCESS3.ACCESS3_DELETE:  0x2,
                RPC.ACCESS3.ACCESS3_EXECUTE: 0x1
            }

        for mapping in mappings:
            # if the client requested it, and we've not already got a positive result
            if nfsmode & mapping and not mode & mapping:
                @runas(arguments["uid"], arguments["gid"], arguments["groups"])
                def f(path, mode):
                    return os.euidaccess(path, mode)
                if f(path, mappings[mapping]):
                    mode |= mapping

        resp = struct.pack("!I", 1)
        resp += self.getattr(path)
        resp += struct.pack("!I", mode)

        self.sendnfsresponseOK(resp, **arguments)

    def READLINK(self, body = None, **arguments):
        path = self.extractpath(body)
        if not path: return RPC.nfsstat3.NFS3ERR_BADHANDLE, {"path": path}
        self.logger.debug("READLINK({0}) from {1}".format(path, arguments["addr"]))
        print path

    def READ(self, **arguments):
        self.logger.debug("READ from {0}".format(arguments["addr"]))
        pass
    def WRITE(self, **arguments):
        self.logger.debug("WRITE from {0}".format(arguments["addr"]))
        pass
    def CREATE(self, **arguments):
        self.logger.debug("CREATE from {0}".format(arguments["addr"]))
        pass
    def MKDIR(self, **arguments):
        self.logger.debug("MKDIR from {0}".format(arguments["addr"]))
        pass
    def SYMLINK(self, **arguments):
        self.logger.debug("SYMLINK from {0}".format(arguments["addr"]))
        pass
    def MKNOD(self, **arguments):
        self.logger.debug("MKNOD from {0}".format(arguments["addr"]))
        pass
    def REMOVE(self, **arguments):
        self.logger.debug("REMOVE from {0}".format(arguments["addr"]))
        pass
    def RMDIR(self, **arguments):
        self.logger.debug("RMDIR from {0}".format(arguments["addr"]))
        pass
    def RENAME(self, **arguments):
        self.logger.debug("RENAME from {0}".format(arguments["addr"]))
        pass
    def LINK(self, **arguments):
        self.logger.debug("LINK from {0}".format(arguments["addr"]))
        pass
    def READDIR(self, **arguments):
        self.logger.debug("READDIR from {0}".format(arguments["addr"]))
        pass

    def READDIRPLUS(self, body = None, **arguments):
        path = self.extractpath(body)
        if not path: return RPC.nfsstat3.NFS3ERR_BADHANDLE, {"path": path}
        self.logger.debug("READDIRPLUS({0}) from {1}".format(path, arguments["addr"]))

        [cookie,
            verifier,
            dircount,
            maxcount
            ] = struct.unpack("!QQII", body.read(2*8+2*4))

        @runas(arguments["uid"], arguments["gid"], arguments["groups"], chroot = path)
        def f(cookie, dircount, **arguments):
            preresp = ""
            # 1 dir_attributes
            preresp += struct.pack("!I", 1)
            preresp += self.getattr(".")
            # verifier
            preresp += struct.pack("!Q", 0)
            fullresp = preresp
            count = 0
            broken = False

            for dirent in os.listdir("."):
                if count < cookie:
                    # skip up to cookie
                    count += 1
                    continue
                resp = ""
                direntstat = os.lstat(dirent)
                resp += struct.pack("!Q", direntstat.st_ino)
                resp += struct.pack("!I", len(dirent))
                resp += dirent
                resp += "\x00" * ((4 - (len(dirent) % 4))&~4)
                count += 1
                # cookie, for advancing
                resp += struct.pack("!Q", count)
                # attrib follows
                resp += struct.pack("!I", 1)
                # attrib
                resp += self.getattr(dirent)
                # fh follows, 64 bytes
                resp += struct.pack("!II", 1, 64)
                resp += self.addfh(dirent)

                if len(fullresp)+len(resp) > dircount and len(fullresp) == len(preresp):
                    self.sendnfsresponse(RPC.nfsstat3.NFS3ERR_TOOSMALL, "", **arguments)
                elif len(fullresp)+len(resp)+4 > dircount:
                    broken = True
                    break
                else:
                    # value follows
                    fullresp += struct.pack("!I", 1)
                    fullresp += resp

            # value follows no
            fullresp += struct.pack("!I", 0)
            # eof if we didn't break early
            fullresp += struct.pack("!I", 0 if broken else 1)
            return fullresp

        fullresp = f(cookie, dircount, **arguments)

        self.sendnfsresponseOK(fullresp, **arguments)

    def FSSTAT(self, **arguments):
        self.logger.debug("FSSTAT from {0}".format(arguments["addr"]))
        pass

    def FSINFO(self, body = None, **arguments):
        path = self.extractpath(body)
        if not path: return RPC.nfsstat3.NFS3ERR_BADHANDLE, {"path": path}

        self.logger.debug("FSINFO({0}) from {1}".format(path, arguments["addr"]))
        # FSINFO3resok RFC1813 p 86-7
        # one obj_attributes
        resp = struct.pack("!I", 1)
        resp += self.getattr(path)

        # max read size, arbitrary. 4k
        resp += struct.pack("!I", 0x1000)
        # perferred read size, matches max
        resp += struct.pack("!I", 0x1000)
        # suggested read size multiple
        resp += struct.pack("!I", 1)

        # max write size, arbitrary
        resp += struct.pack("!I", 0x1000)
        # perferred write size, matches max
        resp += struct.pack("!I", 0x1000)
        # suggested write size multiple
        resp += struct.pack("!I", 1)

        # preferred readdir req size
        resp += struct.pack("!I", 0x1000)

        # max file size
        resp += struct.pack("!Q", 2**64-1)

        # time precision, guarantee second only
        resp += struct.pack("!II", 1, 0)

        # properties
        # LINK|SYMLINK|HOMOGENEOUS|CANSETTIME
        # HOMOGENOUS should be changed if we cross mount boundaries
        resp += struct.pack("!I", 0x1|0x2|0x8|0x10)
        self.sendnfsresponseOK(resp, **arguments)


    def PATHCONF(self, body = None, **arguments):
        path = self.extractpath(body)
        if not path: return RPC.nfsstat3.NFS3ERR_BADHANDLE, {"path": path}

        self.logger.debug("PATHCONF({0}) from {1}".format(path, arguments["addr"]))
        # PATHCONF3resok RFC1813 p 90
        # one obj_attributes
        resp = struct.pack("!I", 1)
        resp += self.getattr(path)
        try:
            resp += struct.pack("!I", os.pathconf(path, "PC_LINK_MAX"))
        except ValueError:
            resp += struct.pack("!I", 0)

        try:
            resp += struct.pack("!I", os.pathconf(path, "PC_NAME_MAX"))
        except ValueError:
            resp += struct.pack("!I", 0)

        # no_trunc         = False
        # chown_restricted = True
        # case_insensitive = False
        # case_preserving  = True
        resp += struct.pack("!IIII", 0, 1, 0, 1)

        self.sendnfsresponseOK(resp, **arguments)

    def COMMIT(self, **arguments):
        self.logger.debug("COMMIT from {0}".format(arguments["addr"]))
        pass

    ############################
    # util functions from here #
    ############################

    def extractpath(self, body):
        [fhlen] = struct.unpack("!I", body.read(4))
        fh = body.read(fhlen)
        path = self.getpath(fh)
        return path

    def getfh(self, fh):
        if fh not in self.filehandles: return {}
        if fh in self.filehandles and self.filehandles[fh].get("expires", 0) < time.time():
            del self.filehandles[fh]
            return {}
        return self.filehandles[fh]

    def addfh(self, path):
        matchingfh = filter(lambda x:self.filehandles[x]["path"] == path, self.filehandles)
        if matchingfh:
            if self.filehandles[matchingfh]["expires"] > time.time():
                return matchingfh
            else:
                del self.filehandles[matchinfh]
        fh = hashlib.sha256(path).hexdigest()
        self.filehandles[fh] = {"path": path, "expires": time.time()+600}
        return fh

    def getpath(self, fh):
        return self.getfh(fh).get("path", "")

    def sendnfsresponseOK(self, args, **arguments):
        self.sendnfsresponse(RPC.nfsstat3.NFS3_OK, args, **arguments)

    def sendnfsresponse(self, errno, args, **arguments):
        resp = struct.pack("!I", errno)
        resp += args
        self.makeRPCHeader(resp, RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)

    def gettype(self, path):
        mode = os.lstat(path).st_mode
        return filter(lambda x:x[1], [
        [RPC.ftype3.NF3REG,  stat.S_ISREG(mode)],
        [RPC.ftype3.NF3DIR,  stat.S_ISDIR(mode)],
        [RPC.ftype3.NF3BLK,  stat.S_ISBLK(mode)],
        [RPC.ftype3.NF3CHR,  stat.S_ISCHR(mode)],
        [RPC.ftype3.NF3LNK,  stat.S_ISLNK(mode)],
        [RPC.ftype3.NF3SOCK, stat.S_ISSOCK(mode)],
        [RPC.ftype3.NF3FIFO, stat.S_ISFIFO(mode)]
        ])[0][0]

    def getmode(self, path):
        mode = os.lstat(path).st_mode
        mode &= (0x800| # setuid
                0x400| # setgid
                0x200| # save swapped text
                0x100| # u+r
                0x080| # u+w
                0x040| # u+x
                0x020| # g+r
                0x010| # g+w
                0x008| # g+x
                0x004| # o+r
                0x002| # o+w
                0x001) # o+x
        return mode

    def packtime(self, time):
        i, f = math.modf(time)[::-1]
        while f != 0 and f < 2**32-1: f *= 10
        f /= 10
        return (i, f)

    def getattr(self, path):
        # return fattr3 RFC1813 p22
        pathstat = os.lstat(path)
        fattr3  = struct.pack("!I", self.gettype(path))
        fattr3 += struct.pack("!I", self.getmode(path))
        fattr3 += struct.pack("!I", pathstat.st_nlink)
        fattr3 += struct.pack("!I", pathstat.st_uid)
        fattr3 += struct.pack("!I", pathstat.st_gid)
        #  twice for size and used
        fattr3 += struct.pack("!Q", pathstat.st_size)
        fattr3 += struct.pack("!Q", pathstat.st_size)

        fattr3 += struct.pack("!II", pathstat.st_rdev/256, pathstat.st_rdev%256)
        # filesystem identifier
        fattr3 += "\x00\x00\x00PyPXE"
        fattr3 += struct.pack("!Q", pathstat.st_ino)

        fattr3 += struct.pack("!II", *self.packtime(pathstat.st_atime))
        fattr3 += struct.pack("!II", *self.packtime(pathstat.st_mtime))
        fattr3 += struct.pack("!II", *self.packtime(pathstat.st_ctime))
        return fattr3


class NFSDTCP(NFS):
    def __init__(self, **server_settings):
        NFS.__init__(self, **server_settings)
        self.PROTO = "TCP"
        self.keepalive = True
        self.filehandles = server_settings["filehandles"]
        # find out what port it should be listening on
        port = server_settings.get("port", 2049)
        # address can be passed to here from cli, and also to portmapper for bind addr
        addr = ""
        # prog, vers, proto, port
        self.registerPort(self.rpcnumber, self.programs[self.rpcnumber]["version"][0], RPC.IPPROTO.IPPROTO_TCP4, port)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", port))
        self.sock.listen(4)

class NFSD:
    def __init__(self, **server_settings):
        self.logger = server_settings.get('logger', None)
        # support multiple roots
        self.nfsroots = server_settings.get('nfsroots', [])
        filehandles = {}
        for root in self.nfsroots:
            filehandles[hashlib.sha256(root).hexdigest()] = {"path": root, "expires": float("inf")}
        tcp_settings = server_settings
        tcp_settings["logger"] = helpers.get_child_logger(self.logger, "TCP")
        tcp_settings["filehandles"] = filehandles
        TCP = NFSDTCP(**tcp_settings)

        self.TCP = threading.Thread(target = TCP.listen)
        self.TCP.daemon = True

    def listen(self):
        self.TCP.start()
        while all(map(lambda x: x.isAlive(), [self.TCP])):
            time.sleep(1)
