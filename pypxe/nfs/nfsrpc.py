import operations
import struct

class Request:
    class cred:
        def __init__(self, data):
            [self.flavor,
                    self.length] = struct.unpack("II", data[:8])
            self.data = data[8:] #opaque

    class verf(cred):
        pass

    def __init__(self, request):
        assert(struct.unpack("i", request[:4]) == 0, "Invalid msg_type in Request class")
        [self.msg_type, #Signed int per RFC4506 4.3
                self.xid, #uint
                self.rpcvers, #uint
                self.prog, #uint
                self.proc #uint
                ] = struct.unpack("iIIII", request[:5*4])
        #[u]int defined as 32-bit in RFC4506 4.1/2
        request = request[5*4:]

        credlen = struct.unpack("xxxxI")[0]
        self.cred = cred(request[:credlen+8]) #include flavor & length
        request = request[credlen+8:]

        verflen = struct.unpack("xxxxI")[0]
        self.verf = verf(request[request[:verflen+8]])
        request = request[verflen+8:]

        taglen = struct.unpack("I")[0]
        self.tag = request[4:taglen+4]
        request = request[taglen+4:]

        [self.minorversion, #uint
                self.opcount #uint
                ] = struct.unpack("II", request[:2*4])

        self.ops = []

        for op in xrange(self.opcount):
            opcode, length = struct.unpack("II", request[:2*4])
            self.ops.append((opcode, length, request[2*4:2*4+length]))
            request = request[2*4+length:]
