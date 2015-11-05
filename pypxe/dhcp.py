'''

This file contains classes and functions that implement the PyPXE DHCP service

'''

import socket
import struct
import os
import logging
from collections import defaultdict
from time import time

class OutOfLeasesError(Exception):
    pass


class DHCPD:
    '''
        This class implements a DHCP Server, limited to PXE options.
        Implemented from RFC2131, RFC2132,
        https://en.wikipedia.org/wiki/Dynamic_Host_Configuration_Protocol,
        and http://www.pix.net/software/pxeboot/archive/pxespec.pdf.
    '''
    def __init__(self, booted_callback=None, expected_hostname=None, **server_settings):
        '''

        :param booted_callback: This function is called when the
        expected_hostname is recognised over DHCP, indicating your host is
        booted
        :param expected_hostname: Expected hostname.
        :param server_settings: Server settings kwargs
        :return:
        '''

        self.ip = server_settings.get('ip', '192.168.2.2')
        self.port = server_settings.get('port', 67)
        self.offer_from = server_settings.get('offer_from', '192.168.2.100')
        self.offer_to = server_settings.get('offer_to', '192.168.2.150')
        self.subnet_mask = server_settings.get('subnet_mask', '255.255.255.0')
        self.router = server_settings.get('router', '192.168.2.1')
        self.dns_server = server_settings.get('dns_server', '8.8.8.8')
        self.broadcast = server_settings.get('broadcast', '<broadcast>')
        self.file_server = server_settings.get('file_server', '192.168.2.2')
        self.file_name = server_settings.get('file_name', '')
        if not self.file_name:
            self.force_file_name = False
            self.file_name = 'pxelinux.0'
        else:
            self.force_file_name = True
        self.ipxe = server_settings.get('use_ipxe', False)
        self.http = server_settings.get('use_http', False)
        self.mode_proxy = server_settings.get('mode_proxy', False) # ProxyDHCP mode
        self.static_config = server_settings.get('static_config', dict())
        self.whitelist = server_settings.get('whitelist', False)
        self.mode_debug = server_settings.get('mode_debug', False) # debug mode
        self.logger = server_settings.get('logger', None)
        self.magic = struct.pack('!I', 0x63825363) # magic cookie
        self.expected_hostname = expected_hostname
        self.booted_callback = booted_callback

        # setup logger
        if self.logger == None:
            self.logger = logging.getLogger('DHCP')
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        if self.mode_debug:
            self.logger.setLevel(logging.DEBUG)

        if self.http and not self.ipxe:
            self.logger.warning('HTTP selected but iPXE disabled. PXE ROM must support HTTP requests.')
        if self.ipxe and self.http:
            self.file_name = 'http://{0}/{1}'.format(self.file_server, self.file_name)
        if self.ipxe and not self.http:
            self.file_name = 'tftp://{0}/{1}'.format(self.file_server, self.file_name)

        self.logger.debug('NOTICE: DHCP server started in debug mode. DHCP server is using the following:')
        self.logger.debug('DHCP Server IP: {0}'.format(self.ip))
        self.logger.debug('DHCP Server Port: {0}'.format(self.port))

        # debug info for ProxyDHCP mode
        if not self.mode_proxy:
            self.logger.debug('Lease Range: {0} - {1}'.format(self.offer_from, self.offer_to))
            self.logger.debug('Subnet Mask: {0}'.format(self.subnet_mask))
            self.logger.debug('Router: {0}'.format(self.router))
            self.logger.debug('DNS Server: {0}'.format(self.dns_server))
            self.logger.debug('Broadcast Address: {0}'.format(self.broadcast))

        if self.static_config:
            self.logger.debug('Using Static Leasing')
            self.logger.debug('Using Static Leasing Whitelist: {0}'.format(self.whitelist))

        self.logger.debug('File Server IP: {0}'.format(self.file_server))
        self.logger.debug('File Name: {0}'.format(self.file_name))
        self.logger.debug('ProxyDHCP Mode: {0}'.format(self.mode_proxy))
        self.logger.debug('Using iPXE: {0}'.format(self.ipxe))
        self.logger.debug('Using HTTP Server: {0}'.format(self.http))

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(('', self.port ))

        # key is MAC
        self.leases = defaultdict(lambda: {'ip': '', 'expire': 0, 'ipxe': self.ipxe})

    def get_namespaced_static(self, path, fallback = {}):
        statics = self.static_config
        for child in path.split('.'):
            statics = statics.get(child, {})
        return statics if statics else fallback

    def next_ip(self):
        '''
            This method returns the next unleased IP from range;
            also does lease expiry by overwrite.
        '''

        # if we use ints, we don't have to deal with octet overflow
        # or nested loops (up to 3 with 10/8); convert both to 32-bit integers

        # e.g '192.168.1.1' to 3232235777
        encode = lambda x: struct.unpack('!I', socket.inet_aton(x))[0]

        # e.g 3232235777 to '192.168.1.1'
        decode = lambda x: socket.inet_ntoa(struct.pack('!I', x))

        from_host = encode(self.offer_from)
        to_host = encode(self.offer_to)

        # pull out already leased IPs
        leased = [self.leases[i]['ip'] for i in self.leases
                if self.leases[i]['expire'] > time()]

        # convert to 32-bit int
        leased = map(encode, leased)

        # loop through, make sure not already leased and not in form X.Y.Z.0
        for offset in xrange(to_host - from_host):
            if (from_host + offset) % 256 and from_host + offset not in leased:
                return decode(from_host + offset)
        raise OutOfLeasesError('Ran out of IP addresses to lease!')

    def tlv_encode(self, tag, value):
        '''Encode a TLV option.'''
        return struct.pack('BB', tag, len(value)) + value

    def tlv_parse(self, raw):
        '''Parse a string of TLV-encoded options.'''
        ret = {}
        while(raw):
            [tag] = struct.unpack('B', raw[0])
            if tag == 0: # padding
                raw = raw[1:]
                continue
            if tag == 255: # end marker
                break
            [length] = struct.unpack('B', raw[1])
            value = raw[2:2 + length]
            raw = raw[2 + length:]
            if tag in ret:
                ret[tag].append(value)
            else:
                ret[tag] = [value]
        return ret

    def get_mac(self, mac):
        '''
            This method converts the MAC Address from binary to
            human-readable format for logging.
        '''
        return ':'.join(map(lambda x: hex(x)[2:].zfill(2), struct.unpack('BBBBBB', mac))).upper()

    def craft_header(self, message):
        '''This method crafts the DHCP header using parts of the message.'''
        xid, flags, yiaddr, giaddr, chaddr = struct.unpack('!4x4s2x2s4x4s4x4s16s', message[:44])
        client_mac = chaddr[:6]

        # op, htype, hlen, hops, xid
        response =  struct.pack('!BBBB4s', 2, 1, 6, 0, xid)
        if not self.mode_proxy:
            response += struct.pack('!HHI', 0, 0, 0) # secs, flags, ciaddr
        else:
            response += struct.pack('!HHI', 0, 0x8000, 0)
        if not self.mode_proxy:
            if self.leases[client_mac]['ip']: # OFFER
                offer = self.leases[client_mac]['ip']
            else: # ACK
                offer = self.get_namespaced_static('dhcp.binding.{0}.ipaddr'.format(self.get_mac(client_mac)))
                offer = offer if offer else self.next_ip()
                self.leases[client_mac]['ip'] = offer
                self.leases[client_mac]['expire'] = time() + 86400
                self.logger.debug('New Assignment - MAC: {0} -> IP: {1}'.format(self.get_mac(client_mac), self.leases[client_mac]['ip']))
            response += socket.inet_aton(offer) # yiaddr
        else:
            response += socket.inet_aton('0.0.0.0')
        response += socket.inet_aton(self.file_server) # siaddr
        response += socket.inet_aton('0.0.0.0') # giaddr
        response += chaddr # chaddr

        # BOOTP legacy pad
        response += chr(0) * 64 # server name
        if self.mode_proxy:
            response += self.file_name
            response += chr(0) * (128 - len(self.file_name))
        else:
            response += chr(0) * 128
        response += self.magic # magic section
        return (client_mac, response)

    def craft_options(self, opt53, client_mac):
        '''
            This method crafts the DHCP option fields
            opt53:
                2 - DHCPOFFER
                5 - DHCPACK
            See RFC2132 9.6 for details.
        '''
        response = self.tlv_encode(53, chr(opt53)) # message type, OFFER
        response += self.tlv_encode(54, socket.inet_aton(self.ip)) # DHCP Server
        if not self.mode_proxy:
            subnet_mask = self.get_namespaced_static('dhcp.binding.{0}.subnet'.format(self.get_mac(client_mac)), self.subnet_mask)
            response += self.tlv_encode(1, socket.inet_aton(subnet_mask)) # subnet mask
            router = self.get_namespaced_static('dhcp.binding.{0}.router'.format(self.get_mac(client_mac)), self.router)
            response += self.tlv_encode(3, socket.inet_aton(router)) # router
            dns_server = self.get_namespaced_static('dhcp.binding.{0}.dns'.format(self.get_mac(client_mac)), [self.dns_server])
            dns_server = ''.join([socket.inet_aton(i) for i in dns_server])
            response += self.tlv_encode(6, dns_server)
            response += self.tlv_encode(51, struct.pack('!I', 86400)) # lease time

        # TFTP Server OR HTTP Server; if iPXE, need both
        response += self.tlv_encode(66, self.file_server)

        # file_name null terminated
        if not self.ipxe or not self.leases[client_mac]['ipxe']:
            # http://www.syslinux.org/wiki/index.php/PXELINUX#UEFI
            if 93 in self.leases[client_mac]['options'] and not self.force_file_name:
                [arch] = struct.unpack("!H", self.leases[client_mac]['options'][93][0])
                if arch == 0: # BIOS/default
                    response += self.tlv_encode(67, 'pxelinux.0' + chr(0))
                elif arch == 6: # EFI IA32
                    response += self.tlv_encode(67, 'syslinux.efi32' + chr(0))
                elif arch == 7: # EFI BC, x86-64 (according to the above link)
                    response += self.tlv_encode(67, 'syslinux.efi64' + chr(0))
                elif arch == 9: # EFI x86-64
                    response += self.tlv_encode(67, 'syslinux.efi64' + chr(0))
            else:
                response += self.tlv_encode(67, self.file_name + chr(0))
        else:
            response += self.tlv_encode(67, 'chainload.kpxe' + chr(0)) # chainload iPXE
            if opt53 == 5: # ACK
                self.leases[client_mac]['ipxe'] = False
        if self.mode_proxy:
            response += self.tlv_encode(60, 'PXEClient')
            response += struct.pack('!BBBBBBB4sB', 43, 10, 6, 1, 0b1000, 10, 4, chr(0) + 'PXE', 0xff)
        response += '\xff'
        return response

    def dhcp_offer(self, message):
        '''This method responds to DHCP discovery with offer.'''
        client_mac, header_response = self.craft_header(message)
        options_response = self.craft_options(2, client_mac) # DHCPOFFER
        response = header_response + options_response
        self.logger.debug('DHCPOFFER - Sending the following')
        self.logger.debug('<--BEGIN HEADER-->')
        self.logger.debug('{0}'.format(repr(header_response)))
        self.logger.debug('<--END HEADER-->')
        self.logger.debug('<--BEGIN OPTIONS-->')
        self.logger.debug('{0}'.format(repr(options_response)))
        self.logger.debug('<--END OPTIONS-->')
        self.logger.debug('<--BEGIN RESPONSE-->')
        self.logger.debug('{0}'.format(repr(response)))
        self.logger.debug('<--END RESPONSE-->')
        self.sock.sendto(response, (self.broadcast, 68))

    def dhcp_ack(self, message):
        '''This method responds to DHCP request with acknowledge.'''
        client_mac, header_response = self.craft_header(message)
        options_response = self.craft_options(5, client_mac) # DHCPACK
        response = header_response + options_response
        self.logger.debug('DHCPACK - Sending the following')
        self.logger.debug('<--BEGIN HEADER-->')
        self.logger.debug('{0}'.format(repr(header_response)))
        self.logger.debug('<--END HEADER-->')
        self.logger.debug('<--BEGIN OPTIONS-->')
        self.logger.debug('{0}'.format(repr(options_response)))
        self.logger.debug('<--END OPTIONS-->')
        self.logger.debug('<--BEGIN RESPONSE-->')
        self.logger.debug('{0}'.format(repr(response)))
        self.logger.debug('<--END RESPONSE-->')
        self.sock.sendto(response, (self.broadcast, 68))

    def validate_req(self, client_mac):
        # client request is valid only if contains Vendor-Class = PXEClient
        if self.whitelist and self.get_mac(client_mac) not in self.get_namespaced_static('dhcp.binding'):
            self.logger.debug('Non-whitelisted client request received')
            return False
        if 60 in self.leases[client_mac]['options'] and 'PXEClient' in self.leases[client_mac]['options'][60][0]:
            self.logger.debug('PXE client request received')
            return True
        if self.mode_debug:
            self.logger.debug('Non-PXE client request received')
        return False

    def listen(self):
        '''Main listen loop.'''
        while True:
            message, address = self.sock.recvfrom(1024)
            [client_mac] = struct.unpack('!28x6s', message[:34])
            self.logger.debug('Received message')
            self.logger.debug('<--BEGIN MESSAGE-->')
            self.logger.debug('{0}'.format(repr(message)))
            self.logger.debug('<--END MESSAGE-->')
            self.leases[client_mac]['options'] = self.tlv_parse(message[240:])
            self.logger.debug('Parsed received options')
            self.logger.debug('<--BEGIN OPTIONS-->')
            self.logger.debug('{0}'.format(repr(self.leases[client_mac]['options'])))

            if self.leases[client_mac]['options'].get(12) is not None and \
                    50 in self.leases[client_mac]['options']:
                if self.leases[client_mac]['options'].get(12)[0] == \
                        self.expected_hostname:
                    byte_ip = self.leases[client_mac]['options'].get(50)[0]
                    booted_ip = str(socket.inet_ntoa(byte_ip))
                    self.booted_callback(booted_ip)
            self.logger.debug('<--END OPTIONS-->')
            if not self.validate_req(client_mac):
                continue
            type = ord(self.leases[client_mac]['options'][53][0]) # see RFC2131, page 10
            if type == 1:
                self.logger.debug('Received DHCPOFFER')
                try:
                    self.dhcp_offer(message)
                except OutOfLeasesError:
                    self.logger.critical('Ran out of leases')
            elif type == 3 and address[0] == '0.0.0.0' and not self.mode_proxy:
                self.logger.debug('Received DHCPACK')
                self.dhcp_ack(message)
            elif type == 3 and address[0] != '0.0.0.0' and self.mode_proxy:
                self.logger.debug('Received DHCPACK')
                self.dhcp_ack(message)
