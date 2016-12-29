import rpcbind
import logging
from pypxe import helpers
import socket
import threading
import time
import struct
import hashlib
import programs
import stat
import math
import multiprocessing
import multiprocessing.managers

import ctypes
import os
libc = ctypes.CDLL("libc.so.6")
# On success (all requested permissions granted), zero is returned.
# normal os.access does not take into account euid
os.euidaccess = lambda *args: not bool(libc.euidaccess(*args))
os.euidaccess.__doc__ = "int euidaccess(const char *pathname, int mode);"

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

    class access:
        F_OK = 0
        R_OK = 4
        W_OK = 2
        X_OK = 1

class dropprivs:
    def __init__(self, uid, gid, groups):
        self.uid = uid
        self.gid = gid
        self.groups = groups

        self.olduid = os.getuid()
        self.oldgid = os.getgid()
        self.oldgroups = os.getgroups()

    def __enter__(self):
        if not os.fork(): return
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
# this is super slow and therefore not good.
# can't use Pool because g and h are closures
def runas(uid, gid, groups):
    def decorator(f):
        def g(*args, **kwargs):
            gpipe = kwargs["gpipe"]
            del kwargs["gpipe"]
            with dropprivs(uid, gid, groups):
                gpipe.send(f(*args, **kwargs))
            gpipe.close()
        def h(*args, **kwargs):
            [gpipea, gpipeb] = multiprocessing.Pipe()
            kwargs["gpipe"] = gpipeb
            gthread = multiprocessing.Process(target = g, args = args, kwargs = kwargs)
            gthread.daemon = True
            gthread.start()
            gthread.join()
            return gpipea.recv()
        return h
    return decorator

class NFS(rpcbind.RPCBIND):
    def setup(self):
        self.server_settings = self.server.server_settings
        self.nfsroot = os.path.abspath(self.server_settings["nfsroot"])
        self.lastfile = False

    def process(self, **arguments):
        # new thread starts here
        # use client sock, not main sock
        self.clientsock = arguments["sock"]
        NFSPROCS = {
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
        try:
            retval = NFSPROCS[arguments["proc"]](**arguments)
        except helpers.PathTraversalException:
            self.logger.debug("PathTraversalException")
            self.sendnfsresponse(RPC.nfsstat3.NFS3ERR_EXIST, struct.pack("!I", 1) + self.getattr(self.nfsroot), **arguments)
            return
        if retval:
            [errno, args] = retval
            if errno == 0:
                pass
            elif errno == RPC.nfsstat3.NFS3ERR_ACCES:
                # send 1 obj_attributes
                self.sendnfsresponse(RPC.nfsstat3.NFS3ERR_ACCES, struct.pack("!I", 1) + self.getattr(args["path"]), **arguments)
            elif errno == RPC.nfsstat3.NFS3ERR_BADHANDLE:
                self.sendnfsresponse(RPC.nfsstat3.NFS3ERR_BADHANDLE, struct.pack("!I", 1) + self.getattr(args["path"] or self.nfsroot), **arguments)
            elif errno == RPC.nfsstat3.NFS3ERR_EXIST:
                self.sendnfsresponse(RPC.nfsstat3.NFS3ERR_EXIST, struct.pack("!I", 1) + self.getattr(args["path"] or self.nfsroot), **arguments)
            elif errno == RPC.nfsstat3.NFS3ERR_INVAL:
                self.sendnfsresponse(RPC.nfsstat3.NFS3ERR_INVAL, struct.pack("!I", 1) + self.getattr(args["path"] or self.nfsroot), **arguments)
            elif errno == RPC.nfsstat3.NFS3ERR_ROFS:
                self.sendnfsresponse(RPC.nfsstat3.NFS3ERR_ROFS, struct.pack("!I", 1) + self.getattr(args["path"] or self.nfsroot), **arguments)

    def NULL(self, **arguments):
        self.makeRPCHeader("", RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)

    def GETATTR(self, body = None, **arguments):
        path = self.extractpath(body)
        if not path: return RPC.nfsstat3.NFS3ERR_BADHANDLE, {"path": path}
        self.logger.debug("GETATTR({0}) from {1}".format(path, arguments["addr"]))

        @runas(arguments["uid"], arguments["gid"], arguments["groups"])
        def f(path):
            return self.getattr(path)

        self.sendnfsresponseOK(f(path), **arguments)

    def SETATTR(self, body = None, **arguments):
        path = self.extractpath(body)
        if not path: return RPC.nfsstat3.NFS3ERR_BADHANDLE, {"path": path}
        return RPC.nfsstat3.NFS3ERR_ROFS, {"path": path}

        fullfile = helpers.normalize_path(self.nfsroot, path)
        if not os.path.exists(fullfile):
            return RPC.nfsstat3.NFS3ERR_EXIST, {"path": path}

        if not self.canread(fullfile, **arguments):
            return RPC.nfsstat3.NFS3ERR_ACCES, {"path": path}

        self.logger.debug("SETATTR({0}) from {1}".format(path, arguments["addr"]))

    def LOOKUP(self, body = None, **arguments):
        path = self.extractpath(body)
        if not path: return RPC.nfsstat3.NFS3ERR_BADHANDLE, {"path": path}
        file = self.extractstring(body)
        self.logger.debug("LOOKUP({0}, {1}) from {2}".format(path, file, arguments["addr"]))

        try:
            fullfile = helpers.normalize_path(path, file)
        except PathTraversalException:
            return RPC.nfsstat3.NFS3ERR_EXIST, {"path": path}

        if not os.path.exists(fullfile):
            return RPC.nfsstat3.NFS3ERR_EXIST, {"path": path}

        @runas(arguments["uid"], arguments["gid"], arguments["groups"])
        def f(fullfile, path):
            resp = struct.pack("!I", 64)
            fh = self.getfh(fullfile)
            if not fh:
                fh = self.addfh(fullfile)
            resp += fh
            resp += struct.pack("!I", 1)
            resp += self.getattr(fullfile)
            resp += struct.pack("!I", 1)
            resp += self.getattr(path)
            return resp

        resp = f(fullfile, path)

        self.sendnfsresponseOK(resp, **arguments)

    def ACCESS(self, body = None, **arguments):
        path = self.extractpath(body)
        if not path: return RPC.nfsstat3.NFS3ERR_BADHANDLE, {"path": path}
        self.logger.debug("ACCESS({0}) from {1}".format(path, arguments["addr"]))

        [nfsmode] = struct.unpack("!I", body.read(4))
        mode = 0

        mappings = {
                # nfs in and out to access() in
                RPC.ACCESS3.ACCESS3_READ:    RPC.access.R_OK,
                RPC.ACCESS3.ACCESS3_LOOKUP:  RPC.access.X_OK,
                RPC.ACCESS3.ACCESS3_MODIFY:  RPC.access.W_OK,
                RPC.ACCESS3.ACCESS3_EXTEND:  RPC.access.W_OK,
                RPC.ACCESS3.ACCESS3_DELETE:  RPC.access.W_OK,
                RPC.ACCESS3.ACCESS3_EXECUTE: RPC.access.X_OK
            }

        @runas(arguments["uid"], arguments["gid"], arguments["groups"])
        def f(path, mode):
            return os.euidaccess(path, mode)
        for mapping in mappings:
            # if the client requested it, and we've not already got a positive result
            if nfsmode & mapping and not mode & mapping:
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

        if self.gettype(path) != RPC.ftype3.NF3LNK:
            return RPC.nfsstat3.NFS3ERR_INVAL, {"path": path}

        if not self.canread(path, **arguments):
            return RPC.nfsstat3.NFS3ERR_ACCES, {"path": path}

        @runas(arguments["uid"], arguments["gid"], arguments["groups"])
        def f(path):
            # 1 getattr
            resp = struct.pack("!I", 1)
            resp += self.getattr(path)
            resp += self.packstring(os.readlink(path))
            return resp

        resp = f(path)

        self.sendnfsresponseOK(resp, **arguments)

    def READ(self, body = True, **arguments):
        path = self.extractpath(body)
        if not path: return RPC.nfsstat3.NFS3ERR_BADHANDLE, {"path": path}
        [offset, count] = struct.unpack("!QI", body.read(8+4))
        self.logger.debug("READ({0}) {1} bytes at {2} from {3}".format(path, count, offset, arguments["addr"]))

        if not self.canread(path, **arguments):
            return RPC.nfsstat3.NFS3ERR_ACCES, {"path": path}

        @runas(arguments["uid"], arguments["gid"], arguments["groups"])
        def f(file, offset, count, fh):
            resp = struct.pack("!I", 1)
            resp += self.getattr(path)
            # optimize consecutive reads
            if not fh or fh.name != file:
                # no file or wrong file
                if fh: fh.close()
                fh = open(path)
            elif fh and fh.name == file and fh.tell() != offset:
                print "semihit"
                # valid file, invalid offset
                fh.seek(offset)
            else:
                print "hit"
            fh.seek(offset)
            data = fh.read(count)
            resp += struct.pack("!I", len(data))
            # we can't read any more if we're at eof
            resp += struct.pack("!I", 0 if len(fh.read(1)) else 1)
            resp += struct.pack("!I", len(data))
            resp += data
            return resp, fh

        [resp, fh] = f(path, offset, count, self.lastfile)
        self.lastfile = fh
        self.sendnfsresponseOK(resp, **arguments)
        return

        readcache = selfserver_settings["readcache"]
        readcachelock = selfserver_settings["readcachelock"]

        addtocache = False
        if (path, offset, count) in readcache:
            self.logger.debug("READ cache hit")
            resp = readcache[(path, offset, count)]
        else:
            self.logger.debug("READ cache miss")
            addtocache = True
            resp = f(path, offset, count)

        self.sendnfsresponseOK(resp, **arguments)
        if addtocache:
            readcachelock.acquire()
            # if we've hit the cache limit, evict something first
            if len(readcache["metadata"]) > readcache["maxcacheelems"]:
                idx = readcache["metadata"].pop(0)
                del readcache[idx]
            # order is important
            readcache["metadata"].append((path, offset, count))
            readcache[(path, offset, count)] = resp
            readcachelock.release()


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

        @runas(arguments["uid"], arguments["gid"], arguments["groups"])
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

                resp += self.packstring(dirent)
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

    def canread(self, path, **arguments):
        @runas(arguments["uid"], arguments["gid"], arguments["groups"])
        def f(path, mode):
            return os.euidaccess(path, mode)
        return f(path, RPC.access.R_OK)

    def extractstring(self, body):
        [strlen] = struct.unpack("!I", body.read(4))
        str = body.read(strlen)
        return str

    def packstring(self, string):
        # string length
        ret = struct.pack("!I", len(string))
        # string itself
        ret += string
        # padding
        ret += "\x00" * ((4 - (len(string) % 4))&~4)

        return ret

    def extractpath(self, body):
        fh = self.extractstring(body)
        path = self.getpath(fh)

        if path == self.nfsroot:
            return self.nfsroot
        else:
            return helpers.normalize_path(self.nfsroot, path)

    def getfh(self, fh):
        filehandles = self.server_settings["filehandles"]
        if fh not in filehandles: return {}
        if fh in filehandles and filehandles[fh].get("expires", 0) < time.time():
            del filehandles[fh]
            return {}
        return filehandles[fh]

    def addfh(self, path):
        filehandles = self.server_settings["filehandles"]
        matchingfh = []
        for handle in filehandles.keys():
            if filehandles[handle].get("path") == path:
                matchingfh.append(handle)
        if matchingfh:
            [matchingfh] = matchingfh
            if filehandles[matchingfh]["expires"] > time.time():
                return matchingfh
            else:
                del filehandles[matchinfh]
        else:
            fh = hashlib.sha256(path).hexdigest()
            filehandles[fh] = {"path": path, "expires": time.time()+600}
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

class NFSD(rpcbind.DAEMON):
    def __init__(self, **server_settings):
        self.logger = server_settings.get('logger', None)

        self.port = server_settings.get("port", 2049)
        # address can be passed to here from cli, and also to portmapper for bind addr
        self.addr = ""

        server_settings["rpcnumber"] = 100003
        server_settings["programs"] = {server_settings["rpcnumber"]: programs.programs[server_settings["rpcnumber"]]}

        # a normal multiprocessing.Manager listens on a unix socket
        # this is useless if we want to use from arbitrary users
        # So use the underlying multiprocessing.manager.BaseManager and
        # .register() stuff
        # we don't particularly care what it listens on, but ought to be localhost
        # the data is authenticated using a random key, so we should be safe from attackers
        # see multiprocessing/managers.py +1088 ish for the rough source of this
        # unfortunately it causes slow shutdown on ^C
        manager = multiprocessing.managers.BaseManager(('127.0.0.1', 0))
        manager.register("dict", dict, multiprocessing.managers.DictProxy)
        manager.register("list", list, multiprocessing.managers.ListProxy)
        manager.register("Lock", threading.Lock, multiprocessing.managers.AcquirerProxy)
        manager.start()
        filehandles = manager.dict()
        readcache = manager.dict()
        readcache["metadata"] = []
        readcachelock = manager.Lock()

        # 4096 average read
        cachesize = int(filter(lambda x:x.isdigit(), server_settings["readcachesize"]))
        cacheunit = filter(lambda x:not x.isdigit(), server_settings["readcachesize"])
        readcache["maxcacheelems"] = (cachesize * {
            "": 1,
            "b": 1,
            "Kb":  1000**1,
            "KiB": 1024**1,
            "Mb" : 1000**2,
            "MiB": 1024**2,
            "Gb":  1000**3,
            "GiB": 1024**3
            }[cacheunit]) / 4096

        self.nfsroot = os.path.abspath(server_settings.get('nfsroot', 'nfsroot'))
        filehandles[hashlib.sha256(self.nfsroot).hexdigest()] = {"path": self.nfsroot, "expires": float("inf")}

        server_settings["filehandles"] = filehandles
        server_settings["readcache"] = readcache
        server_settings["readcachelock"] = readcachelock

        self.createTCP4Thread(NFS, server_settings)
        self.createUDP4Thread(NFS, server_settings)

    def listen(self):
        self.TCP4.start()
        self.UDP4.start()
        while all(map(lambda x: x.isAlive(), [self.TCP4, self.UDP4])):
            time.sleep(1)
