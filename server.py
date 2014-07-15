import threading
import os
import sys

try:
    import argparse
except ImportError:
    sys.exit("ImportError: You do not have the Python 'argparse' module installed. Please install the 'argparse' module and try again.")

from time import sleep
from pypxe.httpd import HTTPD
from pypxe.tftpd import TFTPD
from pypxe.dhcpd import DHCPD

#Default Network Boot File Directory
NETBOOT_DIR = 'netboot'

#Default PXE Boot File
NETBOOT_FILE = ''

#DHCP Default Server Settings
DHCP_SERVER_IP = '192.168.2.2'
DHCP_SERVER_PORT = 67
DHCP_OFFER_BEGIN = '192.168.2.100'
DHCP_OFFER_END = '192.168.2.150'
DHCP_SUBNET = '255.255.255.0'
DHCP_ROUTER = '192.168.2.1'
DHCP_DNS = '8.8.8.8'
DHCP_BROADCAST = '<broadcast>'
DHCP_FILESERVER = '192.168.2.2'

if __name__ == '__main__':
    try:
        #warn the user that they are starting PyPXE as non-root user
        if os.getuid() != 0:
            print '\nWARNING: Not root. Servers will probably fail to bind.\n'
        
        #
        # Define Command Line Arguments
        #

        #main service arguments
        parser = argparse.ArgumentParser(description = 'Set options at runtime. Defaults are in %(prog)s', formatter_class = argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--ipxe', action = 'store_true', dest = 'USE_IPXE', help = 'Enable iPXE ROM', default = False)
        parser.add_argument('--http', action = 'store_true', dest = 'USE_HTTP', help = 'Enable built-in HTTP server', default = False)
        parser.add_argument('--no-tftp', action = 'store_false', dest = 'USE_TFTP', help = 'Disable built-in TFTP server, by default it is enabled', default = True)
        parser.add_argument('--debug', action = 'store_true', dest = 'MODE_DEBUG', help = 'Adds verbosity to the selected services while they run', default = False)
        
        #argument group for DHCP server
        exclusive = parser.add_mutually_exclusive_group(required = False)
        exclusive.add_argument('--dhcp', action = 'store_true', dest = 'USE_DHCP', help = 'Enable built-in DHCP server', default = False)
        exclusive.add_argument('--dhcp-proxy', action = 'store_true', dest = 'DHCP_MODE_PROXY', help = 'Enable built-in DHCP server in proxy mode (implies --dhcp)', default = False)
        parser.add_argument('-s', '--dhcp-server-ip', action = 'store', dest = 'DHCP_SERVER_IP', help = 'DHCP Server IP', default = DHCP_SERVER_IP)
        parser.add_argument('-p', '--dhcp-server-port', action = 'store', dest = 'DHCP_SERVER_PORT', help = 'DHCP Server Port', default = DHCP_SERVER_PORT)
        parser.add_argument('-b', '--dhcp-begin', action = 'store', dest = 'DHCP_OFFER_BEGIN', help = 'DHCP lease range start', default = DHCP_OFFER_BEGIN)
        parser.add_argument('-e', '--dhcp-end', action = 'store', dest = 'DHCP_OFFER_END', help = 'DHCP lease range end', default = DHCP_OFFER_END)
        parser.add_argument('-n', '--dhcp-subnet', action = 'store', dest = 'DHCP_SUBNET', help = 'DHCP lease subnet', default = DHCP_SUBNET)
        parser.add_argument('-r', '--dhcp-router', action = 'store', dest = 'DHCP_ROUTER', help = 'DHCP lease router', default = DHCP_ROUTER)
        parser.add_argument('-d', '--dhcp-dns', action = 'store', dest = 'DHCP_DNS', help = 'DHCP lease DNS server', default = DHCP_DNS)
        parser.add_argument('-c', '--dhcp-broadcast', action = 'store', dest = 'DHCP_BROADCAST', help = 'DHCP broadcast address', default = DHCP_BROADCAST)
        parser.add_argument('-f', '--dhcp-fileserver', action = 'store', dest = 'DHCP_FILESERVER', help = 'DHCP fileserver IP', default = DHCP_FILESERVER)

        #network boot directory and file name arguments
        parser.add_argument('-a', '--netboot-dir', action = 'store', dest = 'NETBOOT_DIR', help = 'Local file serve directory', default = NETBOOT_DIR)
        parser.add_argument('-i', '--netboot-file', action = 'store', dest = 'NETBOOT_FILE', help = 'PXE boot file name (after iPXE if --ipxe)', default = NETBOOT_FILE)

        #parse the arguments given
        args = parser.parse_args()

        #pass warning to user regarding starting HTTP server without iPXE
        if args.USE_HTTP and not args.USE_IPXE and not args.USE_DHCP:
            print '\nWARNING: HTTP selected but iPXE disabled. PXE ROM must support HTTP requests.\n'
        
        #if the argument was pased to enabled ProxyDHCP then enable the DHCP server
        if args.DHCP_MODE_PROXY:
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
        
        #make a list of running threads for each service
        threads = []

        #configure/start TFTP server
        if args.USE_TFTP:
            print 'Starting TFTP server...'
            tftpd = TFTPD(mode_debug = args.MODE_DEBUG)
            tftpthread = threading.Thread(target = tftpd.listen)
            tftpthread.daemon = True
            tftpthread.start()
            threads.append(tftpthread)

        #configure/start DHCP server
        if args.USE_DHCP:
            if args.DHCP_MODE_PROXY:
                print 'Starting DHCP server in ProxyDHCP mode...'
            else:
                print 'Starting DHCP server...'
            dhcpd = DHCPD(
                    args.DHCP_SERVER_IP,
                    args.DHCP_SERVER_PORT,
                    args.DHCP_OFFER_BEGIN,
                    args.DHCP_OFFER_END,
                    args.DHCP_SUBNET,
                    args.DHCP_ROUTER,
                    args.DHCP_DNS,
                    args.DHCP_BROADCAST,
                    args.DHCP_FILESERVER,
                    args.NETBOOT_FILE,
                    args.USE_IPXE,
                    args.USE_HTTP,
                    args.DHCP_MODE_PROXY,
                    args.MODE_DEBUG)
            dhcpthread = threading.Thread(target = dhcpd.listen)
            dhcpthread.daemon = True
            dhcpthread.start()
            threads.append(dhcpthread)


        #configure/start HTTP server
        if args.USE_HTTP:
            print 'Starting HTTP server...'
            httpd = HTTPD(mode_debug = args.MODE_DEBUG)
            httpthread = threading.Thread(target = httpd.listen)
            httpthread.daemon = True
            httpthread.start()
            threads.append(httpthread)

        print 'PyPXE successfully initialized and running!'

        while map(lambda x: x.isAlive(), threads):
            sleep(1)

    except KeyboardInterrupt:
        sys.exit('\nShutting down PyPXE...\n')
