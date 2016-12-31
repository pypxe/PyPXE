import rpcbind
from pypxe import helpers
import threading
import time
import struct
import hashlib
import programs
import stat
import math
import multiprocessing
import multiprocessing.managers
import os

import cProfile
def do_cprofile(func):
    def profiled_func(*args, **kwargs):
        profile = cProfile.Profile()
        try:
            profile.enable()
            result = func(*args, **kwargs)
            profile.disable()
            return result
        finally:
            profile.dump_stats("profiles/{}".format(str(time.time())))
    return profiled_func

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

class NFS(rpcbind.RPCBIND):
    def setup(self):
        self.server_settings = self.server.server_settings
        self.nfsroot = os.path.abspath(self.server_settings["nfsroot"])

    def finish(self):
        # can be used to do UDP caches
        pass

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

        if not self.canread(path, **arguments):
            return RPC.nfsstat3.NFS3ERR_ACCES, {"path": path}

        self.sendnfsresponseOK(self.getattr(path), **arguments)

    def SETATTR(self, body = None, **arguments):
        path = self.extractpath(body)
        if not path: return RPC.nfsstat3.NFS3ERR_BADHANDLE, {"path": path}
        return RPC.nfsstat3.NFS3ERR_ROFS, {"path": path}

        fullfile = helpers.normalize_path(self.nfsroot, path)
        if not os.path.exists(fullfile):
            return RPC.nfsstat3.NFS3ERR_EXIST, {"path": path}

        if not self.canread(fullfile, **arguments):
            return RPC.nfsstat3.NFS3ERR_ACCES, {"path": fullfile}

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

        if not self.canread(fullfile, **arguments):
            return RPC.nfsstat3.NFS3ERR_ACCES, {"path": fullpath}

        resp = struct.pack("!I", 64)
        fh = self.getfh(fullfile)
        if not fh:
            fh = self.addfh(fullfile)
        resp += fh
        resp += struct.pack("!I", 1)
        resp += self.getattr(fullfile)
        resp += struct.pack("!I", 1)
        resp += self.getattr(path)

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

        # need canwrite, canexecute
        if nfsmode & RPC.ACCESS3.ACCESS3_READ:
            mode |= (RPC.ACCESS3.ACCESS3_READ * self.canread(path, **arguments))

        if nfsmode & (RPC.ACCESS3.ACCESS3_MODIFY|RPC.ACCESS3.ACCESS3_EXTEND|RPC.ACCESS3.ACCESS3_DELETE):
            # these three all seem to map to write access
            mode |= ((RPC.ACCESS3.ACCESS3_MODIFY|RPC.ACCESS3.ACCESS3_EXTEND|RPC.ACCESS3.ACCESS3_DELETE) * self.canwrite(path, **arguments))

        if nfsmode & (RPC.ACCESS3.ACCESS3_LOOKUP|RPC.ACCESS3.ACCESS3_EXECUTE):
            mode |= ((RPC.ACCESS3.ACCESS3_LOOKUP|RPC.ACCESS3.ACCESS3_EXECUTE) * self.canexecute(path, **arguments))

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

        # 1 getattr
        resp = struct.pack("!I", 1)
        resp += self.getattr(path)
        resp += self.packstring(os.readlink(path))

        self.sendnfsresponseOK(resp, **arguments)

    def READ(self, body = True, **arguments):
        path = self.extractpath(body)
        if not path: return RPC.nfsstat3.NFS3ERR_BADHANDLE, {"path": path}
        [offset, count] = struct.unpack("!QI", body.read(8+4))
        self.logger.debug("READ({0}) {1} bytes at {2} from {3}".format(path, count, offset, arguments["addr"]))

        if not self.canread(path, **arguments):
            return RPC.nfsstat3.NFS3ERR_ACCES, {"path": path}

        resp = struct.pack("!I", 1)
        resp += self.getattr(path)

        with open(path) as fh:
            fh.seek(offset)
            data = fh.read(count)
            resp += struct.pack("!I", len(data))
            # we can't read any more if we're at eof
            resp += struct.pack("!I", 0 if len(fh.read(1)) else 1)
            resp += struct.pack("!I", len(data))
            resp += data

        self.sendnfsresponseOK(resp, **arguments)
        return

    def WRITE(self, **arguments):
        self.logger.info("WRITE from {0}".format(arguments["addr"]))
        pass
    def CREATE(self, **arguments):
        self.logger.info("CREATE from {0}".format(arguments["addr"]))
        pass
    def MKDIR(self, **arguments):
        self.logger.info("MKDIR from {0}".format(arguments["addr"]))
        pass
    def SYMLINK(self, **arguments):
        self.logger.info("SYMLINK from {0}".format(arguments["addr"]))
        pass
    def MKNOD(self, **arguments):
        self.logger.info("MKNOD from {0}".format(arguments["addr"]))
        pass
    def REMOVE(self, **arguments):
        self.logger.info("REMOVE from {0}".format(arguments["addr"]))
        pass
    def RMDIR(self, **arguments):
        self.logger.info("RMDIR from {0}".format(arguments["addr"]))
        pass
    def RENAME(self, **arguments):
        self.logger.info("RENAME from {0}".format(arguments["addr"]))
        pass
    def LINK(self, **arguments):
        self.logger.info("LINK from {0}".format(arguments["addr"]))
        pass
    def READDIR(self, **arguments):
        self.logger.info("READDIR from {0}".format(arguments["addr"]))
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

        if not self.canexecute(path, **arguments):
            return RPC.nfsstat3.NFS3ERR_ACCES, {"path": path}

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
            direntstat = self.cachestat(dirent)
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
                return self.sendnfsresponse(RPC.nfsstat3.NFS3ERR_TOOSMALL, "", **arguments)
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

        self.sendnfsresponseOK(fullresp, **arguments)

    def FSSTAT(self, **arguments):
        self.logger.info("FSSTAT from {0}".format(arguments["addr"]))
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
        self.logger.info("COMMIT from {0}".format(arguments["addr"]))
        pass

    ############################
    # util functions from here #
    ############################

    def canperm(self, perm, path, **arguments):
        """
        Evaluate a file's permissions against a specific user
        """
        mode = self.getmode(path)
        user, group = self.getowner(path)
        # ordered by scope, so more likely is first ish
        if (perm in ("READ", "WRITE")) and arguments["uid"] == 0:
            # root can rw all
            return True

        perms = {
                "READ": {
                    "other": 0x004,
                    "group": 0x020,
                    "user" : 0x100,
                    },
                "WRITE": {
                    "other": 0x002,
                    "group": 0x010,
                    "user" : 0x080
                    },
                "EXEC": {
                    "other": 0x001,
                    "group": 0x008,
                    "user" : 0x040
                    }
                }

        if   mode & perms[perm]["other"]:
            # o+PERM
            return True
        elif mode & perms[perm]["group"] and (group in arguments["group"] or group == arguments["gid"]):
            # g+PERM
            return True
        elif mode & perms[perm]["user"] and (user == arguments["uid"]):
            # u+PERM
            return True
        else:
            return False

    def canread(self, path, **arguments):
        return self.canperm("READ", path, **arguments)

    def canwrite(self, path, **arguments):
        return self.canperm("WRITE", path, **arguments)

    def canexecute(self, path, **arguments):
        return self.canperm("EXEC", path, **arguments)

    def getowner(self, path):
        """
        Return the user and group for a path
        """
        stat = self.cachestat(path)
        return stat.st_uid, stat.st_gid

    def extractstring(self, body):
        """
        extract a variable length string from a request, and remove padding
        strings are passed as uint32 length, string, padding to 4 byte boundary
        """
        [strlen] = struct.unpack("!I", body.read(4))
        str = body.read(strlen)
        body.read(((4 - (strlen % 4))&~4))
        return str

    def packstring(self, string):
        """
        Opposite of extract string. Return packed length uint32, string and padding to 4 byte
        """
        # string length
        ret = struct.pack("!I", len(string))
        # string itself
        ret += string
        # padding
        ret += "\x00" * ((4 - (len(string) % 4))&~4)
        return ret

    def extractpath(self, body):
        """
        Extract a file handle and turn it into a path
        """
        fh = self.extractstring(body)
        path = self.getpath(fh)

        if path == self.nfsroot:
            return self.nfsroot
        else:
            return helpers.normalize_path(self.nfsroot, path)

    def getfh(self, fh):
        """
        Turn a file handle into a path using the cache
        """
        filehandles = self.server_settings["filehandles"]
        if fh not in filehandles: return {}
        if fh in filehandles and filehandles[fh].get("expires", 0) < time.time():
            del filehandles[fh]
            return {}
        return filehandles[fh]

    def addfh(self, path):
        """
        Turn a path into a file handle using the cache
        """
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
        """
        getfh returns an object, so only return the path component
        """
        return self.getfh(fh).get("path", "")

    def sendnfsresponseOK(self, args, **arguments):
        """
        Function for an NFS3_OK reply
        """
        self.sendnfsresponse(RPC.nfsstat3.NFS3_OK, args, **arguments)

    def sendnfsresponse(self, errno, args, **arguments):
        """
        Send an RPC accepted response. This is ok for errors because they'd be
        NFS errors which are still MSG_SUCCESS
        """
        resp = struct.pack("!I", errno)
        resp += args
        self.makeRPCHeader(resp, RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)

    def gettype(self, path):
        """
        Return the filetype in terms of NFS constants
        """
        mode = self.cachestat(path).st_mode
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
        """
        Return the permissions set for a file
        """
        mode = self.cachestat(path).st_mode
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
        """
        Turn the double time to two uint32s
        """
        i, f = math.modf(time)[::-1]
        while f != 0 and f < 2**32-1: f *= 10
        f /= 10
        return (i, f)

    def cachestat(self, path):
        """
        Caching interface to os.lpath
        """
        # lstat doesn't follow links
        try:
            stat = self.LRUCache(self.server_settings["statcache"], self.server_settings["statcachelock"], path)
            return stat
        except KeyError:
            return self.LRUCache(self.server_settings["statcache"], self.server_settings["statcachelock"], path, os.lstat(path))

    def getattr(self, path):
        """
        Return a fattr3 object for a path
        cached
        """
        try:
            fattr3 = self.LRUCache(self.server_settings["fattr3cache"], self.server_settings["fattr3cachelock"], path)
        except KeyError:
            # return fattr3 RFC1813 p22
            # pathstat = os.lstat(path)
            pathstat = self.cachestat(path)
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
            self.LRUCache(self.server_settings["fattr3cache"], self.server_settings["fattr3cachelock"], path, fattr3)
        return fattr3

    def LRUCache(self, cache, lock, key, value = False):
        """
        Least recently used cache.
        When a value is set/get it is set as the most recently used value
        The first item in the metadata cache is the least mostly recently used
        so can be popped

        cache["metadata"] is an list of keys ordered by use
        cache["maxcacheelems"] is the total number of allowed elements, calculated by specified cache size
        cache[x] is a cached item
        """
        metadata = cache["metadata"]
        if value: # set
            lock.acquire()
            if key not in metadata:
                # check it's not been added by another thread
                cache[key] = value
                metadata.append(key)
                if len(metadata) > cache["maxcacheelems"]:
                    # if the cache is too large, pop and delete the last recently used
                    del cache[metadata.pop(0)]
            cache["metadata"] = metadata
            lock.release()
            # allow functions to just return on this function
            return value
        else: # get
            lock.acquire()
            if key in metadata:
                value = cache[key]
                metadata.remove(key)
                metadata.append(key)
                cache["metadata"] = metadata
                lock.release()
                return value
            else:
                lock.release()
                raise KeyError, key


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

        fattr3cache = manager.dict()
        fattr3cache["metadata"] = []
        fattr3cachelock = manager.Lock()

        statcache = manager.dict()
        statcache["metadata"] = []
        statcachelock = manager.Lock()

        # 144 byte == sys.getsizeof(open("/etc/passwd"))
        cachesize = int(filter(lambda x:x.isdigit(), server_settings["cachesize"]))
        cacheunit = filter(lambda x:not x.isdigit(), server_settings["cachesize"])
        fattr3cache["maxcacheelems"] = (cachesize * {
            "": 1,
            "b": 1,
            "Kb":  1000**1,
            "KiB": 1024**1,
            "Mb" : 1000**2,
            "MiB": 1024**2,
            "Gb":  1000**3,
            "GiB": 1024**3
            }[cacheunit]) / 144

        # 152 byte == sys.getsizeof(os.stat("/"))
        statcache["maxcacheelems"] = (cachesize * {
            "": 1,
            "b": 1,
            "Kb":  1000**1,
            "KiB": 1024**1,
            "Mb" : 1000**2,
            "MiB": 1024**2,
            "Gb":  1000**3,
            "GiB": 1024**3
            }[cacheunit]) / 152

        self.nfsroot = os.path.abspath(server_settings.get('nfsroot', 'nfsroot'))
        filehandles[hashlib.sha256(self.nfsroot).hexdigest()] = {"path": self.nfsroot, "expires": float("inf")}

        server_settings["filehandles"] = filehandles
        server_settings["fattr3cache"] = fattr3cache
        server_settings["fattr3cachelock"] = fattr3cachelock
        server_settings["statcache"] = statcache
        server_settings["statcachelock"] = statcachelock


        self.createTCP4Thread(NFS, server_settings)
        self.createUDP4Thread(NFS, server_settings)

    def listen(self):
        self.TCP4.start()
        self.UDP4.start()
        while all(map(lambda x: x.isAlive(), [self.TCP4, self.UDP4])):
            time.sleep(1)