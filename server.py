import socket
import struct
import os
from collections import defaultdict
from time import time, sleep
import threading

class TFTPD:
    """tftp server, read only. Implemented from
    http://www.ietf.org/rfc/rfc1350.txt"""
    def __init__(self, ip = '', port = 69):
        self.ip = ip
        self.port = port
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))
        #key is (address, port) pair
        self.ongoing = defaultdict(lambda:{"filename":'', "handle":None, "block":1})


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
            print "%s -> %s:%d" % (descriptor['filename'], address[0], address[1])
            self.ongoing.pop(address)
        else:
            descriptor['block'] += 1

    def read(self, address, message):
        """On RRQ opcode, reply with file if
        exists, else error"""
        filename = self.filename(message)
        if filename.startswith('/'):
            filename = '.'+filename
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

class DHCPD:
    """dhcp server, limited to pxe options.
    /24 Hard coded.
    Implemented from
    http://www.ietf.org/rfc/rfc2131.txt and
    https://en.wikipedia.org/wiki/Dynamic_Host_Configuration_Protocol
    https://tools.ietf.org/html/rfc2132"""
    def __init__(self, tftpserver, offerfrom, offerto, subnetmask, router, dnsserver, filename, ip, port = 67):
        self.ip = ip
        self.port = port
        self.tftpserver = tftpserver
        self.offerfrom = offerfrom
        self.offerto = offerto
        self.subnetmask = subnetmask
        self.router = router
        self.dnsserver = dnsserver
        self.filename = filename
        self.magic = struct.pack("!I", 0x63825363) #magic cookie

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', self.port))
        #key is mac
        self.leases = defaultdict(lambda:{'ip':'', 'expire':0})

    def nextip(self):
        """return the next unleased ip from range"""
        network = '.'.join(self.offerfrom.split('.')[:-1])
        fromhost = int(self.offerfrom.split('.')[-1])
        tohost = int(self.offerto.split('.')[-1])
        leased = [self.leases[i]['ip'] for i in self.leases]
        for host in xrange(fromhost, tohost+1):
            if network+"."+str(host) not in leased:
                return network+"."+str(host)

    def timeoutleases(self):
        """remove expired leases for reuse"""
        for lease in self.leases:
            if self.leases[lease]['expire'] < time():
                self.leases.pop(lease)

    def packip(self, ip):
        """NBO the str ip"""
        return struct.pack("!BBBB", *map(int, ip.split('.')))

    def printmac(self, mac):
        return ':'.join(map(lambda x:hex(x)[2:].zfill(2), struct.unpack("BBBBBB", mac))).upper()

    def craftheader(self, message):
        """Craft the DHCP header using parts of the message"""
        xid, flags, giaddr, chaddr = struct.unpack("!4x4s2x2s4x4x4x4s16s", message[:44])
        clientmac = chaddr[:6]
        #op, htype, hlen, hops, xid
        response =  struct.pack("!BBBB4s", 2, 1, 6, 0, xid)
        #secs, flags, ciaddr
        response += struct.pack("!HHI", 0, 0, 0)
        if self.leases[clientmac]['ip']: #OFFER
            offer = self.leases[clientmac]['ip']
        else: #ACK
            offer = self.nextip()
            self.leases[clientmac]['ip'] = offer
            self.leases[clientmac]['expire'] = time() + 86400
            print self.printmac(clientmac), "->", self.leases[clientmac]['ip']
        #yiaddr
        response += self.packip(offer)
        #siaddr
        response += self.packip(self.ip)
        #giaddr
        response += struct.pack("!I", 0)
        #chaddr
        response += chaddr
        #bootp legacy pad
        response += "\x00"*192
        #magic section
        response += self.magic
        return response

    def craftoptions(self, opt53):
        """Craft option fields.
        opt53:
            2 - DHCPOFFER
            5 - DHCPACK
            (See rfc2132 9.6)"""
        #Message type, offer
        response = struct.pack("!BBB", 53, 1, opt53)
        #DHCP Server
        response += struct.pack("!BB", 54, 4) + self.packip(self.ip)
        #SubnetMask
        response += struct.pack("!BB", 1, 4) + self.packip(self.subnetmask)
        #Router
        response += struct.pack("!BB", 3, 4) + self.packip(self.router)
        #Lease time
        response += struct.pack("!BBI", 51, 4, 86400)
        #TFTP Server
        response += struct.pack("!BB", 66, len(self.tftpserver)) + self.tftpserver
        #Filename null terminated
        response += struct.pack("!BB", 67, len(self.filename)+1) + self.filename + "\x00"
        #End options
        response += "\xff"
        return response


    def dhcpoffer(self, message):
        """Respond to discovery with offer"""
        headerresponse = self.craftheader(message)
        optionsresponse = self.craftoptions(2) #DHCPOFFER

        response = headerresponse + optionsresponse
        self.sock.sendto(response, ('<broadcast>', 68))

    def dhcpack(self, message):
        """Respond to request with acknowledge"""
        headerresponse = self.craftheader(message)
        optionsresponse = self.craftoptions(5) #DHCPACK

        response = headerresponse + optionsresponse
        self.sock.sendto(response, ('<broadcast>', 68))

    def listen(self):
        """Main listen loop"""
        while True:
            message, address = self.sock.recvfrom(1024)
            self.timeoutleases()
            op = struct.unpack("!B", message[:1])[0]
            if not op == 1 and address[0] != '0.0.0.0':
                continue #probably not a dhcp packet
            #see rfc2131 pg 10
            type = struct.unpack("!BxB", message[240:240+3]) #options offset
            if type == (53, 1):
                self.dhcpoffer(message)
            elif type == (53, 3):
                self.dhcpack(message)


if __name__ == '__main__':
    tftpd = TFTPD()
    dhcpd = DHCPD('192.168.2.2', '192.168.2.100', '192.168.2.150', '255.255.255.0', '192.168.2.1', '8.8.8.8', '/netboot/pxelinux.0', '192.168.2.2')

    tftpthread = threading.Thread(target=tftpd.listen)
    dhcpthread = threading.Thread(target=dhcpd.listen)

    tftpthread.daemon = True
    dhcpthread.daemon = True

    tftpthread.start()
    dhcpthread.start()

    while True:
        sleep(1)
