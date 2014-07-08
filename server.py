import threading, os
from time import sleep

from httpd import HTTPD
from tftpd import TFTPD
from dhcpd import DHCPD
if __name__ == '__main__':
    
    os.chdir("netboot")
    USEIPXE = True #boot into ipxe first, then filename
    USEHTTP = True #filename is on fileserver as http
    USEDHCP = True #using DHCP server written above
    PROXYDHCP = True

    if not USEIPXE:
        filename = "/pxelinux.0"
    elif not USEHTTP:
        filename = "/boot.ipxe"
    else:
        filename = "/boot.http.ipxe"

    tftpd = TFTPD()
    tftpthread = threading.Thread(target=tftpd.listen)
    tftpthread.daemon = True
    tftpthread.start()

    if USEDHCP:
        dhcpd = DHCPD('192.168.2.2', '192.168.2.100', '192.168.2.150', '255.255.255.0', '192.168.2.1', '8.8.8.8', filename, '192.168.2.2', USEIPXE, USEHTTP, PROXYDHCP)
        dhcpthread = threading.Thread(target=dhcpd.listen)
        dhcpthread.daemon = True
        dhcpthread.start()

    if USEHTTP:
        httpd = HTTPD()
        httpdthread = threading.Thread(target=httpd.listen)
        httpdthread.daemon = True
        httpdthread.start()

    while True:
        sleep(1)
