import threading, os
from time import sleep

from httpd import HTTPD
from tftpd import TFTPD
from dhcpd import DHCPD
if __name__ == '__main__':
    
    #PyPXE Global Settings
    os.chdir("netboot") #local boot file directory
    USE_IPXE = True #boot into ipxe first, then filename
    USE_HTTP = True #filename is on fileserver as http
    USE_DHCP = True #enable/disable built-in DHCP server
    
    #DHCP Server Settings
    DHCP_PROXYDHCP = True
    DHCP_SERVER_IP = '192.168.2.2'
    DHCP_FILESERVER_IP = '192.168.2.2'
    DHCP_OFFER_BEGIN = '192.168.2.100'
    DHCP_OFFER_END = '192.168.2.150'
    DHCP_SUBNET = '255.255.255.0'
    DHCP_ROUTER = '192.168.2.1'
    DHCP_DNS = '8.8.8.8'

    if not USE_IPXE:
        DHCP_FILENAME = "/pxelinux.0"
    elif not USE_HTTP:
        DHCP_FILENAME = "/boot.ipxe"
    else:
        DHCP_FILENAME = "/boot.http.ipxe"

    tftpd = TFTPD()
    tftpthread = threading.Thread(target=tftpd.listen)
    tftpthread.daemon = True
    tftpthread.start()

    if USE_DHCP:
        dhcpd = DHCPD(DHCP_FILESERVER_IP, DHCP_OFFER_BEGIN, DHCP_OFFER_END, DHCP_SUBNET, DHCP_ROUTER, DHCP_DNS, DHCP_FILENAME, DHCP_SERVER_IP, USE_IPXE, USE_HTTP, DHCP_PROXYDHCP)
        dhcpthread = threading.Thread(target=dhcpd.listen)
        dhcpthread.daemon = True
        dhcpthread.start()

    if USE_HTTP:
        httpd = HTTPD()
        httpdthread = threading.Thread(target=httpd.listen)
        httpdthread.daemon = True
        httpdthread.start()

    while True:
        sleep(1)
