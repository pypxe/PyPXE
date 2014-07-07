import socket
import struct
import os
from collections import defaultdict
from time import time, sleep
import threading

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

class DHCPD:
    """dhcp server, limited to pxe options.
    /24 Hard coded.
    Implemented from
    rfc2131, rfc2132 and 
    https://en.wikipedia.org/wiki/Dynamic_Host_Configuration_Protocol"""
    def __init__(self, fileserver, offerfrom, offerto, subnetmask, router, dnsserver, filename, ip, useipxe, usehttp, proxydhcp, port = 67):
        self.ip = ip
        self.port = port
        self.fileserver = fileserver #TFTP OR HTTP
        self.offerfrom = offerfrom
        self.offerto = offerto
        self.subnetmask = subnetmask
        self.router = router
        self.dnsserver = dnsserver
        self.filename = filename
        self.magic = struct.pack("!I", 0x63825363) #magic cookie
        self.ipxe = useipxe
        self.proxydhcp = proxydhcp
        self.bypass = []
        if usehttp and not self.ipxe:
            print "HTTP enabled but iPXE isn't, your client MUST support"
            print "native HTTP booting (e.g. iPXE ROM)"
        if useipxe and usehttp:
            self.filename = "http://%s%s" % (self.fileserver, self.filename)
        if useipxe and not usehttp:
            self.filename = "tftp://%s%s" % (self.fileserver, self.filename)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', self.port))
        #key is mac
        self.leases = defaultdict(lambda:{'ip':'', 'expire':0, 'ipxe':True})

    def nextip(self):
        """return the next unleased ip from range
        Also does lease expiry by overwrite"""
        network = '.'.join(self.offerfrom.split('.')[:-1])
        fromhost = int(self.offerfrom.split('.')[-1])
        tohost = int(self.offerto.split('.')[-1])
        leased = [self.leases[i]['ip'] for i in self.leases if self.leases[i]['expire']>time()]
        for host in xrange(fromhost, tohost+1):
            if network+"."+str(host) not in leased:
                return network+"."+str(host)

    def packip(self, ip):
        """NBO the str ip"""
        return struct.pack("!BBBB", *map(int, ip.split('.')))

    def printmac(self, mac):
        """Turn the MAC Address from binary
        to human friendly format, for logging"""
        return ':'.join(map(lambda x:hex(x)[2:].zfill(2), struct.unpack("BBBBBB", mac))).upper()

    def craftheader(self, message):
        """Craft the DHCP header using parts of the message"""
        xid, flags, yiaddr, giaddr, chaddr = struct.unpack("!4x4s2x2s4x4s4x4s16s", message[:44])
        clientmac = chaddr[:6]
        #op, htype, hlen, hops, xid
        response =  struct.pack("!BBBB4s", 2, 1, 6, 0, xid)
        if not self.proxydhcp:
            #secs, flags, ciaddr
            response += struct.pack("!HHI", 0, 0, 0)
        else:
            response += struct.pack("!HHI", 0, 0x8000, 0)
        if not self.proxydhcp:
            if self.leases[clientmac]['ip']: #OFFER
                offer = self.leases[clientmac]['ip']
            else: #ACK
                offer = self.nextip()
                self.leases[clientmac]['ip'] = offer
                self.leases[clientmac]['expire'] = time() + 86400
                print self.printmac(clientmac), "->", self.leases[clientmac]['ip']
        if not self.proxydhcp:
            #yiaddr
            response += self.packip(offer)
        else:
            response += self.packip('0.0.0.0')
        if not self.proxydhcp:
            #siaddr
            response += self.packip(self.ip)
        else:
            response += self.packip('0.0.0.0')
        #giaddr
        response += struct.pack("!I", 0)
        #chaddr
        response += chaddr
        #bootp legacy pad
        response += "\x00"*64 #server name
        response += self.filename
        response += "\x00"*(128-len(self.filename))
        #magic section
        response += self.magic
        return (clientmac, response)

    def craftoptions(self, opt53, clientmac):
        """Craft option fields.
        opt53:
            2 - DHCPOFFER
            5 - DHCPACK
            (See rfc2132 9.6)"""
        #Message type, offer
        response = struct.pack("!BBB", 53, 1, opt53)
        #DHCP Server
        response += struct.pack("!BB", 54, 4) + self.packip(self.ip)
        if not self.proxydhcp:
            #SubnetMask
            response += struct.pack("!BB", 1, 4) + self.packip(self.subnetmask)
            #Router
            response += struct.pack("!BB", 3, 4) + self.packip(self.router)
            #Lease time
            response += struct.pack("!BBI", 51, 4, 86400)
        #TFTP Server OR HTTP Server
        #If iPXE need both
        response += struct.pack("!BB", 66, len(self.fileserver)) + self.fileserver
        #Filename null terminated
        if not self.ipxe or not self.leases[clientmac]['ipxe']:
            #Either we don't care about iPXE, or we've already chainloaded ipxe
            response += struct.pack("!BB", 67, len(self.filename)+1) + self.filename + "\x00"
        else:
            #chainload iPXE
            response += struct.pack("!BB", 67, 16) + "/chainload.kpxe" + "\x00"
            self.leases[clientmac]['ipxe'] = False
        if self.proxydhcp:
            response += struct.pack("!BB", 60, 9) + "PXEClient"
            response += struct.pack("!BBBBBBB4sB", 43, 10, 6, 1, 0b1000, 10, 4, "\x00PXE", 0xff)

        #End options
        response += "\xff"
        return response


    def dhcpoffer(self, message):
        """Respond to discovery with offer"""
        clientmac, headerresponse = self.craftheader(message)
        optionsresponse = self.craftoptions(2, clientmac) #DHCPOFFER

        response = headerresponse + optionsresponse
        self.sock.sendto(response, ('<broadcast>', 68))

    def dhcpack(self, message):
        """Respond to request with acknowledge"""
        clientmac, headerresponse = self.craftheader(message)
        optionsresponse = self.craftoptions(5, clientmac) #DHCPACK

        response = headerresponse + optionsresponse
        self.sock.sendto(response, ('<broadcast>', 68))

    def listen(self):
        """Main listen loop"""
        while True:
            message, address = self.sock.recvfrom(1024)
            clientmac = struct.unpack("!28x6s", message[:34])
            if not "PXEClient" in message: continue
            #see rfc2131 pg 10
            type = struct.unpack("!BxB", message[240:240+3]) #options offset
            if type == (53, 1):
                self.dhcpoffer(message)
                self.bypass.append(clientmac)
            elif type == (53, 3) and address[0] == '0.0.0.0' and not self.proxydhcp:
                self.dhcpack(message)
            elif type == (53, 3) and address[0] != '0.0.0.0' and self.proxydhcp:
                self.dhcpack(message)
                self.bypass.pop(clientmac)

class HTTPD:
    """HTTP Server, limited to GET and HEAD
    Implemented from
    rfc2616, rfc7230
    """
    def __init__(self, ip = '', port = 80):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((ip, port))
        self.sock.listen(1)
        os.chroot('.')
    def handlereq(self, connection, addr):
        """Handle HTTP request"""
        request = connection.recv(1024)
        startline = request.split("\r\n")[0].split(' ')
        method = startline[0]
        target = startline[1]

        if not os.path.exists(target) or not os.path.isfile(target):
            status = "404 Not Found"
        elif method not in ("GET", "HEAD"):
            status = "501 Not Implemented"
        else:
            status = "200 OK"
        response = "HTTP/1.1 %s\r\n" % status
        if status[:3] in ("404", "501"):
            #Fail out
            connection.send(response)
            connection.close()
            return

        response += "Content-Length: %d\r\n" % os.path.getsize(target)
        response += "\r\n"
        if method == "HEAD":
            connection.send(response)
            connection.close()
            return

        handle = open(target)
        response += handle.read()
        handle.close()
        connection.send(response)
        connection.close()
        print "http://%s -> %s:%d" % (target, addr[0], addr[1])

    def listen(self):
        """Main listen loop"""
        while True:
            conn, addr = self.sock.accept()
            self.handlereq(conn, addr)


if __name__ == '__main__':
    os.chdir("netboot")
    USEIPXE = True #boot into ipxe first, then filename
    USEHTTP = True #filename is on fileserver as http
    PROXYDHCP = True
    if not USEIPXE:
        filename = "/pxelinux.0"
    elif not USEHTTP:
        filename = "/boot.ipxe"
    else:
        filename = "/boot.http.ipxe"

    tftpd = TFTPD()
    dhcpd = DHCPD('192.168.2.2', '192.168.2.100', '192.168.2.150', '255.255.255.0', '192.168.2.1', '8.8.8.8', filename, '192.168.2.2', USEIPXE, USEHTTP, PROXYDHCP)

    tftpthread = threading.Thread(target=tftpd.listen)
    dhcpthread = threading.Thread(target=dhcpd.listen)

    tftpthread.daemon = True
    dhcpthread.daemon = True

    tftpthread.start()
    dhcpthread.start()

    if USEHTTP:
        httpd = HTTPD()
        httpdthread = threading.Thread(target=httpd.listen)
        httpdthread.daemon = True
        httpdthread.start()

    while True:
        sleep(1)
