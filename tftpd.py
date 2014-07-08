import socket, struct, os
from collections import defaultdict

class TFTPD:
    """tftp server, read only. Implemented from
    rfc1350 and rfc2348"""
    def __init__(self, ip = '', port = 69):
        self.ip = ip
        self.port = port
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))
        #key is (address, port) pair
        self.ongoing = defaultdict(lambda:{"filename":'', "handle":None, "block":1})
        os.chroot('.')

    def filename(self, message):
        """First null delimited field after opcode
        is the filename.
        returns filename from message"""
        return message[2:].split("\x00")[0]
    
    def notfound(self, address):
        """short int 5 == Error
        short int 1 == File not found.
        Send message to client"""
        response =  struct.pack("!H", 5) #Error code
        response += struct.pack("!H", 1) #File not found
        response += "File Not Found"
        self.sock.sendto(response, address)

    def sendblock(self, address, initial):
        """short int 3 == data block"""
        if initial: #need to send tsize first. rfc2349
            response =  struct.pack("!H7sB3sB5sB", 6, "blksize", 0, "512", 0, "tsize", 0)
            response += str(os.path.getsize(self.ongoing[address]['filename']))
            response += "\x00"
            self.sock.sendto(response, address)
            return
        descriptor = self.ongoing[address]
        response =  struct.pack("!H", 3) #Data
        response += struct.pack("!H", descriptor['block']) #This block id
        data = descriptor["handle"].read(512)
        response += data
        self.sock.sendto(response, address)
        if len(data) != 512:
            descriptor['handle'].close()
            print "tftp://%s -> %s:%d" % (descriptor['filename'], address[0], address[1])
            self.ongoing.pop(address)
        else:
            descriptor['block'] += 1

    def read(self, address, message):
        """On RRQ opcode, reply with file if
        exists, else error"""
        filename = self.filename(message)
        if not os.path.exists(filename):
            self.notfound(address)
            return
        self.ongoing[address]['filename'] = filename
        self.ongoing[address]['handle'] = open(filename, "r")
        self.sendblock(address, True)

    def listen(self):
        """Main listen loop"""
        while True:
            message, address = self.sock.recvfrom(1024)
            opcode = struct.unpack("!H", message[:2])[0]
            if opcode == 1: #Read request
                self.read(address, message)
            if opcode == 4:
                if self.ongoing.has_key(address):
                    self.sendblock(address, False)
