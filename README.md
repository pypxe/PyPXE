#About
This repository contains code that provides a working PXE server (via HTTP, TFTP, DHCP, and/or iPXE) implemented purely in Python. Currently, only Python 2.6 and newer is supported. Please read `Documentation.md` for further explanation of the PyPXE project as well as recommended use. See the [issues page](https://github.com/psychomario/PyPXE/issues) for open issues, bugs, and enhancements/improvements.

**DISCLAIMER:** None of thes implemented services are fully compliant with any standards or specifications. However, the true specifications and standards were followed when building PyPXE and while they work for PXE any other uses are purely coincidental. Use at your own risk.

##Usage

###Using PyPXE as a Library
PyPXE implements the following services for the purpose of creating a Python-based PXE environment: TFTP, HTTP, and DHCP. Each PyPXE service must be imported individually. For example, to import the TFTP service simply use:
```python
from pypxe import tftp
```
or, if you prefer, you can use:
```python
import pypxe.tftp
```
For more information on how each service works and how to manipulate them, see  `DOCUMENTATION.md`.

###QuickStart
`pypxe-server.py` uses all three services in combination with the option of enabling/disabling them individually while also setting some options. Edit the `pypxe-server.py` settings to your preferred settings or run with `--help` or `-h` to see what command line arguments you can pass. Treat the provided `netboot` directory as `tftpboot` that you would typically see on a TFTP server, put all of your network-bootable files in there and setup your menu(s) in `netboot/pxelinux.cfg/default`.

**Note:** Python 2.6 does not include the `argparse` module, it is included in the standard library as of 2.7 and newer. The `argparse` module is required to take in command line arguments and `pypxe-server.py` will not run without it.

Simply run the following command and you will have an out-of-the-box PXE-bootable server that runs TFTP and serves files out of the `netboot` directory!
```bash
$ sudo python pypxe-server.py
```
If you require the ability to handle DHCP PXE requests then you can either enable the built-in DHCP server (after configuring, of course)...
```bash
$ sudo python pypxe-server.py --dhcp
```
...or start `pypxe-server.py` in ProxyDHCP mode rather than a full DHCP server to prevent DHCP conflicts on your network...
```bash
$ sudo python pypxe-server.py --dhcp-proxy
```

**PyPXE Server Arguments**

The following are arguments that can be passed to `pypxe-server.py` when running from the command line

* __Main Arguments__
  * __`--ipxe`__
    * Description: Enable iPXE ROM
    * Default: False
  * __`--http`__
    * Description: Enable built-in HTTP server
    * Default: False
  * __`--dhcp`__
    * Description: Enable built-in DHCP server
    * Default: False
  * __`--dhcp-proxy`__
    * Description: Enable built-in DHCP server in proxy mode (implies `--dhcp`)
    * Default: False
  * __`--no-tftp`__
    * Description: Disable built-in TFTP server which is enabled by default
    * Default: False
  * __`--debug`__
    * Description: Enable selected services in DEBUG mode
    * Default: False
    * _Note: This adds a level of verbosity so that you can see what's happening in the background. Debug statements are prefixed with `[DEBUG]` and indented to distinguish between normal output that the services give._
* __DHCP Service Arguments__ _each of the following can be set one of two ways, you can use either/or_
  * __`-s DHCP_SERVER_IP` or `--dhcp-server-ip DHCP_SERVER_IP`__
    * Description: Specify DHCP server IP address
    * Default: 192.168.2.2
  * __`-p DHCP_SERVER_PORT` or `--dhcp-server-port DHCP_SERVER_PORT`__
    * Description: Specify DHCP server port
    * Default: 67
  * __`-b DHCP_OFFER_BEGIN` or `--dhcp-begin DHCP_OFFER_BEGIN`__
    * Description: Specify DHCP lease range start
    * Default: 192.168.2.100
  * __`-e DHCP_OFFER_END` or `--dhcp-end DHCP_OFFER_END`__
    * Description: Specify DHCP lease range end
    * Default: 192.168.2.150
  * __`-n DHCP_SUBNET` or `--dhcp-subnet DHCP_SUBNET`__
    * Description: Specify DHCP subnet
    * Default: 255.255.255.0
  * __`-r DHCP_ROUTER` or `--dhcp-router DHCP_ROUTER`__
    * Description: Specify DHCP lease router
    * Default: 192.168.2.1
  * __`-d DHCP_DNS` or `--dhcp-dns DHCP_DNS`__
    * Description: Specify DHCP lease DNS server 
    * Default: 8.8.8.8
  * __`-c DHCP_BROADCAST` or `--dhcp-broadcast DHCP_BROADCAST`__
    * Description: Specify DHCP broadcast address
    * Default: '<broadcast>'
  * __`-f DHCP_FILESERVER_IP` or `--dhcp-fileserver-ip DHCP_FILESERVER_IP`__
    * Description: Specify DHCP file server IP address
    * Default: 192.168.2.2
* __File Name/Directory Arguments__
  * __`-a NETBOOT_DIR` or `--netboot-dir NETBOOT_DIR`__
    * Description: Specify the local directory where network boot files will be served 
    * Default: 'netboot'
  * __`-i NETBOOT_FILE` or `--netboot-file NETBOOT_FILE`__
    * Description: Specify the PXE boot file name
    * Default: automatically set based on what services are enabled or disabled, see documentation for further explanation

##Notes
* `Core.iso` located in `netboot` is from the [TinyCore Project](http://distro.ibiblio.org/tinycorelinux/) and is provided as an example to network boot from using PyPXE
* `chainload.kpxe` located in `netboot` is the `undionly.kpxe` from the [iPXE Project](http://ipxe.org/)  
* `ldlinux.c32`, `libutil.c32`, `pxelinux.0`, `menu.c32`, and `memdisk` located in `netboot` are from the [SYSLINUX Project](http://www.syslinux.org/) version [6.02](http://www.syslinux.org/wiki/index.php/Syslinux_6_Changelog#Changes_in_6.02)
