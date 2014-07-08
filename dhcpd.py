import socket, struct, os
from collections import defaultdict
from time import time

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
            if not self.leases[clientmac]['ipxe']:
                self.leases[clientmac]['ipxe'] = True #fix reboot without restart server
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

