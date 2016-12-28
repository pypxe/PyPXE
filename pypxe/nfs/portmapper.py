import logging
import socket
import rpcbind
import RPCExceptions
import struct
import threading
import time
from pypxe import helpers

def padtomultiple(string, boundary):
    while len(string) % boundary:
        string += "\x00"
    return string

class RPC(rpcbind.RPCBase):
    class PMAPPROC:
        NULL    = 0
        SET     = 1
        UNSET   = 2
        GETADDR = 3
        DUMP    = 4

    class MOUNT_PROC:
        NULL    = 0
        MNT     = 1
        DUMP    = 2
        UMNT    = 3
        UMNTALL = 4
        EXPORT  = 5

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

    class IPPROTO:
        IPPROTO_TCP4 = "tcp4"
        IPPROTO_UDP4 = "udp4"

class PORTMAPPER(rpcbind.RPCBIND):
    def __init__(self, **server_settings):
        # should be swappable for real rpcbind
        self.mode_verbose = server_settings.get('mode_verbose', False) # verbose mode
        self.mode_debug = server_settings.get('mode_debug', False) # debug mode
        self.logger = server_settings.get('logger', None)

        # setup logger
        if self.logger == None:
            self.logger = logging.getLogger('PORTMAPPER.{0}'.format(self.PROTO))
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

        self.programs = server_settings["programs"]

    def process(self, **arguments):
        PORTMAPPERPROCS = {
            RPC.PMAPPROC.NULL : self.NULL,
            RPC.PMAPPROC.SET : self.SET,
            RPC.PMAPPROC.UNSET : self.UNSET,
            RPC.PMAPPROC.GETADDR : self.GETADDR,
            RPC.PMAPPROC.DUMP : self.DUMP
        }
        PORTMAPPERPROCS[arguments["proc"]](**arguments)

    def NULL(self, **arguments):
        self.makeRPCHeader("", RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)
        pass
    def SET(self, **arguments):
        print "SET"
        pass
    def UNSET(self, **arguments):
        print "UNSET"
        pass
    def GETADDR(self, **arguments):
        body = arguments["body"]
        [
            program,
            version,
            proto,
            port
        ] = struct.unpack("!IIII", body.read(4*4))
        if program in self.programs:
            self.makeRPCHeader(
                    struct.pack("!I", self.programs[program]["port"]),
                    RPC.reply_stat.MSG_ACCEPTED,
                    RPC.accept_stat.SUCCESS,
                    **arguments)
        else:
            raise RPCExceptions.RPC_PROG_UNAVAIL, arguments["xid"]


    def DUMP(self, **arguments):
        mappings = []
        for program in self.programs:
            for version in self.programs[program]["version"]:
                mapping = struct.pack(
                        "!II",
                        program,
                        version
                        )
                if arguments["vers"] == 3:
                    protocol = padtomultiple(self.programs[program]["protocol"], 4)
                    r_addr = padtomultiple("{address}.{port}".format(**self.programs[program]), 4)
                    owner = padtomultiple(self.programs[program]["owner"], 4)

                    # auto pad to 4 byte boundaries
                    mapping += struct.pack("!I", len(protocol)) + protocol
                    mapping += struct.pack("!I", len(r_addr)) + r_addr
                    mapping += struct.pack("!I", len(owner)) + owner

                elif arguments["vers"] == 2:
                    mapping += struct.pack("!I", 6 if self.programs[program]["protocol"] == RPC.IPPROTO.IPPROTO_TCP4 else 17)
                    mapping += struct.pack("!I", self.programs[program]["port"])

                mappings.append(mapping)
        # value follows == 0x00000001
        resp = struct.pack("!I", 1)
        resp += struct.pack("!I", 1).join(mappings)
        # no value follows == 0x00000000
        resp += struct.pack("!I", 0)
        self.makeRPCHeader(resp, RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)

class PORTMAPPERTCP(PORTMAPPER):
    def __init__(self, **server_settings):
        PORTMAPPER.__init__(self, **server_settings)
        self.PROTO = "TCP"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.programs[100000]["address"], self.programs[100000]["port"]))
        self.sock.listen(4)

class PORTMAPPERUDP(PORTMAPPER):
    def __init__(self, **server_settings):
        PORTMAPPER.__init__(self, **server_settings)
        self.PROTO = "UDP"
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.programs[100000]["address"], self.programs[100000]["port"]))

class PORTMAPPERD:
    def __init__(self, **server_settings):
        self.pipe = server_settings["pipe"]
        self.logger = server_settings.get('logger', None)

        self.programs = {
                100000: { # portmapper
                        "version": [2, 3],
                        "procedures": [
                            RPC.PMAPPROC.NULL,
                            RPC.PMAPPROC.SET,
                            RPC.PMAPPROC.UNSET,
                            RPC.PMAPPROC.GETADDR,
                            RPC.PMAPPROC.DUMP
                        ],
                        "protocol": RPC.IPPROTO.IPPROTO_TCP4,
                        "port": 111,
                        "owner": "superuser",
                        "address": "0.0.0.0"
                    },
                100003: { # mountd
                        "version": [3],
                        "procedures": [
                            RPC.NFS_PROC.NFSPROC3_NULL,
                            RPC.NFS_PROC.NFSPROC3_GETATTR,
                            RPC.NFS_PROC.NFSPROC3_SETATTR,
                            RPC.NFS_PROC.NFSPROC3_LOOKUP,
                            RPC.NFS_PROC.NFSPROC3_ACCESS,
                            RPC.NFS_PROC.NFSPROC3_READLINK,
                            RPC.NFS_PROC.NFSPROC3_READ,
                            RPC.NFS_PROC.NFSPROC3_WRITE,
                            RPC.NFS_PROC.NFSPROC3_CREATE,
                            RPC.NFS_PROC.NFSPROC3_MKDIR,
                            RPC.NFS_PROC.NFSPROC3_SYMLINK,
                            RPC.NFS_PROC.NFSPROC3_MKNOD,
                            RPC.NFS_PROC.NFSPROC3_REMOVE,
                            RPC.NFS_PROC.NFSPROC3_RMDIR,
                            RPC.NFS_PROC.NFSPROC3_RENAME,
                            RPC.NFS_PROC.NFSPROC3_LINK,
                            RPC.NFS_PROC.NFSPROC3_READDIR,
                            RPC.NFS_PROC.NFSPROC3_READDIRPLUS,
                            RPC.NFS_PROC.NFSPROC3_FSSTAT,
                            RPC.NFS_PROC.NFSPROC3_FSINFO,
                            RPC.NFS_PROC.NFSPROC3_PATHCONF,
                            RPC.NFS_PROC.NFSPROC3_COMMIT
                        ],
                        "protocol": RPC.IPPROTO.IPPROTO_TCP4,
                        "port": 2049,
                        "owner": "superuser",
                        "address": "0.0.0.0"
                    },
                100005: { # mountd
                        "version": [3],
                        "procedures": [
                            RPC.MOUNT_PROC.NULL,
                            RPC.MOUNT_PROC.MNT,
                            RPC.MOUNT_PROC.DUMP,
                            RPC.MOUNT_PROC.UMNT,
                            RPC.MOUNT_PROC.UMNTALL,
                            RPC.MOUNT_PROC.EXPORT
                        ],
                        "protocol": RPC.IPPROTO.IPPROTO_TCP4,
                        "port": 635,
                        "owner": "superuser",
                        "address": "0.0.0.0"
                    }
                }
        server_settings["programs"] = self.programs

        tcp_settings = server_settings
        tcp_settings["logger"] = helpers.get_child_logger(self.logger, "TCP")
        TCP = PORTMAPPERTCP(**tcp_settings)

        udp_settings = server_settings
        udp_settings["logger"] = helpers.get_child_logger(self.logger, "UDP")
        UDP = PORTMAPPERUDP(**udp_settings)

        self.TCP = threading.Thread(target = TCP.listen)
        self.TCP.daemon = True
        self.UDP = threading.Thread(target = UDP.listen)
        self.UDP.daemon = True

    def listen(self):
        self.TCP.start()
        self.UDP.start()
        while all(map(lambda x: x.isAlive(), [self.TCP, self.UDP])):
            if self.pipe.poll(1):
                rpcnumber = self.pipe.recv()
                self.pipe.send(self.programs[rpcnumber])
            time.sleep(1)
