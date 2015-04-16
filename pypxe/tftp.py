'''

This file contains classes and functions that implement the PyPXE TFTP service

'''

import socket
import struct
import os
import select
import time
import logging
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
        self.logger = serverSettings.get('logger', None)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))

        # setup logger
        if self.logger == None:
            self.logger = logging.getLogger("TFTP")
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        if self.mode_debug:
            self.logger.setLevel(logging.DEBUG)

        self.logger.debug('NOTICE: TFTP server started in debug mode. TFTP server is using the following:')
        self.logger.debug('  TFTP Server IP: {}'.format(self.ip))
        self.logger.debug('TFTP Server Port: {}'.format(self.port))
        self.logger.debug('  TFTP Network Boot Directory: {}'.format(self.netbootDirectory))

        #key is (address, port) pair
        self.ongoing = defaultdict(lambda: {'filename': '', 'handle': None, 'block': 1, 'blksize': 512, 'sock':None, 'timeout':float("inf"), 'retries':3})

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
        response += chr(0)
        self.logger.debug("TFTP Sending 'File Not Found'")
        self.sock.sendto(response, address)

    def sendBlock(self, address):
        '''
            short int 3 -> Data Block
        '''
        descriptor = self.ongoing[address]
        response = struct.pack('!H', 3) #opcode 3 is DATA, also sent block number
        response += struct.pack('!H', descriptor['block'] % 2 ** 16)
        data = descriptor['handle'].read(descriptor['blksize'])
        response += data
        self.logger.debug('TFTP Sending block {block}'.format(block = repr(descriptor['block'])))
        descriptor['sock'].sendto(response, address)
        self.ongoing[address]['retries'] -= 1
        self.ongoing[address]['timeout'] = time.time()
        if len(data) != descriptor['blksize']:
            descriptor['handle'].close()
            self.logger.debug('TFTP File Sent - tftp://{filename} -> {address[0]}:{address[1]}'.format(filename = descriptor['filename'], address = address))
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
            self.logger.warning('TFTP request too big, attempting transfer anyway.')
            self.logger.warning('  Details: Filesize {filesize} is too big for blksize {blksize}.\n'.format(filesize = filesize, blksize = self.ongoing[address]['blksize']))
        if 'tsize' in options:
            response += 'tsize' + chr(0)
            response += str(filesize)
            response += chr(0)

        socknew = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socknew.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socknew.bind((self.ip, 0))

        if response:
            response = struct.pack('!H', 6) + response
            socknew.sendto(response, address)

        self.ongoing[address]['sock'] = socknew
        self.sendBlock(address)

    def listen(self):
        '''This method listens for incoming requests'''
        while True:
            rlist, wlist, xlist = select.select([self.sock] + [self.ongoing[i]['sock'] for i in self.ongoing if self.ongoing[i]['sock']], [], [])
            for sock in rlist:
                message, address = sock.recvfrom(1024)
                opcode = struct.unpack('!H', message[:2])[0]
                message = message[2:]
                if opcode == 1: #read the request
                    self.logger.debug('TFTP receiving request')
                    self.read(address, message)
                if opcode == 4:
                    if self.ongoing.has_key(address):
                        blockack = struct.unpack("!H", message[:2])[0]
                        self.ongoing[address]['block'] = blockack + 1
                        self.ongoing[address]['retries'] = 3
                        self.sendBlock(address)
            #Timeouts and Retries. Done after the above so timeout actually has a value
            #Resent those that have timed out
            for i in self.ongoing:
                if self.ongoing[i]['timeout']+5 < time.time() and self.ongoing[i]['retries']:
                    self.ongoing[i]['handle'].seek(-self.ongoing[i]['blksize'], 1)
                    self.sendBlock(i)
                if not self.ongoing[i]['retries']:
                    self.ongoing.pop(i)
