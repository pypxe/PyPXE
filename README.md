#About
This repository contains code that provides a working PXE server (via HTTP, TFTP, DHCP, and/or iPXE) implemented purely in Python. Currently, only Python2 is supported.

**WARNING:** None of these servers are fully compliant with any standards or specifications. However, the true specifications and standards were followed when building PyPXE and while they work for PXE any other uses are purely coincidental. Use at your own risk.

##Usage

Each server type (TFTP/HTTP/DHCP) is in it's own class in it's own file and can be used independently if so desired.

```server.py``` uses all three services in combination with the option of enabling/disabling them individually while also setting some options. Edit the ```server.py``` settings to your preferred network settings or run with ```--help``` or ```-h```. Below is a list of the arguments that ```server.py``` takes, all of which are optional.

Simply run ```sudo python server.py``` and you will have an out-of-the-box PXE-bootable server! If you require the ability to handle PXE requests then you can either enable the built-in DHCP server ```sudo python server.py --dhcp``` (after configuring, of course) or start ```server.py``` in ProxyDHCP rather than full DHCP ```sudo python server.py --dhcp-proxy```

Argument | Explanation
--- | ---
```--ipxe``` | Enable iPXE ROM (default: False)
```--http``` | Enable built-in HTTP server (default: False) 
```--dhcp``` | Enable built-in DHCP server (default: False)
```--dhcp-proxy``` | Enable built-in DHCP server in proxy mode (implies ```--dhcp```) (default: False)
```-s DHCP_SERVER_IP``` or ```--dhcp-server-ip DHCP_SERVER_IP``` | DHCP Server IP (default: 192.168.2.2) 
```-f DHCP_FILESERVER_IP```or ```--dhcp-fileserver-ip DHCP_FILESERVER_IP``` | DHCP fileserver IP (default: 192.168.2.2)
```-b DHCP_OFFER_BEGIN```or ```--dhcp-begin DHCP_OFFER_BEGIN``` | DHCP lease range start (default: 192.168.2.100)
```-e DHCP_OFFER_END``` or ```--dhcp-end DHCP_OFFER_END``` | DHCP lease range end (default: 192.168.2.150)
```-n DHCP_SUBNET``` or ```--dhcp-subnet DHCP_SUBNET``` | DHCP lease subnet (default: 255.255.255.0)
```-r DHCP_ROUTER``` or ```--dhcp-router DHCP_ROUTER``` | DHCP lease router (default: 192.168.2.1)
```-d DHCP_DNS``` or ```--dhcp-dns DHCP_DNS``` | DHCP lease DNS server (default: 8.8.8.8)
```-a NETBOOT_DIR``` or ```--netboot-dir NETBOOT_DIR``` | Local file serve directory (default: netboot)
```-i NETBOOT_FILE``` or ```--netboot-file NETBOOT_FILE``` | PXE boot file name (after iPXE if not ```--no-ipxe```) (default is for it to automatically be set based on what services are enabled/disabled)

##Additional Notes
```Core.iso``` is from the [TinyCore Project](http://distro.ibiblio.org/tinycorelinux/) and is provided as an example to network boot from using PyPXE
```chainload.kpxe``` is the ```undionly.kpxe``` from the [iPXE Project](http://ipxe.org/)  
```pxelinux.0```, ```menu.c32``` and ```memdisk``` are from the [SYSLINUX Project](http://www.syslinux.org/)  

###ToDo
- Add ```--debug``` prints to dhcp/tftp/http (such as 404, Offer/ACKs w/ filename)
- [PEP8](http://legacy.python.org/dev/peps/pep-0008/)
- Turn longer functions to kwargs vs positional
- Remove hardcoded /24 in dhcpd