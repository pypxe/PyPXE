import threading
import os
import argparse
from time import sleep
from httpd import HTTPD
from tftpd import TFTPD
from dhcpd import DHCPD

#Default Network Boot File Directory
NETBOOT_DIR = 'netboot'

#Default PXE Boot File
NETBOOT_FILE = ''

#DHCP Default Server Settings
DHCP_SERVER_IP = '192.168.2.2'
DHCP_FILESERVER_IP = '192.168.2.2'
DHCP_OFFER_BEGIN = '192.168.2.100'
DHCP_OFFER_END = '192.168.2.150'
DHCP_SUBNET = '255.255.255.0'
DHCP_ROUTER = '192.168.2.1'
DHCP_DNS = '8.8.8.8'

if __name__ == '__main__':
    try:
        #warn the user that they are starting PyPXE as non-root user
        if os.getuid() != 0:
            print '\nWARNING: Not root. Servers will probably fail to bind.\n'
        
        #
        # Define Command Line Arguments
        #

        #argument group for DHCP server
        parser = argparse.ArgumentParser(description = 'Set options at runtime. Defaults are in %(prog)s', formatter_class = argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--ipxe', action = 'store_true', dest = 'USE_IPXE', help = 'Enable iPXE ROM', default = False)
        parser.add_argument('--http', action = 'store_true', dest = 'USE_HTTP', help = 'Enable built-in HTTP server', default = False)
        exclusive = parser.add_mutually_exclusive_group(required = False)
        exclusive.add_argument('--dhcp', action = 'store_true', dest = 'USE_DHCP', help = 'Enable built-in DHCP server', default = False)
        exclusive.add_argument('--dhcp-proxy', action = 'store_true', dest = 'DHCP_PROXY_MODE', help = 'Enable built-in DHCP server in proxy mode (implies --dhcp)', default = False)
        parser.add_argument('-s', '--dhcp-server-ip', action = 'store', dest = 'DHCP_SERVER_IP', help = 'DHCP Server IP', default = DHCP_SERVER_IP)
        parser.add_argument('-f', '--dhcp-fileserver-ip', action = 'store', dest = 'DHCP_FILESERVER_IP', help = 'DHCP fileserver IP', default = DHCP_FILESERVER_IP)
        parser.add_argument('-b', '--dhcp-begin', action = 'store', dest = 'DHCP_OFFER_BEGIN', help = 'DHCP lease range start', default = DHCP_OFFER_BEGIN)
        parser.add_argument('-e', '--dhcp-end', action = 'store', dest = 'DHCP_OFFER_END', help = 'DHCP lease range end', default = DHCP_OFFER_END)
        parser.add_argument('-n', '--dhcp-subnet', action = 'store', dest = 'DHCP_SUBNET', help = 'DHCP lease subnet', default = DHCP_SUBNET)
        parser.add_argument('-r', '--dhcp-router', action = 'store', dest = 'DHCP_ROUTER', help = 'DHCP lease router', default = DHCP_ROUTER)
        parser.add_argument('-d', '--dhcp-dns', action = 'store', dest = 'DHCP_DNS', help = 'DHCP lease DNS server', default = DHCP_DNS)

        parser.add_argument('-a', '--netboot-dir', action = 'store', dest = 'NETBOOT_DIR', help = 'Local file serve directory', default = NETBOOT_DIR)
        parser.add_argument('-i', '--netboot-file', action = 'store', dest = 'NETBOOT_FILE', help = 'PXE boot file name (after iPXE if not --no-ipxe)', default = NETBOOT_FILE)

        #parse the arguments given in the command line
        args = parser.parse_args()

        #pass warning to user regarding starting HTTP server without iPXE
        if args.USE_HTTP and not args.USE_IPXE:
            print '\nWARNING: HTTP selected but iPXE disabled. PXE ROM must support HTTP requests.\n'
        
        #if the argument was pased to enabled DHCP proxy mode then enable the DHCP server as well
        if args.DHCP_PROXY_MODE:
            args.USE_DHCP = True

        #if the network boot file name was not specified in the argument, set it based on what services were enabled/disabled
        if args.NETBOOT_FILE == '':
            if not args.USE_IPXE:
                args.NETBOOT_FILE = 'pxelinux.0'
            elif not args.USE_HTTP:
                args.NETBOOT_FILE = 'boot.ipxe'
            else:
                args.NETBOOT_FILE = 'boot.http.ipxe'

        #serve all files from one directory
        os.chdir (args.NETBOOT_DIR)

        #configure/start TFTP server
        tftpd = TFTPD()
        tftpthread = threading.Thread(target = tftpd.listen)
        tftpthread.daemon = True
        tftpthread.start()
        print 'Starting TFTP server...'

        #configure/start DHCP server
        if args.USE_DHCP:
            dhcpd = DHCPD(
                    args.DHCP_SERVER_IP, args.DHCP_FILESERVER_IP,
                    args.DHCP_OFFER_BEGIN,args.DHCP_OFFER_END,
                    args.DHCP_SUBNET, args.DHCP_ROUTER,
                    args.DHCP_DNS, args.NETBOOT_FILE,
                    args.USE_IPXE, args.USE_HTTP, args.DHCP_PROXY_MODE)
            dhcpthread = threading.Thread(target = dhcpd.listen)
            dhcpthread.daemon = True
            dhcpthread.start()
            if args.DHCP_PROXY_MODE:
                print 'Starting DHCP server in proxy mode...'
            else:
                print 'Starting DHCP server...'

        #configure/start HTTP server
        if args.USE_HTTP:
            httpd = HTTPD()
            httpdthread = threading.Thread(target = httpd.listen)
            httpdthread.daemon = True
            httpdthread.start()
            print 'Starting HTTP server...'

        print 'PyPXE successfully initialized and running!'

        while tftpthread.isAlive() or dhcpthread.isAlive() or httpdthread.isAlive():
            sleep(1)

    except KeyboardInterrupt:
        print '\nShutting down PyPXE...\n'