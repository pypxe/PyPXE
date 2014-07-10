#About
This repository contains code that provides a working PXE server (via HTTP, TFTP, DHCP, and/or iPXE) implemented purely in Python. Currently, only Python2 is supported.

**WARNING:** None of these servers are fully compliant with any standards or specifications. However, the true specifications and standards were followed when building PyPXE and while they work for PXE any other uses are purely coincidental. Use at your own risk.

##Usage

PyPXE supports iPXE chainloading and, therefore, iPXE scripts.

Each server type (TFTP/HTTP/DHCP) is in it's own class in it's own file and can be used independently if so desired. See ```server.py``` for example usage where all three are used in combination with the option of enabling/disabling them individually while also setting some options.

Edit the ```server.py``` settings to your preferred network settings or run with ```--help``` 

```
# python2 server.py --help
usage: server.py [-h] [--dhcp | --proxydhcp | --no-dhcp] [--ipxe | --no-ipxe]
                 [--http | --no-http] [-s DHCP_SERVER_IP]
                 [-f DHCP_FILESERVER_IP] [-b DHCP_OFFER_BEGIN]
                 [-e DHCP_OFFER_END] [-n DHCP_SUBNET] [-r DHCP_ROUTER]
                 [-d DHCP_DNS] [-a NETBOOT] [-i DHCP_FILENAME]

Set options at runtime. Defaults are in server.py

optional arguments:
  -h, --help            show this help message and exit
  --dhcp                Use builtin DHCP server (use with --proxydhcp for
                        proxy mode) (default: True)
  --proxydhcp           Use builtin DHCP server in proxy mode (implies --dhcp)
                        (default: False)
  --no-dhcp             Disable builtin DHCP server (default: False)
  --ipxe                Chainload iPXE rom (default: True)
  --no-ipxe             Don't chainload iPXE rom (default: False)
  --http                Use builtin HTTP server (default: True)
  --no-http             Don't use builtin HTTP server (default: False)
  -s DHCP_SERVER_IP, --server DHCP_SERVER_IP
                        DHCP Server IP (default: 192.168.2.2)
  -f DHCP_FILESERVER_IP, --fileserver DHCP_FILESERVER_IP
                        Fileserver IP (default: 192.168.2.2)
  -b DHCP_OFFER_BEGIN, --begin DHCP_OFFER_BEGIN
                        DHCP lease range start (default: 192.168.2.100)
  -e DHCP_OFFER_END, --end DHCP_OFFER_END
                        DHCP lease range end (default: 192.168.2.150)
  -n DHCP_SUBNET, --subnet DHCP_SUBNET
                        DHCP lease subnet (default: 255.255.255.0)
  -r DHCP_ROUTER, --router DHCP_ROUTER
                        DHCP lease router (default: 192.168.2.1)
  -d DHCP_DNS, --dns DHCP_DNS
                        DHCP lease DNS server (default: 8.8.8.8)
  -a NETBOOT, --netboot NETBOOT
                        File serve directory (default: netboot)
  -i DHCP_FILENAME, --filename DHCP_FILENAME
                        PXE filename (after iPXE if --ipxe (default:
                        /boot.http.ipxe)
```

##Additional Notes
```Core.iso``` is from the [TinyCore Project](http://distro.ibiblio.org/tinycorelinux/) and is provided as an example to network boot from using PyPXE
```chainload.kpxe``` is the ```undionly.kpxe``` from the [iPXE Project](http://ipxe.org/)  
```pxelinux.0```, ```menu.c32``` and ```memdisk``` are from the [SYSLINUX Project](http://www.syslinux.org/)  
