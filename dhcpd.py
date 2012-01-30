#!/usr/bin/env python2
#dhcpd.py pure python dhcp server
#pxe capable
import socket, binascii,time
from sys import exit
host = ''
port = 67
serverhost='192.168.2.3'
offerfrom='192.168.2.100'
offerto='192.168.2.150'
subnetmask='255.255.255.0'
broadcast='192.168.2.255'
router='192.168.2.1'
dnsserver='8.8.8.8'
leasetime=86400 #int

tftpserver='192.168.2.3'
pxefilename='/netboot/pxelinux.0'

leases=[]
for ip in ['192.168.2.'+str(x) for x in range(int(offerfrom[offerfrom.rfind('.')+1:]),int(offerto[offerto.rfind('.')+1:])+1)]:
   leases.append([ip,False,'000000000000',0])

def release(): #release a lease after timelimit has expired
   for lease in leases:
      if not lease[1]:
         if time.time()+leasetime == leasetime: continue
         if lease[-1] > time.time()+leasetime:
            print "Released",lease[0]
            lease[1]=False
            lease[2]='000000000000'
            lease[3]=0

def getlease(hwaddr): #return the lease of mac address, or create if doesn't exist
   global leases
   for lease in leases:
      if hwaddr == lease[2]:
         return lease[0]
   for lease in leases:
      if not lease[1]:
         lease[1]=True
         lease[2]=hwaddr
         lease[3]=time.time()
         return lease[0]

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.bind((host, port))
#s.sendto(data,(ip,port))

dhcpfields=[1,1,1,1,4,2,2,4,4,4,4,6,10,192,4,"msg.rfind('\xff')",1,None] #see wikipedia page
def slicendice(msg,slices=dhcpfields): 
   for x in slices:
      if str(type(x)) == "<type 'str'>": x=eval(x) #really dirty, deals with variable length options
      yield msg[:x]
      msg = msg[x:]

def reqparse(message): #handles either DHCPDiscover or DHCPRequest
   data=None
   #send: boolean as to whether to send data back, and data: data to send, if any
   #print len(message)
   hexmessage=binascii.hexlify(message)
   messagesplit=[binascii.hexlify(x) for x in slicendice(message)]
   dhcpopt=messagesplit[15][:6] #hope DHCP type is first. Should be.
   if dhcpopt == '350101':
      #DHCPDiscover
      #craft DHCPOffer
      #DHCPOFFER creation:
      #options = \xcode \xlength \xdata
      lease=getlease(messagesplit[11])
      print 'Leased:',lease
      data='\x02\x01\x06\x00'+binascii.unhexlify(messagesplit[4])+'\x00\x04'+'\x80\x00'+'\x00'*4+socket.inet_aton(lease) #see wikipedia tables for info.
      data+=socket.inet_aton(serverhost)+'\x00'*4+binascii.unhexlify(messagesplit[11])+'\x00'*10+'\x00'*192
      data+='\x63\x82\x53\x63'+'\x35\x01\x02'+'\x01\x04'+socket.inet_aton(subnetmask)+'\x36\x04'+socket.inet_aton(serverhost)
      data+='\x1c\x04'+socket.inet_aton(broadcast)+'\x03\x04'+socket.inet_aton(router)+'\x06\x04'+socket.inet_aton(dnsserver)
      data+='\x33\x04'+binascii.unhexlify(hex(leasetime)[2:].rjust(8,'0'))+'\x42'+binascii.unhexlify(hex(len(tftpserver))[2:].rjust(2,'0'))+tftpserver
      data+='\x43'+binascii.unhexlify(hex(len(pxefilename)+1)[2:].rjust(2,'0'))+pxefilename+'\x00\xff'
   elif dhcpopt == '350103':
      #DHCPRequest
      #craft DHCPACK
      data='\x02\x01\x06\x00'+binascii.unhexlify(messagesplit[4])+'\x00'*8
      data+=binascii.unhexlify(messagesplit[15][messagesplit[15].find('3204')+4:messagesplit[15].find('3204')+12])
      data+=socket.inet_aton(serverhost)+'\x00'*4
      data+=binascii.unhexlify(messagesplit[11])+'\x00'*202+'\x63\x82\x53\x63'+'\x35\x01\05'+'\x36\x04'+socket.inet_aton(serverhost)+'\x01\x04'
      data+=socket.inet_aton(subnetmask)+'\x03\x04'+socket.inet_aton(serverhost)+'\x33\x04'+binascii.unhexlify(hex(leasetime)[2:].rjust(8,'0'))
      data+='\x42'+binascii.unhexlify(hex(len(tftpserver))[2:].rjust(2,'0'))+tftpserver
      data+='\x43'+binascii.unhexlify(hex(len(pxefilename)+1)[2:].rjust(2,'0'))+pxefilename+'\x00\xff'
   return data

while 1: #main loop
    try:
        message, address = s.recvfrom(8192)
        if not message.startswith('\x01') and not address[0] == '0.0.0.0': #only if request is a dhcp request
           continue
        data=reqparse(message) #handle request
        if data:
           s.sendto(data,('<broadcast>',68)) #reply
        release() #update releases table
    except KeyboardInterrupt:
        exit()
#    except:
#        continue
