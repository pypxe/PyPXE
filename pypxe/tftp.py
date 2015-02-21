'''

This file contains classes and functions that implement the PyPXE TFTP service

'''

import socket
import struct
import os
from collections import defaultdict

class TFTPD:
    '''
        This class implements a read-only TFTP server
        implemented from RFC1350 and RFC2348
    '''
    def __init__(self, **serverSettings):
        self.ip = serverSettings.get('ip', '0.0.0.0')
        self.port = serverSettings.get('port', 69)
        self.netbootDirectory = serverSettings.get('netbootDirectory', '.')
        self.mode_debug = serverSettings.get('mode_debug', False) #debug mode
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))

        if self.mode_debug:
            print 'NOTICE: TFTP server started in debug mode. TFTP server is using the following:'
            print '\tTFTP Server IP: ' + self.ip
            print '\tTFTP Server Port: ' + str(self.port)
            print '\tTFTP Network Boot Directory: ' + self.netbootDirectory

        #key is (address, port) pair
        self.ongoing = defaultdict(lambda: {'filename': '', 'handle': None, 'block': 1, 'blksize': 512})

        # Start in network boot file directory and then chroot, 
        # this simplifies target later as well as offers a slight security increase
        os.chdir (self.netbootDirectory)
        os.chroot ('.')

    def filename(self, message):
        '''
            The first null-delimited field after the OPCODE
            is the filename. This method returns the filename
            from the message.
        '''
        return message[2:].split(chr(0))[0]

    def notFound(self, address):
        '''
            short int 5 -> Error
            short int 1 -> File Not Found

            This method sends the message to the client
        '''
        response =  struct.pack('!H', 5) #error code
        response += struct.pack('!H', 1) #file not found
        response += 'File Not Found'
        if self.mode_debug:
            print "[DEBUG] TFTP Sending 'File Not Found'"
        self.sock.sendto(response, address)

    def sendBlock(self, address):
        '''
            short int 3 -> Data Block
        '''
        descriptor = self.ongoing[address]
        response =  struct.pack('!H', 3) #opcode 3 is DATA, also sent block number
        response += struct.pack('!H', descriptor['block'] % 2 ** 16)
        data = descriptor['handle'].read(descriptor['blksize'])
        response += data
        self.sock.sendto(response, address)
        if len(data) != descriptor['blksize']:
            descriptor['handle'].close()
            if self.mode_debug:
                print '[DEBUG] TFTP File Sent - tftp://%s -> %s:%d' % (descriptor['filename'], address[0], address[1])
            self.ongoing.pop(address)
        else:
            if self.mode_debug:
                print '[DEBUG] TFTP Sending block ' + repr(descriptor['block'])
            descriptor['block'] += 1

    def read(self, address, message):
        '''
            On RRQ OPCODE:
                file exists -> reply with file
                file does not exist -> reply with error
        '''
        filename = self.filename(message)
        if not os.path.lexists(filename):
            self.notFound(address)
            return
        self.ongoing[address]['filename'] = filename
        self.ongoing[address]['handle'] = open(filename, 'r')
        options = message.split(chr(0))[3: -1]
        options = dict(zip(options[0::2], options[1::2]))
        response = ''
        if 'blksize' in options:
            response += 'blksize' + chr(0)
            response += options['blksize']
            response += chr(0)
            self.ongoing[address]['blksize'] = int(options['blksize'])
        filesize = os.path.getsize(self.ongoing[address]['filename'])
        if filesize > (2**16 * self.ongoing[address]['blksize']):
            print '\nWARNING: TFTP request too big, attempting transfer anyway.\n'
            print '\tDetails: Filesize %s is too big for blksize %s.\n' % (filesize, self.ongoing[address]['blksize'])
        if 'tsize' in options:
            response += 'tsize' + chr(0)
            response += str(filesize)
            response += chr(0)
        if response:
            response = struct.pack('!H', 6) + response
            self.sock.sendto(response, address)
        self.sendBlock(address)

    def listen(self):
        '''This method listens for incoming requests'''
        while True:
            message, address = self.sock.recvfrom(1024)
            opcode = struct.unpack('!H', message[:2])[0]
            if opcode == 1: #read the request
                if self.mode_debug:
                    print '[DEBUG] TFTP receiving request'
                self.read(address, message)
            if opcode == 4:
                 if self.ongoing.has_key(address):
                    self.sendBlock(address)
