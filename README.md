#About
This repository contains code that provides a working PXE server (via HTTP, TFTP, DHCP, and/or iPXE) implemented purely in Python. Currently, only Python2 is supported.

**WARNING:** None of these servers are fully compliant with any standards or specifications. However, the true specifications and standards were followed when building PyPXE and while they work for PXE any other uses are purely coincidental. Use at your own risk.

##Usage

PyPXE supports iPXE chainloading and, therefore, iPXE scripts.

Each server type (TFTP/HTTP/DHCP) is in it's own class in it's own file and can be used independently if so desired. See ```server.py``` for example usage where all three are used in combination with the option of enabling/disabling them individually while also setting some options.

Edit the ```server.py``` settings to your preferred network settings or run with ```--help``` 

```
# python2 server.py --help
usage: server.py [-h] [--no-ipxe] [--no-http] [--no-dhcp | --no-dhcp-proxy]
                 [-s DHCP_SERVER_IP] [-f DHCP_FILESERVER_IP]
                 [-b DHCP_OFFER_BEGIN] [-e DHCP_OFFER_END] [-n DHCP_SUBNET]
                 [-r DHCP_ROUTER] [-d DHCP_DNS] [-a NETBOOT_DIR]
                 [-i NETBOOT_FILE]

Set options at runtime. Defaults are in server.py

optional arguments:
  -h, --help            show this help message and exit
  --no-ipxe             Toggle iPXE ROM (default: True)
  --no-http             Toggle built-in HTTP server (default: True)
  --no-dhcp             Toggle built-in DHCP server (default: True)
  --no-dhcp-proxy       Toggle built-in DHCP server proxy mode (default: True)
  -s DHCP_SERVER_IP, --dhcp-server-ip DHCP_SERVER_IP
                        DHCP Server IP (default: 192.168.2.2)
  -f DHCP_FILESERVER_IP, --dhcp-fileserver-ip DHCP_FILESERVER_IP
                        DHCP fileserver IP (default: 192.168.2.2)
  -b DHCP_OFFER_BEGIN, --dhcp-begin DHCP_OFFER_BEGIN
                        DHCP lease range start (default: 192.168.2.100)
  -e DHCP_OFFER_END, --dhcp-end DHCP_OFFER_END
                        DHCP lease range end (default: 192.168.2.150)
  -n DHCP_SUBNET, --dhcp-subnet DHCP_SUBNET
                        DHCP lease subnet (default: 255.255.255.0)
  -r DHCP_ROUTER, --dhcp-router DHCP_ROUTER
                        DHCP lease router (default: 192.168.2.1)
  -d DHCP_DNS, --dhcp-dns DHCP_DNS
                        DHCP lease DNS server (default: 8.8.8.8)
  -a NETBOOT_DIR, --netboot-dir NETBOOT_DIR
                        Local file serve directory (default: netboot)
  -i NETBOOT_FILE, --netboot-file NETBOOT_FILE
                        PXE boot file name (after iPXE if --ipxe) (default: )
```

##Additional Notes
```Core.iso``` is from the [TinyCore Project](http://distro.ibiblio.org/tinycorelinux/) and is provided as an example to network boot from using PyPXE
```chainload.kpxe``` is the ```undionly.kpxe``` from the [iPXE Project](http://ipxe.org/)  
```pxelinux.0```, ```menu.c32``` and ```memdisk``` are from the [SYSLINUX Project](http://www.syslinux.org/)  
