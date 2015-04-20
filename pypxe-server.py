import threading
import os
import sys
import json
import logging
import logging.handlers
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
        try:
            if os.getuid() != 0:
                print '\nWARNING: Not root. Servers will probably fail to bind.\n'
        except AttributeError:
            print '\nWARNING: Unable to check your user privileges'
        #
        # Define Command Line Arguments
        #

        #main service arguments
        parser = argparse.ArgumentParser(description = 'Set options at runtime. Defaults are in %(prog)s', formatter_class = argparse.ArgumentDefaultsHelpFormatter)
        parser.add_argument('--ipxe', action = 'store_true', dest = 'USE_IPXE', help = 'Enable iPXE ROM', default = False)
        parser.add_argument('--http', action = 'store_true', dest = 'USE_HTTP', help = 'Enable built-in HTTP server', default = False)
        parser.add_argument('--no-tftp', action = 'store_false', dest = 'USE_TFTP', help = 'Disable built-in TFTP server, by default it is enabled', default = True)
        parser.add_argument('--debug', action = 'store', dest = 'MODE_DEBUG', help = 'Comma Seperated (http,tftp,dhcp). Adds verbosity to the selected services while they run. Use \'all\' for enabling debug on all services', default = '')
        parser.add_argument('--config', action = 'store', dest = 'JSON_CONFIG', help = 'Configure from a json file rather than the command line', default = JSON_CONFIG)
        parser.add_argument('--syslog', action = 'store', dest = 'SYSLOG_SERVER', help = 'Syslog server', default = None)
        parser.add_argument('--syslog-port', action = 'store', dest = 'SYSLOG_PORT', help = 'Syslog server port', default = 514)

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

        # setup main logger
        sys_logger = logging.getLogger("PyPXE")
        if args.SYSLOG_SERVER:
            handler = logging.handlers.SysLogHandler(address = (args.SYSLOG_SERVER, int(args.SYSLOG_PORT)))
        else:
            handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s %(name)s [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        sys_logger.addHandler(handler)
        sys_logger.setLevel(logging.INFO)

        #pass warning to user regarding starting HTTP server without iPXE
        if args.USE_HTTP and not args.USE_IPXE and not args.USE_DHCP:
            sys_logger.warning('WARNING: HTTP selected but iPXE disabled. PXE ROM must support HTTP requests.')
        
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
        os.chdir(os.path.abspath(args.NETBOOT_DIR))
        
        #make a list of running threads for each service
        runningServices = []

        #configure/start TFTP server
        if args.USE_TFTP:
            # setup tftp logger
            tftp_logger = sys_logger.getChild("TFTP")
            sys_logger.info('Starting TFTP server...')
            tftpServer = tftp.TFTPD(mode_debug = ("tftp" in args.MODE_DEBUG.lower() or "all" in args.MODE_DEBUG.lower()), logger = tftp_logger)
            tftpd = threading.Thread(target = tftpServer.listen)
            tftpd.daemon = True
            tftpd.start()
            runningServices.append(tftpd)

        #configure/start DHCP server
        if args.USE_DHCP:
            # setup dhcp logger
            dhcp_logger = sys_logger.getChild("DHCP")
            if args.DHCP_MODE_PROXY:
                sys_logger.info('Starting DHCP server in ProxyDHCP mode...')
            else:
                sys_logger.info('Starting DHCP server...')
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
                    mode_debug = ("dhcp" in args.MODE_DEBUG.lower() or "all" in args.MODE_DEBUG.lower()),
                    logger = dhcp_logger)
            dhcpd = threading.Thread(target = dhcpServer.listen)
            dhcpd.daemon = True
            dhcpd.start()
            runningServices.append(dhcpd)

        #configure/start HTTP server
        if args.USE_HTTP:
            # setup http logger
            http_logger = sys_logger.getChild("HTTP")
            sys_logger.info('Starting HTTP server...')
            httpServer = http.HTTPD(mode_debug = ("http" in args.MODE_DEBUG.lower() or "all" in args.MODE_DEBUG.lower()), logger = http_logger)
            httpd = threading.Thread(target = httpServer.listen)
            httpd.daemon = True
            httpd.start()
            runningServices.append(httpd)

        sys_logger.info('PyPXE successfully initialized and running!')

        while map(lambda x: x.isAlive(), runningServices):
            sleep(1)

    except KeyboardInterrupt:
        sys.exit('\nShutting down PyPXE...\n')
