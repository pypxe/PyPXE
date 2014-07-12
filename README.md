#About
This repository contains code that provides a working PXE server (via HTTP, TFTP, DHCP, and/or iPXE) implemented purely in Python. Currently, only Python2 is supported.

**DISCLAIMER:** None of these servers are fully compliant with any standards or specifications. However, the true specifications and standards were followed when building PyPXE and while they work for PXE any other uses are purely coincidental. Use at your own risk.

##Usage

###Using PyPXE as a Library
Each server type (TFTP/HTTP/DHCP) is in it's own class in it's own file and can be used independently if so desired. For more information on how each service works and how to manipulate them, see  ```DOCUMENTATION.md```.

###QuickStart
```server.py``` uses all three services in combination with the option of enabling/disabling them individually while also setting some options. Edit the ```server.py``` settings to your preferred settings or run with ```--help``` or ```-h``` to see what command line arguments you can pass. Treat the provided ```netboot``` directory as ```/tftpboot``` that you would typically see on a TFTP server, put all of your network-bootable files in there and setup your menu(s) in ```netboot/pxelinux.cfg/default```.

Simply run the following command and you will have an out-of-the-box PXE-bootable server that runs TFTP and serves files out of the ```netboot``` directory!
```
sudo python server.py
```
If you require the ability to handle DHCP PXE requests then you can either enable the built-in DHCP server (after configuring, of course)...
```
sudo python server.py --dhcp
```
...or start ```server.py``` in ProxyDHCP mode rather than a full DHCP server to prevent DHCP conflicts on your network...
```
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

Enable built-in DHCP server in DEBUG mode [Default: False]
```
--dhcp-debug
```
This adds a level of verbosity so that you can see what's happening in the background. Debug statements are prefixed with ```[DEBUG]``` and indented to distinguish between normal output that the server gives.

Disable built-in TFTP server which is enabled by default [Default: True]
```
--no-tftp
```

**DHCP Server Arguments** _each of the following can be set one of two ways, you can use either/or_

Specify DHCP server IP address [Default: 192.168.2.2]
```
-s DHCP_SERVER_IP
```
```
--dhcp-server-ip DHCP_SERVER_IP
```

Specify DHCP fileserver IP address [Default: 192.168.2.2]
```
-f DHCP_FILESERVER_IP
```
```
--dhcp-fileserver-ip DHCP_FILESERVER_IP
```

Specify DHCP lease range start [Default: 192.168.2.100]
```
-b DHCP_OFFER_BEGIN
```
```
--dhcp-begin DHCP_OFFER_BEGIN
```

Specify DHCP lease range end [Default: 192.168.2.150]
```
-e DHCP_OFFER_END
```
```
--dhcp-end DHCP_OFFER_END
```

Specify DHCP subnet [Default: 255.255.255.0]
```
-n DHCP_SUBNET
```
```
--dhcp-subnet DHCP_SUBNET
```

Specify DHCP lease router [Default: 192.168.2.1]
```
-r DHCP_ROUTER
```
```
--dhcp-router DHCP_ROUTER
```

Specify DHCP lease DNS server [Default: 8.8.8.8]
```
-d DHCP_DNS
```
```
--dhcp-dns DHCP_DNS
```

Specify DHCP broadcast address [Default: '<broadcast>']
```
-c DHCP_BROADCAST
```
```
--dhcp-broadcast DHCP_BROADCAST
```

Specify the local directory where network boot files will be served [Default: 'netboot']
```
-a NETBOOT_DIR
```
```
--netboot-dir NETBOOT_DIR
```

Specify the PXE boot file name [Default: automatically set based on what services are enabled or disabled, see documentation for further explanation]
```
-i NETBOOT_FILE
```
```
--netboot-file NETBOOT_FILE
```

##Notes
```Core.iso``` located in ```netboot``` is from the [TinyCore Project](http://distro.ibiblio.org/tinycorelinux/) and is provided as an example to network boot from using PyPXE
```chainload.kpxe``` located in ```netboot``` is the ```undionly.kpxe``` from the [iPXE Project](http://ipxe.org/)  
```pxelinux.0```, ```menu.c32```, and ```memdisk``` located in ```netboot``` are from the [SYSLINUX Project](http://www.syslinux.org/)  
