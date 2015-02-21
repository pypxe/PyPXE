'''

This file contains classes and functions that implement the PyPXE TFTP service

'''

import socket
import struct
import os
import select
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
            print '\tTFTP Server IP: {}'.format(self.ip)
            print '\tTFTP Server Port: {}'.format(self.port)
            print '\tTFTP Network Boot Directory: {}'.format(self.netbootDirectory)

        #key is (address, port) pair
        self.ongoing = defaultdict(lambda: {'filename': '', 'handle': None, 'block': 1, 'blksize': 512, 'sock':None})

        # Start in network boot file directory and then chroot, 
        # this simplifies target later as well as offers a slight security increase
        os.chdir (self.netbootDirectory)
        os.chroot ('.')

    def filename(self, message):
        '''
            The first null-delimited field
            is the filename. This method returns the filename
            from the message.
        '''
        return message.split(chr(0))[0]

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
        if self.mode_debug:
            print '[DEBUG] TFTP Sending block {block}'.format(block = repr(descriptor['block']))
        descriptor['sock'].sendto(response, address)
        if len(data) != descriptor['blksize']:
            descriptor['handle'].close()
            if self.mode_debug:
                print '[DEBUG] TFTP File Sent - tftp://{filename} -> {address[0]}:{address[1]}'.format(filename = descriptor['filename'], address = address)
            descriptor['sock'].close()
            self.ongoing.pop(address)

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
        options = message.split(chr(0))[2: -1]
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
            print '\tDetails: Filesize {filesize} is too big for blksize {blksize}.\n'.format(filesize = filesize, blksize = self.ongoing[address]['blksize'])
        if 'tsize' in options:
            response += 'tsize' + chr(0)
            response += str(filesize)
            response += chr(0)
        if response:
            response = struct.pack('!H', 6) + response
            socknew = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            socknew.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            socknew.bind((self.ip, 0))
            socknew.sendto(response, address)
            self.ongoing[address]['sock'] = socknew

    def listen(self):
        '''This method listens for incoming requests'''
        while True:
            rlist, wlist, xlist = select.select([self.sock] + [self.ongoing[i]['sock'] for i in self.ongoing if self.ongoing[i]['sock']], [], [])
            for sock in rlist:
                message, address = sock.recvfrom(1024)
                opcode = struct.unpack('!H', message[:2])[0]
                message = message[2:]
                if opcode == 1: #read the request
                    if self.mode_debug:
                        print '[DEBUG] TFTP receiving request'
                    self.read(address, message)
                if opcode == 4:
                     if self.ongoing.has_key(address):
                        blockack = struct.unpack("!H", message[:2])[0]
                        self.ongoing[address]['block'] = blockack + 1
                        self.sendBlock(address)
