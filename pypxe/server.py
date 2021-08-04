#!/usr/bin/env python
import threading
import io
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
from pypxe import tftp # PyPXE TFTP service
from pypxe import dhcp # PyPXE DHCP service
from pypxe import http # PyPXE HTTP service
from pypxe import nbd  # PyPXE NBD service
from pypxe import helpers
args = None
# default settings
SETTINGS = {'NETBOOT_DIR':'netboot',
            'NETBOOT_FILE':'',
            'DHCP_SERVER_IP':'192.168.2.2',
            'DHCP_SERVER_PORT':67,
            'DHCP_OFFER_BEGIN':'192.168.2.100',
            'DHCP_OFFER_END':'192.168.2.150',
            'DHCP_SUBNET':'255.255.255.0',
            'DHCP_DNS':'8.8.8.8',
            'DHCP_ROUTER':'192.168.2.1',
            'DHCP_BROADCAST':'',
            'DHCP_FILESERVER':'192.168.2.2',
            'DHCP_WHITELIST':False,
            'HTTP_PORT':80,
            'HTTP_SERVER_IP':'0.0.0.0',
            'LEASES_FILE':'',
            'STATIC_CONFIG':'',
            'SYSLOG_SERVER':None,
            'SYSLOG_PORT':514,
            'TFTP_SERVER_IP':'0.0.0.0',
            'USE_IPXE':False,
            'USE_HTTP':False,
            'USE_TFTP':True,
            'USE_DHCP':False,
            'DHCP_MODE_PROXY':False,
            'NBD_BLOCK_DEVICE':'',
            'NBD_WRITE':False,
            'NBD_COW':True,
            'NBD_COW_IN_MEM':False,
            'NBD_COPY_TO_RAM':False,
            'NBD_SERVER_IP':'0.0.0.0',
            'NBD_PORT':10809,
            'MODE_DEBUG':'',
            'MODE_VERBOSE':''}

def parse_cli_arguments():
    # main service arguments
    parser = argparse.ArgumentParser(description = 'Set options at runtime. Defaults are in %(prog)s', formatter_class = argparse.ArgumentDefaultsHelpFormatter)

    ipxeexclusive = parser.add_mutually_exclusive_group(required = False)
    ipxeexclusive.add_argument('--ipxe', action = 'store_true', dest = 'USE_IPXE', help = 'Enable iPXE ROM', default = SETTINGS['USE_IPXE'])
    ipxeexclusive.add_argument('--no-ipxe', action = 'store_false', dest = 'USE_IPXE', help = 'Disable iPXE ROM', default = not SETTINGS['USE_IPXE'])

    httpexclusive = parser.add_mutually_exclusive_group(required = False)
    httpexclusive.add_argument('--http', action = 'store_true', dest = 'USE_HTTP', help = 'Enable built-in HTTP server', default = SETTINGS['USE_HTTP'])
    httpexclusive.add_argument('--no-http', action = 'store_false', dest = 'USE_HTTP', help = 'Disable built-in HTTP server', default = not SETTINGS['USE_HTTP'])

    tftpexclusive = parser.add_mutually_exclusive_group(required = False)
    tftpexclusive.add_argument('--tftp', action = 'store_true', dest = 'USE_TFTP', help = 'Enable built-in TFTP server, by default it is enabled', default = SETTINGS['USE_TFTP'])
    tftpexclusive.add_argument('--no-tftp', action = 'store_false', dest = 'USE_TFTP', help = 'Disable built-in TFTP server, by default it is enabled', default = not SETTINGS['USE_TFTP'])

    parser.add_argument('--debug', action = 'store', dest = 'MODE_DEBUG', help = 'Comma Seperated (http,tftp,dhcp). Adds verbosity to the selected services while they run. Use \'all\' for enabling debug on all services. Precede an option with \'-\' to disable debugging for that service; as an example, one can pass in the following to enable debugging for all services except the DHCP service: \'--debug all,-dhcp\'', default = SETTINGS['MODE_DEBUG'])
    parser.add_argument('--verbose', action = 'store', dest = 'MODE_VERBOSE', help = 'Comma Seperated (http,tftp,dhcp). Adds verbosity to the selected services while they run. Less verbose than \'debug\'. Use \'all\' for enabling verbosity on all services. Precede an option with \'-\' to disable debugging for that service; as an example, one can pass in the following to enable debugging for all services except the DHCP service: \'--debug all,-dhcp\'', default = SETTINGS['MODE_VERBOSE'])
    parser.add_argument('--config', action = 'store', dest = 'JSON_CONFIG', help = 'Configure from a JSON file rather than the command line', default = '')
    parser.add_argument('--dump-config', action = 'store_true', dest = 'DUMP_CONFIG', help = 'Dump the default configuration as a valid input file')
    parser.add_argument('--dump-config-merged', action = 'store_true', dest = 'DUMP_CONFIG_MERGED', help = 'Like --dump-config, but also merge in CLI options')
    parser.add_argument('--static-config', action = 'store', dest = 'STATIC_CONFIG', help = 'Configure leases from a json file rather than the command line', default = SETTINGS['STATIC_CONFIG'])
    parser.add_argument('--save-leases', action = 'store', dest = 'LEASES_FILE', help = 'Save all DHCP leases on exit or SIGHUP. Will load from this file on start', default = SETTINGS['LEASES_FILE'])
    parser.add_argument('--syslog', action = 'store', dest = 'SYSLOG_SERVER', help = 'Syslog server', default = SETTINGS['SYSLOG_SERVER'])
    parser.add_argument('--syslog-port', action = 'store', dest = 'SYSLOG_PORT', help = 'Syslog server port', default = SETTINGS['SYSLOG_PORT'])

    # DHCP server arguments
    dhcp_group = parser.add_argument_group(title = 'DHCP', description = 'Arguments relevant to the DHCP server')
    exclusive = dhcp_group.add_mutually_exclusive_group(required = False)
    exclusive.add_argument('--dhcp', action = 'store_true', dest = 'USE_DHCP', help = 'Enable built-in DHCP server', default = SETTINGS['USE_DHCP'])
    exclusive.add_argument('--dhcp-proxy', action = 'store_true', dest = 'DHCP_MODE_PROXY', help = 'Enable built-in DHCP server in proxy mode (implies --dhcp)', default = SETTINGS['DHCP_MODE_PROXY'])

    dhcp_group.add_argument('--dhcp-server-ip', action = 'store', dest = 'DHCP_SERVER_IP', help = 'DHCP Server IP', default = SETTINGS['DHCP_SERVER_IP'])
    dhcp_group.add_argument('--dhcp-server-port', action = 'store', dest = 'DHCP_SERVER_PORT', help = 'DHCP Server Port', default = SETTINGS['DHCP_SERVER_PORT'])
    dhcp_group.add_argument('--dhcp-begin', action = 'store', dest = 'DHCP_OFFER_BEGIN', help = 'DHCP lease range start', default = SETTINGS['DHCP_OFFER_BEGIN'])
    dhcp_group.add_argument('--dhcp-end', action = 'store', dest = 'DHCP_OFFER_END', help = 'DHCP lease range end', default = SETTINGS['DHCP_OFFER_END'])
    dhcp_group.add_argument('--dhcp-subnet', action = 'store', dest = 'DHCP_SUBNET', help = 'DHCP lease subnet', default = SETTINGS['DHCP_SUBNET'])
    dhcp_group.add_argument('--dhcp-router', action = 'store', dest = 'DHCP_ROUTER', help = 'DHCP lease router', default = SETTINGS['DHCP_ROUTER'])
    dhcp_group.add_argument('--dhcp-dns', action = 'store', dest = 'DHCP_DNS', help = 'DHCP lease DNS server', default = SETTINGS['DHCP_DNS'])
    dhcp_group.add_argument('--dhcp-broadcast', action = 'store', dest = 'DHCP_BROADCAST', help = 'DHCP broadcast address', default = SETTINGS['DHCP_BROADCAST'])
    dhcp_group.add_argument('--dhcp-fileserver', action = 'store', dest = 'DHCP_FILESERVER', help = 'DHCP fileserver IP', default = SETTINGS['DHCP_FILESERVER'])
    dhcp_group.add_argument('--dhcp-whitelist', action = 'store_true', dest = 'DHCP_WHITELIST', help = 'Only respond to DHCP clients present in --static-config', default = SETTINGS['DHCP_WHITELIST'])

    # HTTP server arguments
    http_group = parser.add_argument_group(title = 'HTTP', description = 'Arguments relevant to the HTTP server')
    http_group.add_argument('--http-port', action = 'store', dest = 'HTTP_PORT', help = 'HTTP Server Port', default = SETTINGS['HTTP_PORT'])
    http_group.add_argument('--http-server-ip', action = 'store', dest = 'HTTP_SERVER_IP', help = 'HTTP Server IP', default = SETTINGS['HTTP_SERVER_IP'])

    # network boot directory and file name arguments
    parser.add_argument('--netboot-dir', action = 'store', dest = 'NETBOOT_DIR', help = 'Local file serve directory', default = SETTINGS['NETBOOT_DIR'])
    parser.add_argument('--netboot-file', action = 'store', dest = 'NETBOOT_FILE', help = 'PXE boot file name (after iPXE if --ipxe)', default = SETTINGS['NETBOOT_FILE'])

    # NBD server arguments
    nbd_group = parser.add_argument_group(title = 'Network Block Device', description = 'Arguments relevant to the NBD server')
    nbd_group.add_argument('--nbd', action = 'store', dest = 'NBD_BLOCK_DEVICE', help = 'Enable the NDB server with a specific block device (Can be a disk image)', default = SETTINGS['NBD_BLOCK_DEVICE'])
    nbd_group.add_argument('--nbd-write', action = 'store_true', dest = 'NBD_WRITE', help = 'Enable writes on the NBD device', default = SETTINGS['NBD_WRITE'])
    nbd_group.add_argument('--nbd-cow', action = 'store_true', dest = 'NBD_COW', help = 'Enable copy-on-write for the NBD device (Non-persistent changes)', default = SETTINGS['NBD_COW'])
    nbd_group.add_argument('--nbd-cow-in-mem', action = 'store_true', dest = 'NBD_COW_IN_MEM', help = 'Store copy-on-write pages in memory', default = SETTINGS['NBD_COW_IN_MEM'])
    nbd_group.add_argument('--nbd-copy-to-ram', action = 'store_true', dest = 'NBD_COPY_TO_RAM', help = 'Copy the NBD device to memory before serving clients', default = SETTINGS['NBD_COPY_TO_RAM'])
    nbd_group.add_argument('--nbd-server', action = 'store', dest = 'NBD_SERVER_IP', help = 'NBD Server IP', default = SETTINGS['NBD_SERVER_IP'])
    nbd_group.add_argument('--nbd-port', action = 'store', dest = 'NBD_PORT', help = 'NBD Server Port', default = SETTINGS['NBD_PORT'])

    # TFTP server arguments
    tftp_group = parser.add_argument_group(title = 'TFTP', description = 'Arguments relevant to the TFTP server')
    tftp_group.add_argument('--tftp-server-ip', action = 'store', dest = 'TFTP_SERVER_IP', help = 'TFTP Server IP', default = SETTINGS['TFTP_SERVER_IP'])

    return parser.parse_args()

def do_debug(service):
    return ((service in args.MODE_DEBUG.lower()
            or 'all' in args.MODE_DEBUG.lower())
            and '-{0}'.format(service) not in args.MODE_DEBUG.lower())

def do_verbose(service):
    return ((service in args.MODE_VERBOSE.lower()
            or 'all' in args.MODE_VERBOSE.lower())
            and '-{0}'.format(service) not in args.MODE_VERBOSE.lower())

def main():
    global SETTINGS, args
    try:
        # configure
        args = parse_cli_arguments()

        if args.DUMP_CONFIG or args.DUMP_CONFIG_MERGED:
            if args.DUMP_CONFIG:
                settings = SETTINGS
            else:
                # some arguments don't make sense to print
                settings = args.__dict__
                del settings['DUMP_CONFIG']
                del settings['DUMP_CONFIG_MERGED']
                del settings['JSON_CONFIG']
            print(json.dumps(settings, sort_keys=True, indent=4))
            sys.exit()

        if args.JSON_CONFIG: # load from configuration file if specified
            try:
                config_file = io.open(args.JSON_CONFIG, 'r')
            except IOError:
                sys.exit('Failed to open {0}'.format(args.JSON_CONFIG))
            try:
                loaded_config = json.load(config_file)
                config_file.close()
            except ValueError:
                sys.exit('{0} does not contain valid JSON'.format(args.JSON_CONFIG))
            for setting in loaded_config:
                if type(loaded_config[setting]) is bytes:
                    loaded_config[setting] = loaded_config[setting].encode('ascii')
            SETTINGS.update(loaded_config) # update settings with JSON config
            args = parse_cli_arguments() # re-parse, CLI options take precedence

        # warn the user that they are starting PyPXE as non-root user
        if os.getuid() != 0:
            print(sys.stderr, '\nWARNING: Not root. Servers will probably fail to bind.\n')


        # ideally this would be in dhcp itself, but the chroot below *probably*
        # breaks the ability to open the config file.
        if args.STATIC_CONFIG:
            try:
                static_config = io.open(args.STATIC_CONFIG, 'r')
            except IOError:
                sys.exit("Failed to open {0}".format(args.STATIC_CONFIG))
            try:
                loaded_statics = json.load(static_config)
                static_config.close()
            except ValueError:
                sys.exit("{0} does not contain valid json".format(args.STATIC_CONFIG))
        else:
            loaded_statics = dict()

        # setup main logger
        sys_logger = logging.getLogger('PyPXE')
        if args.SYSLOG_SERVER:
            handler = logging.handlers.SysLogHandler(address = (args.SYSLOG_SERVER, int(args.SYSLOG_PORT)))
        else:
            handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s %(message)s')
        handler.setFormatter(formatter)
        sys_logger.addHandler(handler)
        sys_logger.setLevel(logging.INFO)

        # pass warning to user regarding starting HTTP server without iPXE
        if args.USE_HTTP and not args.USE_IPXE and not args.USE_DHCP:
            sys_logger.warning('HTTP selected but iPXE disabled. PXE ROM must support HTTP requests.')

        # if the argument was passed to enabled ProxyDHCP then enable the DHCP server
        if args.DHCP_MODE_PROXY:
            args.USE_DHCP = True

        # if the network boot file name was not specified in the argument,
        # set it based on what services were enabled/disabled
        if args.NETBOOT_FILE == '':
            if not args.USE_IPXE:
                args.NETBOOT_FILE = 'pxelinux.0'
            elif not args.USE_HTTP:
                args.NETBOOT_FILE = 'boot.ipxe'
            else:
                args.NETBOOT_FILE = 'boot.http.ipxe'

        if args.NBD_WRITE and not args.NBD_COW:
            sys_logger.warning('NBD Write enabled but copy-on-write is not. Multiple clients may cause corruption')

        if args.NBD_COW_IN_MEM or args.NBD_COPY_TO_RAM:
            sys_logger.warning('NBD cowinmem and copytoram can cause high RAM usage')

        if args.NBD_COW and not args.NBD_WRITE:
            # cow implies write
            args.NBD_WRITE = True

        # make a list of running threads for each service
        running_services = []

        # configure/start TFTP server
        if args.USE_TFTP:

            # setup TFTP logger
            tftp_logger = helpers.get_child_logger(sys_logger, 'TFTP')
            sys_logger.info('Starting TFTP server...')

            # setup the thread
            tftp_server = tftp.TFTPD(
                mode_debug = do_debug('tftp'),
                mode_verbose = do_verbose('tftp'),
                logger = tftp_logger,
                netboot_directory = args.NETBOOT_DIR,
                ip = args.TFTP_SERVER_IP)
            tftpd = threading.Thread(target = tftp_server.listen)
            tftpd.daemon = True
            tftpd.start()
            running_services.append(tftpd)

        # configure/start DHCP server
        if args.USE_DHCP:

            # setup DHCP logger
            dhcp_logger = helpers.get_child_logger(sys_logger, 'DHCP')
            if args.DHCP_MODE_PROXY:
                sys_logger.info('Starting DHCP server in ProxyDHCP mode...')
            else:
                sys_logger.info('Starting DHCP server...')

            # setup the thread
            dhcp_server = dhcp.DHCPD(
                ip = args.DHCP_SERVER_IP,
                port = args.DHCP_SERVER_PORT,
                offer_from = args.DHCP_OFFER_BEGIN,
                offer_to = args.DHCP_OFFER_END,
                subnet_mask = args.DHCP_SUBNET,
                router = args.DHCP_ROUTER,
                dns_server = args.DHCP_DNS,
                broadcast = args.DHCP_BROADCAST,
                file_server = args.DHCP_FILESERVER,
                file_name = args.NETBOOT_FILE,
                use_ipxe = args.USE_IPXE,
                use_http = args.USE_HTTP,
                mode_proxy = args.DHCP_MODE_PROXY,
                mode_debug = do_debug('dhcp'),
                mode_verbose = do_verbose('dhcp'),
                whitelist = args.DHCP_WHITELIST,
                static_config = loaded_statics,
                logger = dhcp_logger,
                saveleases = args.LEASES_FILE)
            dhcpd = threading.Thread(target = dhcp_server.listen)
            dhcpd.daemon = True
            dhcpd.start()
            running_services.append(dhcpd)

        # configure/start HTTP server
        if args.USE_HTTP:

            # setup HTTP logger
            http_logger = helpers.get_child_logger(sys_logger, 'HTTP')
            sys_logger.info('Starting HTTP server...')

            # setup the thread
            http_server = http.HTTPD(
                    mode_debug = do_debug('http'),
                    mode_verbose = do_verbose('http'),
                    logger = http_logger,
                    port = args.HTTP_PORT,
                    netboot_directory = args.NETBOOT_DIR,
                    ip = args.HTTP_SERVER_IP)
            httpd = threading.Thread(target = http_server.listen)
            httpd.daemon = True
            httpd.start()
            running_services.append(httpd)

        # configure/start NBD server
        if args.NBD_BLOCK_DEVICE:
            # setup NBD logger
            nbd_logger = helpers.get_child_logger(sys_logger, 'NBD')
            sys_logger.info('Starting NBD server...')
            nbd_server = nbd.NBD(
                block_device = args.NBD_BLOCK_DEVICE,
                write = args.NBD_WRITE,
                cow = args.NBD_COW,
                in_mem = args.NBD_COW_IN_MEM,
                copy_to_ram = args.NBD_COPY_TO_RAM,
                ip = args.NBD_SERVER_IP,
                port = args.NBD_PORT,
                mode_debug = do_debug('nbd'),
                mode_verbose = do_verbose('nbd'),
                logger = nbd_logger,
                netboot_directory = args.NETBOOT_DIR)
            nbdd = threading.Thread(target = nbd_server.listen)
            nbdd.daemon = True
            nbdd.start()
            running_services.append(nbdd)

        sys_logger.info('PyPXE successfully initialized and running!')

        while all(map(lambda x: x.is_alive(), running_services)):
            sleep(1)

    except KeyboardInterrupt:
        sys.exit('\nShutting down PyPXE...\n')

if __name__ == '__main__':
    main()
