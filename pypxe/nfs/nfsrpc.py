import operations
import struct
import socket

class Request:
    class credentials:
        pass

    class verifier:
        pass

    def __init__(self, request, connection, addr, state):
        self.connection = connection
        self.addr = addr
        self.state = state

        fmt =  "!" #Network byte order
        fmt += "I" #Fragment Header
        fmt += "I" #xid
        fmt += "I" #msg type (0)
        fmt += "I" #rpcver (2)
        fmt += "I" #prog (100003)
        fmt += "I" #vers (4)
        fmt += "I" #procedure (0 NULL/1 COMPOUND)
        [self.frag,
        self.xid,
        self.msgtype,
        self.rpcver,
        self.prog,
        self.vers,
        self.proc
        ] = struct.unpack(fmt,request[:7*4])
        if not sum([self.msgtype == 0,
              self.rpcver == 2,
              self.prog == 100003,
              self.vers == 4,
              self.proc in (0,1)]) == 5:
            return
        request = request[7*4:]

        #Credentials, uint flavor, uint length followed by opaque length bytes
        [self.credentials.flavor,
        self.credentials.length
        ] = struct.unpack("!II", request[:2*4])
        request = request[2*4:]
        self.credentials.opaque = request[:self.credentials.length]
        request = request[self.credentials.length:]

        #See Credentials
        [self.verifier.flavor,
        self.verifier.length
        ] = struct.unpack("!II", request[:2*4])
        request = request[2*4:]
        self.verifier.opaque = request[:self.verifier.length]
        request = request[self.verifier.length:]

        #NULL procedure, sometimes used for overhead measurement
        if self.proc == 0:
            self.null()
            return

        #COMPOUND procedure, all other actions
        #Tag. RFC665-16.2.3, implementation defined, must respond matching
        [self.taglen] = struct.unpack("!I", request[:4])
        request = request[4:]
        self.tag = request[:self.taglen]
        request = request[self.taglen:]

        self.minorversion = struct.unpack("!I", request[:4])
        request = request[4:]

        [self.operations] = struct.unpack("!I", request[:4])
        request = request[4:]

        #Operations can take a variable length input
        #This should be implemented inside the operation
        #function, and they MUST clean up the response properly
        #This is the pramble. NFS4_OK (0) should probably be handled properly
        response =  struct.pack("!II", 0, self.taglen)
        response += self.tag
        response += struct.pack("!I", self.operations)
        [operation] = struct.unpack("!I", request[:4])
        if operation == 53: #SEQUENCE, loops for us
            request, response = self.dispatch(request, response)
            self.send(response)
        else:
            for _ in xrange(self.operations):
                request, response = self.dispatch(request, response)
                self.send(response)

    def null(self):
        #RFC5661-16.1
        #We're not allowed to do anything here
        #XID, msgtype = reply, replystate = accepted
        response = struct.pack("!III", self.xid, 1, 0)
        #Verifier AUTH_NULL
        response += struct.pack("!II", 0, 0)
        #RPC Success
        response += struct.pack("!I", 0)
        #Fragmentation header, 1<<31 == last fragment yes
        fraghdr = 1<<31 | len(response)
        response = struct.pack("!I", fraghdr) + response
        self.connection.send(response)
        self.connection.close()

    def dispatch(self, request, response):
        [operation] = struct.unpack("!I", request[:4])
        request = request[4:]
        print operation, operations.nfs_opnum4[operation].__name__
        #Will recurse on SEQUENCE, functions append to request
        request, response = operations.nfs_opnum4[operation](request, response, self.state)
        return request, response

    def send(self, response):
        preresponse = struct.pack("!III", self.xid, 1, 0)
        #Verifier AUTH_NULL
        preresponse += struct.pack("!II", 0, 0)
        #RPC Success
        preresponse += struct.pack("!I", 0)
        #Fragmentation header, 1<<31 == last fragment yes
        fraghdr = 1<<31 | len(preresponse+response)
        response = struct.pack("!I", fraghdr) + preresponse + response
        self.connection.send(response)
        self.connection.close()


class NFS:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', 2049)) #RFC5661-2.9.3
        self.sock.listen(1)
        #Global state info.
        self.state = {}

    def handleRequest(self, connection, addr):
        data = connection.recv(8192)
        Request(data, connection, addr, self.state)

    def listen(self):
        while True:
            conn, addr = self.sock.accept()
            self.handleRequest(conn, addr)
