import socket
import struct
import os
from collections import defaultdict
from time import time

class DHCPD:
    '''
        This class implements a DHCP Server, limited to pxe options,
        where the subnet /24 is hard coded. Implemented from RFC2131,
        RFC2132, https://en.wikipedia.org/wiki/Dynamic_Host_Configuration_Protocol
        and http://www.pix.net/software/pxeboot/archive/pxespec.pdf
    '''
    def __init__(
        self,
        ip,
        fileserver,
        offerfrom,
        offerto,
        subnetmask,
        router,
        dnsserver,
        filename = 'pxelinux.0',
        useipxe = False,
        usehttp = False,
        proxydhcp = False,
        debug = False,
        port = 67):
        
        self.ip = ip
        self.port = port
        self.fileserver = fileserver #TFTP or HTTP
        self.offerfrom = offerfrom
        self.offerto = offerto
        self.subnetmask = subnetmask
        self.router = router
        self.dnsserver = dnsserver
        self.filename = filename
        self.magic = struct.pack('!I', 0x63825363) #magic cookie
        self.ipxe = useipxe
        self.proxydhcp = proxydhcp #ProxyDHCP mode
        self.debug = debug #debug mode

        if usehttp and not useipxe:
            print '\nWARNING: HTTP selected but iPXE disabled. PXE ROM must support HTTP requests.\n'
        if useipxe and usehttp:
            self.filename = 'http://%s%s' % (self.fileserver, self.filename)
        if useipxe and not usehttp:
            self.filename = 'tftp://%s%s' % (self.fileserver, self.filename)

        if self.debug:
            print '\nNOTICE: DHCP server started in debug mode. DHCP server is using the following:\n'
            print '\tDHCP Sever IP: ' + self.ip
            print '\tDHCP Server Port: ' + str (self.port)
            print '\tDHCP File Server IP: ' + self.fileserver
            print '\tDHCP Lease Range: ' + self.offerfrom + ' - ' + self.offerto
            print '\tDHCP Subnet Mask: ' + self.subnetmask
            print '\tDHCP Router: ' + self.router
            print '\tDHCP DNS Server: ' + self.dnsserver
            print '\tDHCP File Name: ' + self.filename
            print '\tProxyDHCP: ' + str(self.proxydhcp)
            print '\tUsing HTTP Server: ' + str(usehttp)
            print '\tUsing iPXE: ' + str(useipxe)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind( ('', self.port ))
        #key is mac
        self.leases = defaultdict(lambda: {'ip': '', 'expire': 0, 'ipxe': self.ipxe})

    def nextip(self):
        '''
            This method returns the next unleased IP from range;
            also does lease expiry by overwrite.
        '''
        #Reasoning:
        #If we use ints, we don't have to deal with octet overflow
        #or nested loops (up to 3 with 10/8)
        #convert both to 32bit integers
        #e.g '192.168.1.1' to 3232235777
        encode = lambda x: struct.unpack("!I", socket.inet_aton(x))[0]
        #e.g 3232235777 to '192.168.1.1'
        decode = lambda x: socket.inet_ntoa(struct.pack("!I", x))
        fromhost = encode(self.offerfrom)
        tohost = encode(self.offerto)
        #pull out already leased ips.
        leased = [self.leases[i]['ip'] for i in self.leases
                if self.leases[i]['expire'] > time()]
        #convert to 32bit int
        leased = map(encode, leased)
        #loop through, make sure not already leased and not in form X.Y.Z.0
        for offset in xrange(tohost - fromhost):
            if (fromhost + offset) % 256 and fromhost + offset not in leased:
                return decode(fromhost + offset)

    def printmac(self, mac):
        '''
            This method converts the MAC Address from binary to
            human-readable format for logging.
        '''
        return ':'.join(map(lambda x: hex(x)[2:].zfill(2), struct.unpack('BBBBBB', mac))).upper()

    def craftHeader(self, message):
        '''This method crafts the DHCP header using parts of the message'''
        xid, flags, yiaddr, giaddr, chaddr = struct.unpack('!4x4s2x2s4x4s4x4s16s', message[:44])
        clientmac = chaddr[:6]
        #op, htype, hlen, hops, xid
        response =  struct.pack('!BBBB4s', 2, 1, 6, 0, xid)
        if not self.proxydhcp:
            #secs, flags, ciaddr
            response += struct.pack('!HHI', 0, 0, 0)
        else:
            response += struct.pack('!HHI', 0, 0x8000, 0)
        if not self.proxydhcp:
            if self.leases[clientmac]['ip']: #OFFER
                offer = self.leases[clientmac]['ip']
            else: #ACK
                offer = self.nextip()
                self.leases[clientmac]['ip'] = offer
                self.leases[clientmac]['expire'] = time() + 86400
                print 'MAC: ' + self.printmac(clientmac) + ' -> IP: ' + self.leases[clientmac]['ip']
            #yiaddr
            response += socket.inet_aton(offer)
        else:
            response += socket.inet_aton('0.0.0.0')
        #siaddr
        response += socket.inet_aton(self.fileserver)
        #giaddr
        response += socket.inet_aton('0.0.0.0')
        #chaddr
        response += chaddr
        #bootp legacy pad
        response += chr(0) * 64 #server name
        if self.proxydhcp:
            response += self.filename
            response += chr(0) * (128 - len(self.filename))
        else:
            response += chr(0) * 128
        #magic section
        response += self.magic
        return (clientmac, response)

    def craftOptions(self, opt53, clientmac):
        '''This method crafts the DHCP option fields
            opt53:
                2 - DHCPOFFER
                5 - DHCPACK
            (See RFC2132 9.6)
        '''
        #Message type, offer
        response = struct.pack('!BBB', 53, 1, opt53)
        #DHCP Server
        response += struct.pack('!BB', 54, 4) + socket.inet_aton(self.ip)
        if not self.proxydhcp:
            #SubnetMask
            response += struct.pack('!BB', 1, 4 ) + socket.inet_aton(self.subnetmask)
            #Router
            response += struct.pack('!BB', 3, 4 ) + socket.inet_aton(self.router)
            #Lease time
            response += struct.pack('!BBI', 51, 4, 86400)
        #TFTP Server OR HTTP Server; if iPXE, need both
        response += struct.pack('!BB', 66, len(self.fileserver)) + self.fileserver
        #Filename null terminated
        if not self.ipxe or not self.leases[clientmac]['ipxe']:
            #Either we don't care about iPXE, or we've already chainloaded ipxe
            response += struct.pack('!BB', 67, len(self.filename) + 1) + self.filename + chr(0)
        else:
            #chainload iPXE
            response += struct.pack('!BB', 67, 16) + '/chainload.kpxe' + chr(0)
            #don't boot-loop once we've sent the two first packets
            if opt53 == 5: #ack
                self.leases[clientmac]['ipxe'] = False
        if self.proxydhcp:
            response += struct.pack('!BB', 60, 9) + 'PXEClient'
            response += struct.pack('!BBBBBBB4sB', 43, 10, 6, 1, 0b1000, 10, 4, chr(0) + 'PXE', 0xff)

        #End options
        response += '\xff'
        return response

    def dhcpoffer(self, message):
        '''This method responds to DHCP discovery with offer'''
        clientmac, headerResponse = self.craftHeader(message)
        optionsResponse = self.craftOptions(2, clientmac) #DHCPOFFER

        response = headerResponse + optionsResponse
        if self.debug:
            print '[DEBUG] DHCPOFFER - Sending the following'
            print '\t<--BEGIN HEADER-->\n\t' + str(headerResponse) + '\n\t<--END HEADER-->\n'
            print '\t<--BEGIN OPTIONS-->\n\t' + str(optionsResponse) + '\n\t<--END OPTIONS-->\n'
            print '\t<--BEGIN RESPONSE-->\n\t' + str(response) + '\n\t<--END RESPONSE-->\n'
        self.sock.sendto(response, ('<broadcast>', 68))

    def dhcpack(self, message):
        '''This method responds to DHCP request with acknowledge'''
        clientmac, headerResponse = self.craftHeader(message)
        optionsResponse = self.craftOptions(5, clientmac) #DHCPACK

        response = headerResponse + optionsResponse
        if self.debug:
            print '[DEBUG] DHCPACK - Sending the following'
            print '\t<--BEGIN HEADER-->\n\t' + str(headerResponse) + '\n\t<--END HEADER-->\n'
            print '\t<--BEGIN OPTIONS-->\n\t' + str(optionsResponse) + '\n\t<--END OPTIONS-->\n'
            print '\t<--BEGIN RESPONSE-->\n\t' + str(response) + '\n\t<--END RESPONSE-->\n'
        self.sock.sendto(response, ('<broadcast>', 68))

    def listen(self):
        '''Main listen loop'''
        while True:
            message, address = self.sock.recvfrom(1024)
            clientmac = struct.unpack('!28x6s', message[:34])
            if self.debug:
                print '[DEBUG] Received message'
                print '\t<--BEGIN MESSAGE-->\n\t' + message + '\n\t<--END MESSAGE-->\n'
            if not 'PXEClient' in message: continue
            #see RFC2131 page 10
            type = struct.unpack('!BxB', message[240:240+3]) #options offset
            if type == (53, 1):
                if self.debug:
                    print '[DEBUG] Received DHCPOFFER'
                self.dhcpoffer(message)
            elif type == (53, 3) and address[0] == '0.0.0.0' and not self.proxydhcp:
                if self.debug:
                    print '[DEBUG] Received DHCPACK'
                self.dhcpack(message)
            elif type == (53, 3) and address[0] != '0.0.0.0' and self.proxydhcp:
                if self.debug:
                    print '[DEBUG] Received DHCPACK'
                self.dhcpack(message)
