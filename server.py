import threading, os, argparse
from time import sleep

from httpd import HTTPD
from tftpd import TFTPD
from dhcpd import DHCPD
if __name__ == '__main__':
    if os.getuid() != 0:
        print "\nWarning: Not root. Servers will probably fail to bind.\n"
    
    #PyPXE Global Settings
    NETBOOT = "netboot" #local boot file directory
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

    parser = argparse.ArgumentParser(description="Set options at runtime. Defaults are in %(prog)s", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    exclusive = parser.add_mutually_exclusive_group(required=False)
    exclusive.add_argument("--dhcp", action="store_true", dest="USE_DHCP", help="Use builtin DHCP server", default=USE_DHCP)
    exclusive.add_argument("--proxydhcp", action="store_true", dest="DHCP_PROXYDHCP", help="Use builtin DHCP server in proxy mode (implies --dhcp)", default=DHCP_PROXYDHCP)
    exclusive.add_argument("--no-dhcp", action="store_false", dest="USE_DHCP", help="Disable builtin DHCP server", default=not USE_DHCP)

    exclusive = parser.add_mutually_exclusive_group(required=False)
    exclusive.add_argument("--ipxe", action="store_true", dest="USE_IPXE", help="Chainload iPXE rom", default=USE_IPXE)
    exclusive.add_argument("--no-ipxe", action="store_false", dest="USE_IPXE", help="Don't chainload iPXE rom", default=not USE_IPXE)

    exclusive = parser.add_mutually_exclusive_group(required=False)
    exclusive.add_argument("--http", action="store_true", dest="USE_HTTP", help="Use builtin HTTP server", default=USE_HTTP)
    exclusive.add_argument("--no-http", action="store_false", dest="USE_HTTP", help="Don't use builtin HTTP server", default=not USE_HTTP)

    parser.add_argument("-s", "--server", action="store", dest="DHCP_SERVER_IP", help="DHCP Server IP", default=DHCP_SERVER_IP)
    parser.add_argument("-f", "--fileserver", action="store", dest="DHCP_FILESERVER_IP", help="Fileserver IP", default=DHCP_FILESERVER_IP)
    parser.add_argument("-b", "--begin", action="store", dest="DHCP_OFFER_BEGIN", help="DHCP lease range start", default=DHCP_OFFER_BEGIN)
    parser.add_argument("-e", "--end", action="store", dest="DHCP_OFFER_END", help="DHCP lease range end", default=DHCP_OFFER_END)
    parser.add_argument("-n", "--subnet", action="store", dest="DHCP_SUBNET", help="DHCP lease subnet", default=DHCP_SUBNET)
    parser.add_argument("-r", "--router", action="store", dest="DHCP_ROUTER", help="DHCP lease router", default=DHCP_ROUTER)
    parser.add_argument("-d", "--dns", action="store", dest="DHCP_DNS", help="DHCP lease DNS server", default=DHCP_DNS)
    parser.add_argument("-a", "--netboot", action="store", dest="NETBOOT", help="File serve directory", default=NETBOOT)
    parser.add_argument("-i", "--filename", action="store", dest="DHCP_FILENAME", help="PXE filename (after iPXE if --ipxe", default=DHCP_FILENAME)

    args = parser.parse_args()
    if args.USE_HTTP and not args.USE_IPXE:
        print "\nWarning: HTTP selected but iPXE disabled. PXE ROM must support HTTP requests.\n"
    if args.PROXY_PROXYDHCP:
        args.USE_DHCP = True

    os.chdir(args.NETBOOT)


    tftpd = TFTPD()
    tftpthread = threading.Thread(target=tftpd.listen)
    tftpthread.daemon = True
    tftpthread.start()

    if args.USE_DHCP:
        dhcpd = DHCPD(args.DHCP_FILESERVER_IP, args.DHCP_OFFER_BEGIN, args.DHCP_OFFER_END, args.DHCP_SUBNET, args.DHCP_ROUTER, args.DHCP_DNS, args.DHCP_FILENAME, args.DHCP_SERVER_IP, args.USE_IPXE, args.USE_HTTP, args.DHCP_PROXYDHCP)
        dhcpthread = threading.Thread(target=dhcpd.listen)
        dhcpthread.daemon = True
        dhcpthread.start()

    if args.USE_HTTP:
        httpd = HTTPD()
        httpdthread = threading.Thread(target=httpd.listen)
        httpdthread.daemon = True
        httpdthread.start()

    while True:
        sleep(1)
