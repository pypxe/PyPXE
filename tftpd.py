import socket,binascii,os
from math import ceil
from sys import exit

host = ''
port = 69

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((host, port))

def group(s, n): return [s[i:i+n] for i in xrange(0, len(s), n)]

while 1:
    try:
        message, address = s.recvfrom(8192)
        if message.startswith('\x00\x01'): #WRQ
           message=message.split('\x00')
           filename=message[1][1:]
           print address,"wants",repr(filename)
           if not os.path.exists('.'+filename): s.sendto('\x00\x05\x00\x01no such file exists',address);continue
           fsize=os.path.getsize('.'+filename)
           s.sendto('\x00\x06blksize\x001024\x00tsize\x00%s\x00' % fsize,address) ##512
        elif message.startswith('\x00\x04'): #OptACK
           f=open('.'+filename,'r')
           data=f.read()
           dataset=group(data,1024) ##512
           if len(dataset) > 65534: print "Won't work, too large... >64MB"
           for index,chunk in enumerate(dataset):
              index+=1
              try:
                 s.sendto('\x00\x03'+binascii.unhexlify(hex(index)[2:].rjust(4,'0'))+chunk,address)
              except TypeError: break
              s.recvfrom(128)
    except KeyboardInterrupt:
        exit()
