'''

This file contains classes and functions that implement the PyPXE DHCP service

'''

import socket
import struct
import os
import logging
from collections import defaultdict
from time import time

class DHCPD:
    '''
        This class implements a DHCP Server, limited to pxe options,
        where the subnet /24 is hard coded. Implemented from RFC2131,
        RFC2132, https://en.wikipedia.org/wiki/Dynamic_Host_Configuration_Protocol
        and http://www.pix.net/software/pxeboot/archive/pxespec.pdf
    '''
    def __init__(self, **serverSettings):
        
        self.ip = serverSettings.get('ip', '192.168.2.2')
        self.port = serverSettings.get('port', 67)
        self.offerfrom = serverSettings.get('offerfrom', '192.168.2.100')
        self.offerto = serverSettings.get('offerto', '192.168.2.150')
        self.subnetmask = serverSettings.get('subnetmask', '255.255.255.0')
        self.router = serverSettings.get('router', '192.168.2.1')
        self.dnsserver = serverSettings.get('dnsserver', '8.8.8.8')
        self.broadcast = serverSettings.get('broadcast', '<broadcast>')
        self.fileserver = serverSettings.get('fileserver', '192.168.2.2')
        self.filename = serverSettings.get('filename', '')
        if not self.filename:
            self.forcefilename = False
            self.filename = "pxelinux.0"
        else:
            self.forcefilename = True
        self.ipxe = serverSettings.get('useipxe', False)
        self.http = serverSettings.get('usehttp', False)
        self.mode_proxy = serverSettings.get('mode_proxy', False) #ProxyDHCP mode
        self.mode_debug = serverSettings.get('mode_debug', False) #debug mode
        self.magic = struct.pack('!I', 0x63825363) #magic cookie
        self.logger = serverSettings.get('logger', None)

        # setup logger
        if self.logger == None:
            self.logger = logging.getLogger("DHCP")
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s %(name)s [%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        if self.mode_debug:
            self.logger.setLevel(logging.DEBUG)

        if self.http and not self.ipxe:
            self.logger.warning('WARNING: HTTP selected but iPXE disabled. PXE ROM must support HTTP requests.')
        if self.ipxe and self.http:
            self.filename = 'http://{fileserver}/{filename}'.format(fileserver = self.fileserver, filename = self.filename)
        if self.ipxe and not self.http:
            self.filename = 'tftp://{fileserver}/{filename}'.format(fileserver = self.fileserver, filename = self.filename)

        self.logger.debug('NOTICE: DHCP server started in debug mode. DHCP server is using the following:')
        self.logger.debug('  DHCP Server IP: {}'.format(self.ip))
        self.logger.debug('  DHCP Server Port: {}'.format(self.port))
        self.logger.debug('  DHCP Lease Range: {} - {}'.format(self.offerfrom, self.offerto))
        self.logger.debug('  DHCP Subnet Mask: {}'.format(self.subnetmask))
        self.logger.debug('  DHCP Router: {}'.format(self.router))
        self.logger.debug('  DHCP DNS Server: {}'.format(self.dnsserver))
        self.logger.debug('  DHCP Broadcast Address: {}'.format(self.broadcast))
        self.logger.debug('  DHCP File Server IP: {}'.format(self.fileserver))
        self.logger.debug('  DHCP File Name: {}'.format(self.filename))
        self.logger.debug('  ProxyDHCP Mode: {}'.format(self.mode_proxy))
        self.logger.debug('  tUsing iPXE: {}'.format(self.ipxe))
        self.logger.debug('  Using HTTP Server: {}'.format(self.http))

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', self.port ))
        
        #key is mac
        self.leases = defaultdict(lambda: {'ip': '', 'expire': 0, 'ipxe': self.ipxe})

    def nextIP(self):
        '''
            This method returns the next unleased IP from range;
            also does lease expiry by overwrite.
        '''

        #if we use ints, we don't have to deal with octet overflow
        #or nested loops (up to 3 with 10/8); convert both to 32bit integers
        
        #e.g '192.168.1.1' to 3232235777
        encode = lambda x: struct.unpack('!I', socket.inet_aton(x))[0]
        
        #e.g 3232235777 to '192.168.1.1'
        decode = lambda x: socket.inet_ntoa(struct.pack('!I', x))
        
        fromhost = encode(self.offerfrom)
        tohost = encode(self.offerto)
        
        #pull out already leased ips
        leased = [self.leases[i]['ip'] for i in self.leases
                if self.leases[i]['expire'] > time()]
        
        #convert to 32bit int
        leased = map(encode, leased)
        
        #loop through, make sure not already leased and not in form X.Y.Z.0
        for offset in xrange(tohost - fromhost):
            if (fromhost + offset) % 256 and fromhost + offset not in leased:
                return decode(fromhost + offset)

    def tlvEncode(self, tag, value):
        '''
            Encode a TLV option
        '''
        return struct.pack("BB", tag, len(value)) + value

    def tlvParse(self, raw):
        '''
            Parse a string of TLV encoded options.
        '''
        ret = {}
        while(raw):
            tag = struct.unpack('B', raw[0])[0]
            if tag == 0:  #padding
                raw = raw[1:]
                continue
            if tag == 255:  #end marker
                break
            length = struct.unpack('B', raw[1])[0]
            value = raw[2:2 + length]
            raw = raw[2 + length:]
            if tag in ret:
                ret[tag].append(value)
            else:
                ret[tag] = [value]
        return ret

    def printMAC(self, mac):
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
        if not self.mode_proxy:
            response += struct.pack('!HHI', 0, 0, 0) #secs, flags, ciaddr
        else:
            response += struct.pack('!HHI', 0, 0x8000, 0)
        if not self.mode_proxy:
            if self.leases[clientmac]['ip']: #OFFER
                offer = self.leases[clientmac]['ip']
            else: #ACK
                offer = self.nextIP()
                self.leases[clientmac]['ip'] = offer
                self.leases[clientmac]['expire'] = time() + 86400
                self.logger.debug('New DHCP Assignment - MAC: {MAC} -> IP: {IP}'.format(MAC = self.printMAC(clientmac), IP = self.leases[clientmac]['ip']))
            response += socket.inet_aton(offer) #yiaddr
        else:
            response += socket.inet_aton('0.0.0.0')
        response += socket.inet_aton(self.fileserver) #siaddr
        response += socket.inet_aton('0.0.0.0') #giaddr
        response += chaddr #chaddr
        
        #bootp legacy pad
        response += chr(0) * 64 #server name
        if self.mode_proxy:
            response += self.filename
            response += chr(0) * (128 - len(self.filename))
        else:
            response += chr(0) * 128
        response += self.magic #magic section
        return (clientmac, response)

    def craftOptions(self, opt53, clientmac):
        '''This method crafts the DHCP option fields
            opt53:
                2 - DHCPOFFER
                5 - DHCPACK
            (See RFC2132 9.6)
        '''
        response = self.tlvEncode(53, chr(opt53)) #message type, offer
        response += self.tlvEncode(54, socket.inet_aton(self.ip)) #DHCP Server
        if not self.mode_proxy:
            response += self.tlvEncode(1, socket.inet_aton(self.subnetmask)) #SubnetMask
            response += self.tlvEncode(3, socket.inet_aton(self.router)) #Router
            response += self.tlvEncode(51, struct.pack('!I', 86400)) #lease time
        
        #TFTP Server OR HTTP Server; if iPXE, need both
        response += self.tlvEncode(66, self.fileserver)
        
        #filename null terminated
        if not self.ipxe or not self.leases[clientmac]['ipxe']:
            #http://www.syslinux.org/wiki/index.php/PXELINUX#UEFI
            if 93 in self.options and not self.forcefilename:
                [arch] = struct.unpack("!H", self.options[93][0])
                if arch == 6: #EFI IA32
                    response += self.tlvEncode(67, "syslinux.efi32" + chr(0))
                elif arch == 7: #EFI BC, x86-64 according to link above
                    response += self.tlvEncode(67, "syslinux.efi64" + chr(0))
                elif arch == 9: #EFI x86-64
                    response += self.tlvEncode(67, "syslinux.efi64" + chr(0))
                if arch == 0: #BIOS/default
                    response += self.tlvEncode(67, "pxelinux.0" + chr(0))
            else:
                response += self.tlvEncode(67, self.filename + chr(0))
        else:
            response += self.tlvEncode(67, '/chainload.kpxe' + chr(0)) #chainload iPXE
            if opt53 == 5: #ACK
                self.leases[clientmac]['ipxe'] = False
        if self.mode_proxy:
            response += self.tlvEncode(60, 'PXEClient')
            response += struct.pack('!BBBBBBB4sB', 43, 10, 6, 1, 0b1000, 10, 4, chr(0) + 'PXE', 0xff)
        response += '\xff'
        return response

    def dhcpOffer(self, message):
        '''This method responds to DHCP discovery with offer'''
        clientmac, headerResponse = self.craftHeader(message)
        optionsResponse = self.craftOptions(2, clientmac) #DHCPOFFER
        response = headerResponse + optionsResponse
        self.logger.debug('DHCPOFFER - Sending the following')
        self.logger.debug('  <--BEGIN HEADER-->\n\t{headerResponse}\n\t<--END HEADER-->'.format(headerResponse = repr(headerResponse)))
        self.logger.debug('  <--BEGIN OPTIONS-->\n\t{optionsResponse}\n\t<--END OPTIONS-->'.format(optionsResponse = repr(optionsResponse)))
        self.logger.debug('  <--BEGIN RESPONSE-->\n\t{response}\n\t<--END RESPONSE-->'.format(response = repr(response)))
        self.sock.sendto(response, (self.broadcast, 68))

    def dhcpAck(self, message):
        '''This method responds to DHCP request with acknowledge'''
        clientmac, headerResponse = self.craftHeader(message)
        optionsResponse = self.craftOptions(5, clientmac) #DHCPACK
        response = headerResponse + optionsResponse
        self.logger.debug('DHCPACK - Sending the following')
        self.logger.debug('  <--BEGIN HEADER-->\n\t{headerResponse}\n\t<--END HEADER-->'.format(headerResponse = repr(headerResponse)))
        self.logger.debug('  <--BEGIN OPTIONS-->\n\t{optionsResponse}\n\t<--END OPTIONS-->'.format(optionsResponse = repr(optionsResponse)))
        self.logger.debug('  <--BEGIN RESPONSE-->\n\t{response}\n\t<--END RESPONSE-->'.format(response = repr(response)))
        self.sock.sendto(response, (self.broadcast, 68))

    def validateReq(self):
        # client request is valid only if contains Vendor-Class = PXEClient
        if 60 in self.options and 'PXEClient' in self.options[60][0]:
            self.logger.debug('Valid client request received')
            return True
        if self.mode_debug:
            self.logger.debug('Invalid client request received')
        return False

    def listen(self):
        '''Main listen loop'''
        while True:
            message, address = self.sock.recvfrom(1024)
            clientmac = struct.unpack('!28x6s', message[:34])
            self.logger.debug('Received message')
            self.logger.debug('  <--BEGIN MESSAGE-->\n\t{message}\n\t<--END MESSAGE-->'.format(message = repr(message)))
            self.options = self.tlvParse(message[240:])
            self.logger.debug('Parsed received options')
            self.logger.debug('  <--BEGIN OPTIONS-->\n\t{options}\n\t<--END OPTIONS-->'.format(options = repr(self.options)))
            if not self.validateReq():
                continue
            type = ord(self.options[53][0]) #see RFC2131 page 10
            if type == 1:
                self.logger.debug('Received DHCPOFFER')
                self.dhcpOffer(message)
            elif type == 3 and address[0] == '0.0.0.0' and not self.mode_proxy:
                self.logger.debug('Received DHCPACK')
                self.dhcpAck(message)
            elif type == 3 and address[0] != '0.0.0.0' and self.mode_proxy:
                self.logger.debug('Received DHCPACK')
                self.dhcpAck(message)
