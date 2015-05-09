'''

This file contains classes and functions that implement the PyPXE HTTP service

'''

import socket
import struct
import os
import threading
import logging

class HTTPD:
    '''
        This class implements a HTTP Server, limited to GET and HEAD,
        from RFC2616, RFC7230.
    '''
    def __init__(self, **server_settings):

        self.ip = server_settings.get('ip', '0.0.0.0')
        self.port = server_settings.get('port', 80)
        self.netboot_directory = server_settings.get('netboot_directory', '.')
        self.mode_debug = server_settings.get('mode_debug', False) # debug mode
        self.logger =  server_settings.get('logger', None)

        # setup logger
        if self.logger == None:
            self.logger = logging.getLogger('HTTP')
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        if self.mode_debug:
            self.logger.setLevel(logging.DEBUG)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))
        self.sock.listen(1)

        # start in network boot file directory and then chroot,
        # this simplifies target later as well as offers a slight security increase
        os.chdir (self.netboot_directory)
        os.chroot ('.')

        self.logger.debug('NOTICE: HTTP server started in debug mode. HTTP server is using the following:')
        self.logger.debug('HTTP Server IP: {0}'.format(self.ip))
        self.logger.debug('HTTP Server Port: {0}'.format(self.port))
        self.logger.debug('HTTP Network Boot Directory: {0}'.format(self.netboot_directory))

    def handle_request(self, connection, addr):
        '''This method handles HTTP request.'''
        request = connection.recv(1024)
        self.logger.debug('Recieved message from {addr}'.format(addr = repr(addr)))
        self.logger.debug('<--BEGIN MESSAGE-->')
        self.logger.debug('{0}'.format(repr(request)))
        self.logger.debug('<--END MESSAGE-->')
        method, target, version = request.split('\r\n')[0].split(' ')
        if not os.path.lexists(target) or not os.path.isfile(target):
            status = '404 Not Found'
        elif method not in ('GET', 'HEAD'):
            status = '501 Not Implemented'
        else:
            status = '200 OK'
        response = 'HTTP/1.1 {0}\r\n'.format(status)
        if status[:3] in ('404', '501'): # fail out
            connection.send(response)
            connection.close()
            self.logger.debug('Sending message to {0}'.format(repr(addr)))
            self.logger.debug('<--BEING MESSAGE-->')
            self.logger.debug('{0}'.format(repr(response)))
            self.logger.debug('<--END MESSAGE-->')
            return
        response += 'Content-Length: {0}\r\n'.format(os.path.getsize(target))
        response += '\r\n'
        if method == 'HEAD':
            connection.send(response)
            connection.close()
            self.logger.debug('Sending message to {0}'.format(repr(addr)))
            self.logger.debug('<--BEING MESSAGE-->')
            self.logger.debug('{0}'.format(repr(response)))
            self.logger.debug('<--END MESSAGE-->')
            return
        handle = open(target, 'rb')
        response += handle.read()
        handle.close()
        connection.send(response)
        connection.close()
        self.logger.debug('Sending message to {0}'.format(repr(addr)))
        self.logger.debug('<--BEING MESSAGE-->')
        self.logger.debug('{0}'.format(repr(response)))
        self.logger.debug('<--END MESSAGE-->')
        self.logger.debug('File Sent - http://{target} -> {addr[0]}:{addr[1]}'.format(target = target, addr = addr))

    def listen(self):
        '''This method is the main loop that listens for requests.'''
        while True:
            conn, addr = self.sock.accept()
            client = threading.Thread(target = self.handle_request, args = (conn, addr))
            client.daemon = True;
            client.start()
