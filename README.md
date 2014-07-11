#About
This repository contains code that provides a working PXE server (via HTTP, TFTP, DHCP, and/or iPXE) implemented purely in Python. Currently, only Python2 is supported.

**DISCLAIMER:** None of these servers are fully compliant with any standards or specifications. However, the true specifications and standards were followed when building PyPXE and while they work for PXE any other uses are purely coincidental. Use at your own risk.

##Usage

###Using PyPXE as a Library
Each server type (TFTP/HTTP/DHCP) is in it's own class in it's own file and can be used independently if so desired. For more information on how each service works and how to manipulate them, see  ```DOCUMENTATION.md``` in the root of ```master```.

###QuickStart
```server.py``` uses all three services in combination with the option of enabling/disabling them individually while also setting some options. Edit the ```server.py``` settings to your preferred settings or run with ```--help``` or ```-h``` to see what command line arguments you can pass. Treat the provided 'netboot' directory as '/tftpboot/' that you would typically see on a TFTP server, put all of your network-bootable files in there and setup your menu(s) in 'pxelinux.cfg/default'.

Simply run the following command and you will have an out-of-the-box PXE-bootable server that runs TFTP and serves files out of the 'netboot' directory!
```shell
sudo python server.py
```
If you require the ability to handle DHCP PXE requests then you can either enable the built-in DHCP server (after configuring, of course)...
```shell
sudo python server.py --dhcp
```
...or start ```server.py``` in ProxyDHCP mode rather than a full DHCP server to prevent DHCP conflicts on your network...
```shell
sudo python server.py --dhcp-proxy
```

**TFTP/DHCP/HTTP/iPXE Arguments**

Enable iPXE ROM [Default: False]
```
--ipxe
```

Enable built-in HTTP server [Default: False]
```
--http
```

Enable built-in DHCP server [Default: False]
```
--dhcp
```

Enable built-in DHCP server in proxy mode (implies ```--dhcp```) [Default: False]
```
--dhcp-proxy
```

**DHCP Server Arguments**

**Argument:** ```-s``` or ```--dhcp-server-ip```
**Variable:** DHCP_SERVER_IP
**Explanation:** DHCP Server IP (default: 192.168.2.2) 

**Argument:** ```-f```or ```--dhcp-fileserver-ip```
**Variable:** DHCP_FILESERVER_IP
**Explanation:** DHCP fileserver IP (default: 192.168.2.2)

**Argument:** ```-b```or ```--dhcp-begin```
**Variable:** DHCP_OFFER_BEGIN
**Explanation:** DHCP lease range start (default: 192.168.2.100)

**Argument:** ```-e``` or ```--dhcp-end```
**Variable:** DHCP_OFFER_END
**Explanation:** DHCP lease range end (default: 192.168.2.150)

**Argument:** ```-n``` or ```--dhcp-subnet```
**Variable:** DHCP_SUBNET
**Explanation:** DHCP lease subnet (default: 255.255.255.0)

**Argument:** ```-r``` or ```--dhcp-router```
**Variable:** DHCP_ROUTER
**Explanation:** DHCP lease router (default: 192.168.2.1)

**Argument:** ```-d``` or ```--dhcp-dns```
**Variable:** DHCP_DNS
**Explanation:** DHCP lease DNS server (default: 8.8.8.8)

**Argument:** ```-a``` or ```--netboot-dir```
**Variable:** NETBOOT_DIR
**Explanation:** Local file serve directory (default: 'netboot')

**Argument:** ```-i``` or ```--netboot-file```
**Variable:** NETBOOT_FILE
**Explanation:** PXE boot file name (default is for it to automatically be set based on what services are enabled/disabled)

##Additional Notes
```Core.iso``` is from the [TinyCore Project](http://distro.ibiblio.org/tinycorelinux/) and is provided as an example to network boot from using PyPXE
```chainload.kpxe``` is the ```undionly.kpxe``` from the [iPXE Project](http://ipxe.org/)  
```pxelinux.0```, ```menu.c32``` and ```memdisk``` are from the [SYSLINUX Project](http://www.syslinux.org/)  

###ToDo
- Add ```--debug``` prints to dhcp/tftp/http (such as 404, Offer/ACKs w/ filename)
- [PEP8](http://legacy.python.org/dev/peps/pep-0008/)
- Turn longer functions to kwargs vs positional
- Remove hardcoded /24 in dhcpd