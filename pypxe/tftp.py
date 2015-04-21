'''

This file contains classes and functions that implement the PyPXE TFTP service

'''

import socket
import struct
import os
import select
import time
import logging
import math
#from collections import defaultdict

class Psocket(socket.socket):
    '''Subclassed socket.socket to enable a link back to the client object'''
    parent = None

class Client:
    '''Client instance for TFTPD.'''
    def __init__(self, mainsock, parent):
        # main socket recieve `message`
        # self.ongoing.append(Client(message, retries, timeout))
        # select from main socket + [x.sock for x in self.ongoing]
        self.default_retries = parent.default_retries
        self.timeout = parent.timeout
        self.ip = parent.ip
        self.message, self.address = mainsock.recvfrom(1024)
        self.logger = parent.logger.getChild('Client.{}'.format(self.address))
        self.logger.debug('TFTP recieving request')
        self.retries = self.default_retries
        self.block = 1
        self.blksize = 512
        self.sent_time = float("inf")
        self.dead = False
        self.fh = None
        self.filename = ''

        # message from the main socket
        self.handle()

    def ready(self):
        '''Called when there is something to be read on our socket'''
        self.message = self.sock.recv(1024)
        self.handle()

    def sendBlock(self):
        '''Send the next block of data, setting the timeout and retry variables
        accordingly.'''
        data = self.fh.read(self.blksize)
        # opcode 3 == DATA, wraparound block number
        response = struct.pack("!HH", 3, self.block % 65536)
        response += data
        self.sock.sendto(response, self.address)
        self.logger.debug("Sending block %d", self.block)
        self.retries -= 1
        self.sent_time = time.time()

    def noACK(self):
        '''Have we timed out waiting for an ACK from the client?'''
        if self.sent_time + self.timeout < time.time():
            return True
        return False

    def noRetries(self):
        '''Has the client ran out of retry attempts'''
        if not self.retries:
            return True
        return False

    def validMode(self):
        '''Is the file read mode octet? If not, send an error'''
        mode = self.message.split(chr(0))[1]
        if mode == "octet": return True
        self.sendError(5, 'Mode {} not supported'.format(mode))
        return False

    def checkFile(self):
        '''Does the file exist and is it a file. If not, send an error'''
        filename = self.message.split(chr(0))[0]
        if os.path.lexists(filename) and os.path.isfile(filename):
            self.filename = filename
            return True
        self.sendError(1, 'File Not Found')
        return False

    def parseOptions(self):
        '''Extract the options sent from a client, if any, calculate the last
        block based on the filesize and blocksize'''
        options = self.message.split(chr(0))[2: -1]
        options = dict(zip(options[0::2], map(int, options[1::2])))
        self.blksize = options.get('blksize', self.blksize)
        self.lastblock = math.ceil(self.filesize / float(self.blksize))
        self.tsize = True if 'tsize' in options else False
        if self.filesize > (2**16)*self.blksize:
            self.logger.warning('TFTP request too big, attempting transfer anyway.')
            self.logger.debug('  Details: Filesize %s is too big for blksize %s.\n', self.filesize, self.blksize)

        if len(options):
            # we need to know later if we actually had any options
            self.block = 0
            return True
        else:
            return False

    def replyOptions(self):
        '''If we got sent options, we need to ack them'''
        # only called if options, so send them all
        response = struct.pack("!H", 6)

        response += 'blksize' + chr(0)
        response += str(self.blksize) + chr(0)
        response += 'tsize' + chr(0)
        response += str(self.filesize) + chr(0)

        self.sock.sendto(response, self.address)

    def newRequest(self):
        '''Called when we get a read request from the parent socket. Open our
        own socket and check the read request. If we don't have any options,
        send the first block'''
        self.sock = Psocket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, 0))
        # used by select() to find ready clients
        self.sock.parent = self

        if not self.validMode() or not self.checkFile():
            # some clients just ACK the error (wrong code?)
            # so forcefully shutdown
            self.complete()
            return

        self.fh = open(self.filename, 'rb')
        self.filesize = os.path.getsize(self.filename)

        if not self.parseOptions():
            # no options recieved so start transfer
            if self.block == 1:
                self.sendBlock()
            return

        # we got some options, so ack those first
        self.replyOptions()

    def sendError(self, code = 1, message = "File Not Found"):
        '''Send an error code and string to a client'''
        response =  struct.pack('!H', 5) # error opcode
        response += struct.pack('!H', code) # error code
        response += message
        response += chr(0)
        self.sock.sendto(response, self.address)
        self.logger.debug("TFTP Sending '%d: %s'", code, message)

    def complete(self):
        '''When we've finished sending a file, we need to close it, the
        socket, and mark ourselves as dead to be cleaned up'''
        self.fh.close()
        self.sock.close()
        self.dead = True

    def handle(self):
        '''Take the message from the parent socket and act accordingly'''
        #if addr not in ongoing, call this, else ready()
        [opcode] = struct.unpack("!H", self.message[:2])
        if opcode == 1:
            self.message = self.message[2:]
            self.newRequest()
        elif opcode == 4:
            [block] = struct.unpack("!H", self.message[2:4])
            if block < self.block:
                self.logger.warning('Ignoring duplicated ACK received for block %d', self.block)
            elif block > self.block:
                self.logger.warning('Ignoring out of sequence ACK received for block %d', self.block)
            elif block == self.lastblock:
                self.logger.debug("Completed sending %s", self.filename)
                self.complete()
            else:
                self.block = block + 1
                self.retries = self.default_retries
                self.sendBlock()


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

        self.logger.debug('NOTICE: TFTP server started in debug mode. TFTP server is using the following:')
        self.logger.debug('  TFTP Server IP: {}'.format(self.ip))
        self.logger.debug('TFTP Server Port: {}'.format(self.port))
        self.logger.debug('  TFTP Network Boot Directory: {}'.format(self.netbootDirectory))

        self.ongoing = []

        # Start in network boot file directory and then chroot, 
        # this simplifies target later as well as offers a slight security increase
        os.chdir (self.netbootDirectory)
        os.chroot ('.')


    def listen(self):
        '''This method listens for incoming requests'''
        while True:
            # Remove complete clients to select doesn't fail
            map(self.ongoing.remove, [client for client in self.ongoing if client.dead])
            rlist, _, _ = select.select([self.sock] + [client.sock for client in self.ongoing if not client.dead], [], [], 0)
            for sock in rlist:
                if sock == self.sock:
                    # main socket, so new client
                    self.ongoing.append(Client(sock, self))
                else:
                    # client socket, so tell the client object it's ready
                    sock.parent.ready()
            # If we haven't recieved an ACK in timeout time, retry
            [client.sendBlock() for client in self.ongoing if client.noACK()]
            # If we have run out of retries, kill the client.
            [client.complete() for client in self.ongoing if client.noRetries()]
