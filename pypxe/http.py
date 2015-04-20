'''

This file contains classes and functions that implement the PyPXE HTTP service

'''

import socket
import struct
import os
import logging

class HTTPD:
    '''
        This class implements a HTTP Server, limited to GET and HEAD,
        from RFC2616, RFC7230
    '''
    def __init__(self, **serverSettings):
        
        self.ip = serverSettings.get('ip', '0.0.0.0')
        self.port = serverSettings.get('port', 80)
        self.netbootDirectory = serverSettings.get('netbootDirectory', os.getcwd())
        self.mode_debug = serverSettings.get('mode_debug', False) #debug mode
        self.logger =  serverSettings.get('logger', None)

        # setup logger
        if self.logger == None:
            self.logger = logging.getLogger("HTTP")
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s %(name)s [%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        if self.mode_debug:
            self.logger.setLevel(logging.DEBUG)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))
        self.sock.listen(1)

        self.chroot()

        self.logger.debug('NOTICE: HTTP server started in debug mode. HTTP server is using the following:')
        self.logger.debug('  HTTP Server IP: {}'.format(self.ip))
        self.logger.debug('  HTTP Server Port: {}'.format(self.port))
        self.logger.debug('  HTTP Network Boot Directory: {}'.format(self.netbootDirectory))

    def chroot(self):
        # Start in network boot file directory and then chroot, 
        # this simplifies target later as well as offers a slight security increase
        os.chdir (self.netbootDirectory)
        try:
            os.chroot ('.')
        except AttributeError:
            self.logger.warning("Cannot chroot in '{dir}', maybe os.chroot() unsupported by your platform ?".format(dir = self.netbootDirectory))

    def handleRequest(self, connection, addr):
        '''This method handles HTTP request'''
        request = connection.recv(1024)
        self.logger.debug('HTTP Recieved message from {addr}'.format(addr = repr(addr)))
        self.logger.debug('  <--BEGIN MESSAGE-->\n\t{request}\n\t<--END MESSAGE-->'.format(request = repr(request)))
        startline = request.split('\r\n')[0].split(' ')
        method = startline[0]
        req_file = startline[1]

        # avoid directory traversal: strip all ../ and make it relative
        target = os.path.normpath(os.sep + self.netbootDirectory + os.sep + req_file).lstrip(os.sep)

        if not os.path.lexists(target) or not os.path.isfile(target):
            status = '404 Not Found'
        elif method not in ('GET', 'HEAD'):
            status = '501 Not Implemented'
        else:
            status = '200 OK'
        response = 'HTTP/1.1 %s\r\n' % status
        if status[:3] in ('404', '501'): #fail out
            connection.send(response)
            connection.close()
            self.logger.debug('HTTP Sending message to {addr}'.format(addr = repr(addr)))
            self.logger.debug('  <--BEING MESSAGE-->\n\t{response}\n\t<--END MESSAGE-->'.format(response = repr(response)))
            return
        response += 'Content-Length: %d\r\n' % os.path.getsize(target)
        response += '\r\n'
        if method == 'HEAD':
            connection.send(response)
            connection.close()
            self.logger.debug('HTTP Sending message to {addr}'.format(addr = repr(addr)))
            self.logger.debug('  <--BEING MESSAGE-->\n\t{response}\n\t<--END MESSAGE-->'.format(response = repr(response)))
            return
        handle = open(target)
        response += handle.read()
        handle.close()
        connection.send(response)
        connection.close()
        self.logger.debug('HTTP Sending message to {addr}'.format(addr = repr(addr)))
        self.logger.debug('  <--BEING MESSAGE-->\n\t{response}\n\t<--END MESSAGE-->'.format(response = repr(response)))
        self.logger.debug('  HTTP File Sent - http://{req_file} -> {addr[0]}:{addr[1]}'.format(req_file = req_file, addr = addr))

    def listen(self):
        '''This method is the main loop that listens for requests'''
        while True:
            conn, addr = self.sock.accept()
            self.handleRequest(conn, addr)
