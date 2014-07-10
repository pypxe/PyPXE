import threading, os, argparse
from time import sleep
from httpd import HTTPD
from tftpd import TFTPD
from dhcpd import DHCPD

#Default Network Boot File Directory
NETBOOTDIR = 'netboot'

#DHCP Default Server Settings
DHCP_PROXYMODE = False
DHCP_SERVER_IP = '192.168.2.2'
DHCP_FILESERVER_IP = '192.168.2.2'
DHCP_OFFER_BEGIN = '192.168.2.100'
DHCP_OFFER_END = '192.168.2.150'
DHCP_SUBNET = '255.255.255.0'
DHCP_ROUTER = '192.168.2.1'
DHCP_DNS = '8.8.8.8'

if __name__ == '__main__':
    
    try:

        if os.getuid() != 0:
            print "\nWARNING: Not root. Servers will probably fail to bind.\n"

        #define command line arguments
        parser = argparse.ArgumentParser(description="Set options at runtime. Defaults are in %(prog)s", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        exclusive = parser.add_mutually_exclusive_group(required=False)
        exclusive.add_argument("--dhcp", action="store_true", dest="USE_DHCP", help="Use builtin DHCP server (use with --proxydhcp for proxy mode)", default=True)
        exclusive.add_argument("--proxydhcp", action="store_true", dest="DHCP_PROXYMODE", help="Use builtin DHCP server in proxy mode (implies --dhcp)", default=DHCP_PROXYMODE)
        exclusive.add_argument("--no-dhcp", action="store_false", dest="USE_DHCP", help="Disable builtin DHCP server")

        exclusive = parser.add_mutually_exclusive_group(required=False)
        exclusive.add_argument("--ipxe", action="store_true", dest="USE_IPXE", help="Chainload iPXE ROM", default=True)
        exclusive.add_argument("--no-ipxe", action="store_false", dest="USE_IPXE", help="Don't chainload iPXE ROM")

        exclusive = parser.add_mutually_exclusive_group(required=False)
        exclusive.add_argument("--http", action="store_true", dest="USE_HTTP", help="Use builtin HTTP server", default=True)
        exclusive.add_argument("--no-http", action="store_false", dest="USE_HTTP", help="Don't use builtin HTTP server")

        parser.add_argument("-s", "--server", action="store", dest="DHCP_SERVER_IP", help="DHCP Server IP", default=DHCP_SERVER_IP)
        parser.add_argument("-f", "--fileserver", action="store", dest="DHCP_FILESERVER_IP", help="Fileserver IP", default=DHCP_FILESERVER_IP)
        parser.add_argument("-b", "--begin", action="store", dest="DHCP_OFFER_BEGIN", help="DHCP lease range start", default=DHCP_OFFER_BEGIN)
        parser.add_argument("-e", "--end", action="store", dest="DHCP_OFFER_END", help="DHCP lease range end", default=DHCP_OFFER_END)
        parser.add_argument("-n", "--subnet", action="store", dest="DHCP_SUBNET", help="DHCP lease subnet", default=DHCP_SUBNET)
        parser.add_argument("-r", "--router", action="store", dest="DHCP_ROUTER", help="DHCP lease router", default=DHCP_ROUTER)
        parser.add_argument("-d", "--dns", action="store", dest="DHCP_DNS", help="DHCP lease DNS server", default=DHCP_DNS)
        parser.add_argument("-a", "--netboot", action="store", dest="NETBOOTDIR", help="File serve directory", default=NETBOOTDIR)
        parser.add_argument("-i", "--filename", action="store", dest="DHCP_FILENAME", help="PXE filename (after iPXE if --ipxe", default='')

        #parse the arguments given in the command line
        args = parser.parse_args()

        #pass warning to user regarding starting HTTP server without iPXE
        if args.USE_HTTP and not args.USE_IPXE:
            print "\nWARNING: HTTP selected but iPXE disabled. PXE ROM must support HTTP requests.\n"
        
        #if the argument was pased to enabled DHCP proxy mode then enable the DHCP server as well
        if args.DHCP_PROXYMODE:
            args.USE_DHCP = True

        #if the DHCP file name was not specified in the argument, set it based on what services were enabled/disabled
        if args.DHCP_FILENAME == '':
            if not args.USE_IPXE:
                args.DHCP_FILENAME = "/pxelinux.0"
            elif not args.USE_HTTP:
                args.DHCP_FILENAME = "/boot.ipxe"
            else:
                args.DHCP_FILENAME = "/boot.http.ipxe"

        os.chdir(args.NETBOOTDIR)

        #configure/start TFTP server
        tftpd = TFTPD()
        tftpthread = threading.Thread(target=tftpd.listen)
        tftpthread.daemon = True
        tftpthread.start()
        print 'Starting TFTP server...'

        #configure/start DHCP server
        if args.USE_DHCP:
            dhcpd = DHCPD(args.DHCP_FILESERVER_IP, args.DHCP_OFFER_BEGIN, args.DHCP_OFFER_END, args.DHCP_SUBNET, args.DHCP_ROUTER, args.DHCP_DNS, args.DHCP_FILENAME, args.DHCP_SERVER_IP, args.USE_IPXE, args.USE_HTTP, args.DHCP_PROXYMODE)
            dhcpthread = threading.Thread(target=dhcpd.listen)
            dhcpthread.daemon = True
            dhcpthread.start()
            if args.DHCP_PROXYMODE:
                print 'Starting DHCP server in proxy mode...'
            else:
                print 'Starting DHCP server...'

        #configure/start HTTP server
        if args.USE_HTTP:
            httpd = HTTPD()
            httpdthread = threading.Thread(target=httpd.listen)
            httpdthread.daemon = True
            httpdthread.start()
            print 'Starting HTTP server...'

        print 'PyPXE successfully initialized and running!'

        while tftpthread.isAlive() or dhcpthread.isAlive() or httpdthread.isAlive():
            sleep( 1 )

    except KeyboardInterrupt:
        print '\nShutting down PyPXE...\n'