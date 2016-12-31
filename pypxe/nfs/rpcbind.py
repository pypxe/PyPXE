import struct
import StringIO
from pypxe import helpers
import threading
import select
import socket
import random
import SocketServer
import logging
from multiprocessing.pool import ThreadPool

class RPCBase:
    """For Constants from RFC1057"""
    class msg_type:
        CALL  = 0
        REPLY = 1

    VERSION2 = 2

    class reply_stat:
        MSG_ACCEPTED = 0
        MSG_DENIED   = 1

    class accept_stat:
        SUCCESS       = 0 # RPC executed successfully
        PROG_UNAVAIL  = 1 # remote hasn't exported program
        PROG_MISMATCH = 2 # remote can't support version #
        PROC_UNAVAIL  = 3 # program can't support procedure
        GARBAGE_ARGS  = 4 # procedure can't decode params

    class reject_stat:
        RPC_MISMATCH = 0 # RPC version number != 2
        AUTH_ERROR   = 1   # remote can't authenticate caller

    class auth_flavor:
        AUTH_NULL  = 0
        AUTH_UNIX  = 1
        AUTH_SHORT = 2
        AUTH_DES   = 3

    class auth_stat:
        AUTH_BADCRED      = 1  # bad credentials (seal broken)
        AUTH_REJECTEDCRED = 2  # client must begin new session
        AUTH_BADVERF      = 3  # bad verifier (seal broken)
        AUTH_REJECTEDVERF = 4  # verifier expired or replayed
        AUTH_TOOWEAK      = 5  # rejected for security reasons

    class PORTMAPPER:
        VERSION = 2
        PROGRAM = 100000
        SET     = 1
        UNSET   = 2

class RPCBIND(SocketServer.BaseRequestHandler):
    def __init__(self, *args, **kwargs):
        [_, self.client_address, _] = args
        SocketServer.BaseRequestHandler.__init__(self, *args, **kwargs)

    # skip registration. Used for portmapper itself
    autoregister = True
    def handle(self):
        self.server_settings = self.server.server_settings
        self.PROTO = self.server_settings["PROTO"]
        self.programs = self.server_settings["programs"]
        self.logger = self.server_settings["logger"]
        """
        RFC1057 compliant RPC
        """
        if isinstance(self.request, socket.socket):
            # tcp
            conn = self.request
            addr = self.client_address
        else:
            addr = self.client_address
            data, conn = self.request

        while True:
            if self.PROTO == "TCP":
                data = ""
                while len(data) != 4:
                    [conn], _, _ = select.select([conn], [], [])
                    thisdata = conn.recv(4)
                    if not thisdata:
                        self.logger.debug("Client disconnected")
                        return
                    data += thisdata
                [fragheader] = struct.unpack("!I", data)

                # fragheader TCP only
                lastfragment = bool(fragheader & (1 << 31))
                length = fragheader & ~(1 << 31)

                # use StringIO so the string acts like a file, we can .read()
                # it and we don't have to do any horrible x = x[n:]
                req = StringIO.StringIO(conn.recv(length))
            else:
                req = StringIO.StringIO(data)

            [xid] = struct.unpack("!I", req.read(4))
            [msg_type] = struct.unpack("!I", req.read(4))
            if msg_type != RPCBase.msg_type.CALL: return

            [
                rpcvers,
                prog,
                vers,
                proc
            ] = struct.unpack("!IIII", req.read(4*4))

            if rpcvers != RPCBase.VERSION2:
                self.makeRPCHeader("", RPCBase.reply_stat.MSG_DENIED, RPCBase.reject_stat.RPC_MISMATCH, xid = xid, sock = conn, addr = addr)
                if self.PROTO == "UDP": break
                else: continue
            if prog not in self.programs or not self.programs[prog]["port"]:
                self.makeRPCHeader("", RPCBase.reply_stat.MSG_ACCEPTED, RPCBase.accept_stat.PROG_UNAVAIL, xid = xid, sock = conn, addr = addr)
                if self.PROTO == "UDP": break
                else: continue
            if vers not in self.programs[prog]["version"]:
                self.logger.debug("Bumping client version due to PROG_MISMATCH")
                self.makeRPCHeader("", RPCBase.reply_stat.MSG_ACCEPTED, RPCBase.accept_stat.PROG_MISMATCH, xid = xid, prog = prog, sock = conn, addr = addr)
                if self.PROTO == "UDP": break
                else: continue
            if proc not in self.programs[prog]["procedures"]:
                self.makeRPCHeader("", RPCBase.reply_stat.MSG_ACCEPTED, RPCBase.accept_stat.PROC_UNAVAIL, xid = xid, sock = conn, addr = addr)
                if self.PROTO == "UDP": break
                else: continue

            [
                auth_type,
                authlength
            ] = struct.unpack("!II", req.read(2*4))

            if auth_type not in (RPCBase.auth_flavor.AUTH_NULL, RPCBase.auth_flavor.AUTH_UNIX):
                self.makeRPCHeader("", RPCBase.reply_stat.MSG_DENIED, RPCBase.reject_stat.AUTH_ERROR, xid = xid, sock = conn, addr = addr)
                if self.PROTO == "UDP": break
                else: continue

            if auth_type == RPCBase.auth_flavor.AUTH_UNIX:
                [stamp,
                    machinenamelen
                    ] = struct.unpack("!II", req.read(4*2))
                machinename = req.read(machinenamelen)
                req.read((4 - (machinenamelen % 4))&~4)
                [uid,
                    gid,
                    groupcount
                    ] = struct.unpack("!III", req.read(4*3))
                groups = struct.unpack("!{0}I".format(groupcount), req.read(4*groupcount))

                creds = {"uid": uid, "gid": gid, "groups": groups}
            else:
                auth_body = req.read(authlength)
                creds = {"auth_body": auth_body}

            [
                verf_type,
                verflength
            ] = struct.unpack("!II", req.read(2*4))
            verf_body = req.read(verflength)

            self.process(
                xid = xid,
                rpcvers = rpcvers,
                prog = prog,
                vers = vers,
                proc = proc,
                auth_type = auth_type,
                verf_type = verf_type,
                verf_body = verf_body,
                sock = conn,
                body = req,
                addr = addr,
                **creds
            )
            if self.PROTO == "UDP": break

    def makeRPCHeader(self, data, reply_stat, state, **extra):
        resp  = struct.pack("!I", extra["xid"])
        resp += struct.pack("!I", RPCBase.msg_type.REPLY)
        # state in RPCBase.reply_stat
        resp += struct.pack("!I", reply_stat)
        if reply_stat == RPCBase.reply_stat.MSG_ACCEPTED:
            # verf
            resp += struct.pack("!II", RPCBase.auth_flavor.AUTH_NULL, 0)
        # accept or reject state in RPCBase.{accept_stat, reject_stat}
        resp += struct.pack("!I", state)

        if reply_stat == RPCBase.reply_stat.MSG_ACCEPTED:
            if state == RPCBase.accept_stat.SUCCESS:
                # data is appended later on
                pass
            elif state == RPCBase.accept_stat.PROG_MISMATCH:
                prog = extra.get("prog", [3])
                resp += struct.pack("!II", min(self.programs[prog]["version"]), max(self.programs[prog]["version"]))
            else:
                # RPCBase.accept_stat.PROC_UNAVAIL,
                # RPCBase.accept_stat.PROG_UNAVAIL,
                # RPCBase.accept_stat.GARBAGE_ARGS
                pass
        else:
            # MSG_DENIED
            if state == RPCBase.reject_stat.RPC_MISMATCH:
                resp += struct.pack("!II", 2, 2)
            elif state == RPCBase.reject_stat.AUTH_ERROR:
                resp += struct.pack("!I", extra.get("auth_stat", 0))

        resp += data
        sock = extra["sock"]
        if self.PROTO == "TCP" or extra.get("register", False):
            # fragment header goes at the start
            resp = struct.pack("!I", len(resp)|(1<<31)) + resp
            sock.send(resp)
        else:
            sock.sendto(resp, extra["addr"])

    # used externally
    @staticmethod
    def portmapper(rpcnumber, version, protocol, port, register = True):
        portmapper = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        portmapper.connect(("127.0.0.1", 111))
        # prog, vers, proto, port
        req  = struct.pack("!I", random.getrandbits(4))
        req += struct.pack("!I", RPCBase.msg_type.CALL)
        # RPC version
        req += struct.pack("!I", 2)
        # target program and version
        req += struct.pack("!II", RPCBase.PORTMAPPER.PROGRAM, RPCBase.PORTMAPPER.VERSION)
        # procedure
        req += struct.pack("!I", RPCBase.PORTMAPPER.SET if register else RPCBase.PORTMAPPER.UNSET)
        # auth
        req += struct.pack("!II", RPCBase.auth_flavor.AUTH_NULL, 0)
        # verf
        req += struct.pack("!II", RPCBase.auth_flavor.AUTH_NULL, 0)
        req += struct.pack("!IIII", rpcnumber, version, protocol, port)
        req = struct.pack("!I", len(req)|(1<<31)) + req
        portmapper.send(req)

    def registerPort(self, rpcnumber, version, protocol, port):
        self.portmapper(rpcnumber, version, protocol, port, True)

    def deregisterPort(self, rpcnumber, version, protocol, port):
        self.portmapper(rpcnumber, version, protocol, port, False)

# the following *significantly* speeds everything up, at least for UDP
# maybe we can use ThreadPool somehow for TCP connections?
class PooledThreadingMixIn:
    """Mix-in class to handle each request in a new thread.
    Taken from SocketServer.py, modified to use a thread pool
    """

    # Decides how threads will act upon termination of the
    # main process
    daemon_threads = False

    def __init__(self, threadcount = 8):
        self.pool = ThreadPool(threadcount)

    def process_request_thread(self, request, client_address):
        """Same as in BaseServer but as a thread.

        In addition, exception handling is done here.

        """
        try:
            self.finish_request(request, client_address)
            self.shutdown_request(request)
        except:
            self.handle_error(request, client_address)
            self.shutdown_request(request)

    def process_request(self, request, client_address):
        """Start a new thread to process the request."""
        self.pool.apply_async(self.process_request_thread, (request, client_address))

class serverTCP(PooledThreadingMixIn, SocketServer.TCPServer):
    allow_reuse_address = True
    def __init__(self, server_address, RequestHandlerClass, logger):
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass)
        PooledThreadingMixIn.__init__(self, threadcount = 8)
        self.RequestHandlerClass = RequestHandlerClass
        self.logger = logger

    def serve_forever(self):
        if self.RequestHandlerClass.autoregister:
            for version in self.server_settings["programs"][self.server_settings["rpcnumber"]]["version"]:
                self.RequestHandlerClass.portmapper(self.server_settings["rpcnumber"],
                        version,
                        6, # TCP
                        self.server_address[1])
        self.logger.info("Started")
        SocketServer.TCPServer.serve_forever(self)

class serverUDP(PooledThreadingMixIn, SocketServer.UDPServer):
    allow_reuse_address = True
    def __init__(self, server_address, RequestHandlerClass, logger):
        SocketServer.UDPServer.__init__(self, server_address, RequestHandlerClass)
        PooledThreadingMixIn.__init__(self, threadcount = 8)
        self.logger = logger

    def serve_forever(self):
        if self.RequestHandlerClass.autoregister:
            for version in self.server_settings["programs"][self.server_settings["rpcnumber"]]["version"]:
                self.RequestHandlerClass.portmapper(self.server_settings["rpcnumber"],
                        version,
                        17, # UDP
                        self.server_address[1])
        self.logger.info("Started")
        SocketServer.UDPServer.serve_forever(self)

class DAEMON:
    def createTCP4Thread(self, target, server_settings):
        if server_settings["mode_debug"]:
            self.logger.setLevel(logging.DEBUG)
        elif server_settings["mode_verbose"]:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.WARN)

        tcp_settings = server_settings.copy()
        tcp_settings.update({"PROTO": "TCP", "logger": helpers.get_child_logger(self.logger, "TCP")})
        TCP4 = serverTCP((self.addr, self.port), target, tcp_settings["logger"])
        TCP4.server_settings = tcp_settings
        self.TCP4 = threading.Thread(target = TCP4.serve_forever)
        self.TCP4.daemon = True

    def createUDP4Thread(self, target, server_settings):
        if server_settings["mode_debug"]:
            self.logger.setLevel(logging.DEBUG)
        elif server_settings["mode_verbose"]:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.WARN)

        udp_settings = server_settings.copy()
        udp_settings.update({"PROTO": "UDP", "logger": helpers.get_child_logger(self.logger, "UDP")})
        UDP4 = serverUDP((self.addr, self.port), target, udp_settings["logger"])
        UDP4.server_settings = udp_settings
        self.UDP4 = threading.Thread(target = UDP4.serve_forever)
        self.UDP4.daemon = True
