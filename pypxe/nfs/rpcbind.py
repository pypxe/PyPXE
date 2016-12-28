import struct
import StringIO
import sys
from pypxe import helpers
import traceback
import RPCExceptions
import threading
import select
import socket

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

class RPCBIND:
    def listen(self):
        if self.PROTO == "TCP":
            while True:
                conn, addr = self.sock.accept()
                client = threading.Thread(target = self.handle, args=(conn, addr))
                client.daemon = True
                client.start()
        else:
            while True:
                # don't need to thread UDP because only one socket.
                rlist, _, _ = select.select([self.sock], [], [], 1)
                if not rlist: continue
                self.handle(self.sock)

    # overwritten by NFS to keep connections alive
    keepalive = False
    def handle(self, conn, addr = None):
        # will become not null later if this is a UDP connection
        self.addr = addr
        while True:
            # overwritten if we have an error, otherwise stays False
            retried = False
            try:
                self.parse(conn)
            except RPCExceptions.RPC_MISMATCH as e:
                self.makeRPCHeader("", RPCBase.reply_stat.MSG_DENIED, RPCBase.reject_stat.RPC_MISMATCH, xid = e.args[0], sock = conn)
            except (RPCExceptions.RPC_PROG_UNAVAIL, RPCExceptions.RPC_PROC_UNAVAIL) as e:
                exceptionmap = {
                        RPCExceptions.RPC_PROG_UNAVAIL: RPCBase.accept_stat.PROG_UNAVAIL,
                        RPCExceptions.RPC_PROC_UNAVAIL: RPCBase.accept_stat.PROC_UNAVAIL
                        }
                self.makeRPCHeader("", RPCBase.reply_stat.MSG_ACCEPTED, exceptionmap[e.__class__], xid = e.args[0], sock = conn)
            except RPCExceptions.AUTH_ERROR as e:
                self.makeRPCHeader("", RPCBase.reply_stat.MSG_DENIED, RPCBase.reject_stat.AUTH_ERROR, xid = e.args[0], auth_stat = e.args[1], sock = conn)
            except RPCExceptions.PROG_MISMATCH as e:
                self.makeRPCHeader("", RPCBase.reply_stat.MSG_ACCEPTED, RPCBase.accept_stat.PROG_MISMATCH, xid = e.args[0], prog = e.args[1], sock = conn)
                # recurse just incase the client reuses the socket to bump version
                # makes the log in the wrong order
                self.logger.debug("Bumping client version due to PROG_MISMATCH")
                self.keepalive = True
            except RPCExceptions.CLIENT_GAVE_UP:
                    self.logger.debug("Client disappeared on retry")
                    conn.close()
                    return
            # except Exception as e:
                # all other errors are just logged
                # when this class is subclassed, the parent class MUST handle their
                # own errors. i.e send a response but NOT close the socket.
                # pass
            if self.keepalive:
                # loop forever if keepalive
                # used for NFS
                continue
            if not self.keepalive: break

    def parse(self, conn):
        """
        RFC1057 compliant RPC
        """
        if self.PROTO == "TCP":
            if self.keepalive:
                data = ""
                while len(data) != 4:
                    [conn], _, _ = select.select([conn], [], [])
                    data += conn.recv(4, socket.MSG_WAITALL)
                [fragheader] = struct.unpack("!I", data)
            else:
                conn.settimeout(3)
                try:
                    data = conn.recv(4, socket.MSG_WAITALL)
                    if not data:
                        # client closed on us
                        raise RPCExceptions.CLIENT_GAVE_UP
                    [fragheader] = struct.unpack("!I", data)
                except socket.timeout:
                    # probably second run, client didn't want to try again on the same socket
                    raise RPCExceptions.CLIENT_GAVE_UP

            # no fragheader in UDP
            lastfragment = bool(fragheader & (1 << 31))
            length = fragheader & ~(1 << 31)

            # use StringIO so the string acts like a file, we can .read()
            # it and we don't have to do any horrible x = x[n:]
            req = StringIO.StringIO(conn.recv(length))
        else:
            data, addr = conn.recvfrom(256)
            self.addr = addr
            req = StringIO.StringIO(data)

        [xid] = struct.unpack("!I", req.read(4))
        [msg_type] = struct.unpack("!I", req.read(4))
        if msg_type != RPCBase.msg_type.CALL: raise RPCException.INCORRECT_MSG_TYPE

        [
            rpcvers,
            prog,
            vers,
            proc
        ] = struct.unpack("!IIII", req.read(4*4))
        if rpcvers != RPCBase.VERSION2: raise RPCExceptions.RPC_MISMATCH, xid
        if prog not in self.programs: raise RPCExceptions.RPC_PROG_UNAVAIL, xid
        if vers not in self.programs[prog]["version"]: raise RPCExceptions.PROG_MISMATCH, (xid, prog)
        if proc not in self.programs[prog]["procedures"]: raise RPCExceptions.RPC_PROC_UNAVAIL, xid

        [
            auth_type,
            authlength
        ] = struct.unpack("!II", req.read(2*4))

        if auth_type not in (RPCBase.auth_flavor.AUTH_NULL, RPCBase.auth_flavor.AUTH_UNIX): raise RPCExceptions.AUTH_ERROR, (xid, RPCBase.auth_stat.AUTH_REJECTEDCRED)

        auth_body = req.read(authlength)

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
            auth_body = auth_body,
            verf_type = verf_type,
            verf_body = verf_body,
            sock = conn,
            body = req,
            addr = self.addr
        )

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
        if self.PROTO == "TCP":
            # fragment header goes at the start
            resp = struct.pack("!I", len(resp)|(1<<31)) + resp
            sock.send(resp)
        else:
            sock.sendto(resp, self.addr)
