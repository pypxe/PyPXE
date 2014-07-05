#!/usr/bin/env python2
import socket,binascii,os
from math import ceil
from sys import exit
from settings import *

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((host, port))

def group(s, n): return [s[i:i+n] for i in xrange(0, len(s), n)]
last=()
while 1:
    try:
        message, address = s.recvfrom(8192)
        if last == address: continue
        if message.startswith('\x00\x01'): #WRQ
           message=message.split('\x00')
           filename=message[1][1:]
           print address,"wants",repr(filename)
           if not os.path.exists('.'+filename):
              s.sendto('\x00\x05\x00\x01no such file exists',address)
              continue
           fsize=os.path.getsize('.'+filename)
           s.sendto('\x00\x06blksize\x00512\x00tsize\x00%s\x00' % fsize,address)
        elif message.startswith('\x00\x04'): #OptACK
           last=address
           f=open('.'+filename,'r')
           data=f.read()
           dataset=group(data,512)
           if len(dataset) > 65534: print "Won't work, too large... >64MB"
           for index,chunk in enumerate(dataset):
              try:
                 s.sendto('\x00\x03'+binascii.unhexlify(hex(index+1)[2:].rjust(4,'0'))+chunk,address)
              except TypeError:
                 break
              s.recvfrom(128)
           s.sendto('\x00\x03'+binascii.unhexlify(hex(index+2)[2:].rjust(4,'0')),address)
           f.close()
    except KeyboardInterrupt:
        exit()
