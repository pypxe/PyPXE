import threading
import os
import sys
import json

try:
    import argparse
except ImportError:
    sys.exit("ImportError: You do not have the Python 'argparse' module installed. Please install the 'argparse' module and try again.")

from time import sleep
from pypxe import tftp #PyPXE TFTP service
from pypxe import dhcp #PyPXE DHCP service
from pypxe import http #PyPXE HTTP service

#json default
JSON_CONFIG = ''

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
        parser.add_argument('--config', action = 'store', dest = 'JSON_CONFIG', help = 'Configure from a json file rather than the command line', default = JSON_CONFIG)
        
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
        if args.JSON_CONFIG:
            try:
                config = open(args.JSON_CONFIG)
            except IOError:
                sys.exit("Failed to open %s" % args.JSON_CONFIG)
            try:
                loadedcfg = json.load(config)
                config.close()
            except ValueError:
                sys.exit("%s does not contain valid json" % args.JSON_CONFIG)
            dargs = vars(args)
            dargs.update(loadedcfg)
            args = argparse.Namespace(**dargs)

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
        runningServices = []

        #configure/start TFTP server
        if args.USE_TFTP:
            print 'Starting TFTP server...'
            tftpServer = tftp.TFTPD(mode_debug = args.MODE_DEBUG)
            tftpd = threading.Thread(target = tftpServer.listen)
            tftpd.daemon = True
            tftpd.start()
            runningServices.append(tftpd)

        #configure/start DHCP server
        if args.USE_DHCP:
            if args.DHCP_MODE_PROXY:
                print 'Starting DHCP server in ProxyDHCP mode...'
            else:
                print 'Starting DHCP server...'
            dhcpServer = dhcp.DHCPD(
                    ip = args.DHCP_SERVER_IP,
                    port = args.DHCP_SERVER_PORT,
                    offerfrom = args.DHCP_OFFER_BEGIN,
                    offerto = args.DHCP_OFFER_END,
                    subnet = args.DHCP_SUBNET,
                    router = args.DHCP_ROUTER,
                    dnsserver = args.DHCP_DNS,
                    broadcast = args.DHCP_BROADCAST,
                    fileserver = args.DHCP_FILESERVER,
                    filename = args.NETBOOT_FILE,
                    useipxe = args.USE_IPXE,
                    usehttp = args.USE_HTTP,
                    mode_proxy = args.DHCP_MODE_PROXY,
                    mode_debug = args.MODE_DEBUG)
            dhcpd = threading.Thread(target = dhcpServer.listen)
            dhcpd.daemon = True
            dhcpd.start()
            runningServices.append(dhcpd)


        #configure/start HTTP server
        if args.USE_HTTP:
            print 'Starting HTTP server...'
            httpServer = http.HTTPD(mode_debug = args.MODE_DEBUG)
            httpd = threading.Thread(target = httpServer.listen)
            httpd.daemon = True
            httpd.start()
            runningServices.append(httpd)

        print 'PyPXE successfully initialized and running!'

        while map(lambda x: x.isAlive(), runningServices):
            sleep(1)

    except KeyboardInterrupt:
        sys.exit('\nShutting down PyPXE...\n')
