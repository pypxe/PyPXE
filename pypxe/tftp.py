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
        self.netbootDirectory = serverSettings.get('netbootDirectory',  os.getcwd())
        self.mode_debug = serverSettings.get('mode_debug', False) #debug mode
        self.logger = serverSettings.get('logger', None)
        self.default_retries = serverSettings.get('default_retries', 3)
        self.timeout = serverSettings.get('timeout', 5)
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

        self.chroot()

        self.logger.debug('NOTICE: TFTP server started in debug mode. TFTP server is using the following:')
        self.logger.debug('  TFTP Server IP: {}'.format(self.ip))
        self.logger.debug('TFTP Server Port: {}'.format(self.port))
        self.logger.debug('  TFTP Network Boot Directory: {}'.format(self.netbootDirectory))

        #key is (address, port) pair
        self.ongoing = defaultdict(lambda: {'filename': '', 'handle': None, 'block': 1, 'blksize': 512, 'sock': None, 'sent_time': float("inf"), 'retries': self.default_retries})

    def chroot(self):
        # Start in network boot file directory and then chroot, 
        # this simplifies target later as well as offers a slight security increase
        os.chdir (self.netbootDirectory)
        try:
            os.chroot ('.')
        except AttributeError:
            self.logger.warning("Cannot chroot in '{dir}', maybe os.chroot() unsupported by your platform ?".format(dir = self.netbootDirectory))

    def filename(self, message):
        '''
            The first null-delimited field
            is the filename. This method returns the filename
            from the message.
        '''
        return message.split(chr(0))[0]

    def tftpError(self, address, code=1, message="File Not Found"):
        '''
            short int 5 -> Error Opcode
            This method sends the error message to the client

            Error codes from RFC1350 page 10:
            Value     Meaning
            0         Not defined, see error message (if any).
            1         File not found.
            2         Access violation.
            3         Disk full or allocation exceeded.
            4         Illegal TFTP operation.
            5         Unknown transfer ID.
            6         File already exists.
            7         No such user.
        '''
        response =  struct.pack('!H', 5) # error opcode
        response += struct.pack('!H', code) # error code
        response += message
        response += chr(0)
        self.logger.debug("TFTP Sending '{code}: {message}'".format(code = code, message = message))
        self.sock.sendto(response, address)

    def mode(self, message):
        '''
            The second null-delimited field
            is the transfer mode. This method returns the mode
            from the message.
        '''
        return message.split(chr(0))[1]


    def sendBlock(self, address):
        '''
            short int 3 -> Data Block
        '''
        descriptor = self.ongoing[address]
        response = struct.pack('!H', 3) #opcode 3 is DATA, also sent block number
        response += struct.pack('!H', descriptor['block'] % 2 ** 16)
        data = descriptor['handle'].read(descriptor['blksize'])
        response += data
        self.logger.debug('TFTP Sending block {block} to client {ip}:{port}'.format(block = repr(descriptor['block']), ip = address[0], port = address[1]))
        descriptor['sock'].sendto(response, address)
        self.ongoing[address]['retries'] -= 1
        self.ongoing[address]['sent_time'] = time.time()
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
        mode = self.mode(message)
        if mode != 'octet':
            self.logger.error("Mode '{mode}' not supported".format(mode = mode))
            self.tftpError(address, 5, 'Mode {mode} not supported'.format(mode = mode))
            return
        req_file = self.filename(message)
        # avoid directory traversal: strip all ../ and make it relative
        filename = os.path.normpath(os.sep + os.getcwd() + os.sep + req_file).lstrip(os.sep)
        
        if not os.path.lexists(filename):
            self.logger.debug("File '{filename}' not found, sending error message to the client".format(filename = filename) )
            self.tftpError(address, 1, 'File Not Found')
            return

        self.ongoing[address]['filename'] = req_file
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

        # Create the data socket only if needed
        if self.ongoing[address]['sock'] == None:
            socknew = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            socknew.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            socknew.bind((self.ip, 0))
            self.ongoing[address]['sock'] = socknew

        if response:
            response = struct.pack('!H', 6) + response
            socknew.sendto(response, address)
        # if no options in request and no block sent yet start sending data
        elif self.ongoing[address]['block'] == 1:
            self.sendBlock(address)
        else:
            self.logger.warning('Ignored TFTP request: no options in a middle of a transmission')

    def listen(self):
        '''This method listens for incoming requests'''
        while True:
            rlist, wlist, xlist = select.select([self.sock] + [self.ongoing[i]['sock'] for i in self.ongoing if self.ongoing[i]['sock']], [], [], 0)
            for sock in rlist:
                message, address = sock.recvfrom(1024)
                opcode = struct.unpack('!H', message[:2])[0]
                message = message[2:]
                if opcode == 1: # read the request
                    self.logger.debug('TFTP receiving request')
                    self.read(address, message)
                if opcode == 4: # ack
                    if self.ongoing.has_key(address):
                        blockack = struct.unpack("!H", message[:2])[0]
                        if blockack < self.ongoing[address]['block']:
                            self.logger.warning('Ignoring duplicated ACK received for block {blockack}'.format(blockack = blockack))
                            continue
                        if blockack > self.ongoing[address]['block']:
                            self.logger.warning('Ignoring out of sequence ACK received for block {blockack}'.format(blockack = blockack))
                            continue
                        self.ongoing[address]['block'] = blockack + 1
                        self.ongoing[address]['retries'] = self.default_retries
                        self.sendBlock(address)

            # Timeouts and Retries. Done after the above so timeout actually has a value
            # Resent those that have timed out
            dead_conn = []
            for i in self.ongoing:
                if self.ongoing[i]['sent_time'] + self.timeout < time.time() and self.ongoing[i]['retries']:
                    self.logger.debug('No ACK received for block: {block}, retrying'.format(block = self.ongoing[address]['block']))
                    self.ongoing[i]['handle'].seek(-self.ongoing[i]['blksize'], 1)
                    self.sendBlock(i)
                if not self.ongoing[i]['retries']:
                    self.logger.debug('Max retries reached, aborting connection with {client}:{port}'.format(client = i[0], port = i[1]))
                    self.tftpError(i, 0, 'Timeout reached')
                    self.ongoing[i]['handle'].close()
                    self.ongoing[i]['sock'].close()
                    dead_conn.append(i)

            # Clean up dead connections
            for i in dead_conn:
                self.ongoing.remove(i)
