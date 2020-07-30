'''

This file contains classes and functions that implement the PyPXE HTTP service

'''

import socket
import struct
import os
import threading
import logging
from pypxe import helpers

class HTTPD:
    '''
        This class implements a HTTP Server, limited to GET and HEAD,
        from RFC2616, RFC7230.
    '''
    def __init__(self, **server_settings):

        self.ip = server_settings.get('ip', '0.0.0.0')
        self.port = int(server_settings.get('port', 80))
        self.netboot_directory = server_settings.get('netboot_directory', '.')
        self.mode_verbose = server_settings.get('mode_verbose', False) # verbose mode
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
        elif self.mode_verbose:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.WARN)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip, self.port))
        self.sock.listen(1)

        self.logger.debug('NOTICE: HTTP server started in debug mode. HTTP server is using the following:')
        self.logger.info('Server IP: {0}'.format(self.ip))
        self.logger.info('Server Port: {0}'.format(self.port))
        self.logger.info('Network Boot Directory: {0}'.format(self.netboot_directory))

    def handle_request(self, connection, addr):
        '''This method handles HTTP request.'''
        request = connection.recv(1024)
        self.logger.debug('Received message from {addr}'.format(addr = repr(addr)))
        self.logger.debug('<--BEGIN MESSAGE-->')
        self.logger.debug('{0}'.format(repr(request)))
        self.logger.debug('<--END MESSAGE-->')
        method, target, version = request.decode('ascii').split('\r\n')[0].split(' ')
        target = target.lstrip('/')
        try:
            self.logger.debug("Netboot: {0}, Target: {1}".format(self.netboot_directory, target))
            target = helpers.normalize_path(self.netboot_directory, target)
            if not os.path.lexists(target) or not os.path.isfile(target):
                status = '404 Not Found'
            elif method not in ('GET', 'HEAD'):
                status = '501 Not Implemented'
            else:
                status = '200 OK'
        except helpers.PathTraversalException:
            status = '403 Forbidden'
        response = 'HTTP/1.1 {0}\r\n'.format(status)
        if status[:3] != '200': # fail out
            connection.send(response.encode('ascii'))
            connection.close()
            self.logger.warn('Sending {status} to {addr[0]}:{addr[1]} for {target}'.format(status = status, target = target, addr = addr))
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
        connection.send(response.encode('ascii'))
        with open(target, 'rb') as handle:
            while True:
                data = handle.read(8192)
                if not data: break
                connection.send(data)
        connection.close()
        self.logger.info('File Sent - {target} -> {addr[0]}:{addr[1]}'.format(target = target, addr = addr))

    def listen(self):
        '''This method is the main loop that listens for requests.'''
        while True:
            conn, addr = self.sock.accept()
            client = threading.Thread(target = self.handle_request, args = (conn, addr))
            client.daemon = True;
            client.start()
