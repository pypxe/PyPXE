# About
This repository contains code that provides a working PXE server (via HTTP, TFTP, DHCP, and/or iPXE) implemented purely in Python. Please read [`DOCUMENTATION.md`](DOCUMENTATION.md) for further explanation of the PyPXE project as well as recommended use. See the [issues page](https://github.com/pypxe/PyPXE/issues) for open issues, bugs, and enhancements/improvements.

**DISCLAIMER:** None of the implemented services are fully compliant with any standards or specifications. However, the true specifications and standards were followed when building PyPXE and while they work for PXE any other uses are purely coincidental. Use at your own risk.

## Usage

### Using PyPXE as a Library
PyPXE implements the following services for the purpose of creating a Python-based PXE environment: TFTP, HTTP, and DHCP. Each PyPXE service must be imported individually. For example, to import the TFTP service simply use:
```python
from pypxe import tftp
```
or, if you prefer, you can use:
```python
import pypxe.tftp
```
For more information on how each service works and how to manipulate them, see  [`DOCUMENTATION.md`](DOCUMENTATION.md).

### QuickStart
`pypxe.server` uses all three services in combination with the option of enabling/disabling them individually while also setting some options. Run `pypxe.server` with `--help` or `-h` to see what command line arguments you can pass. Treat the provided `netboot` directory as `tftpboot` that you would typically see on a TFTP server, put all of your network-bootable files in there and setup your menu(s) in `netboot/pxelinux.cfg/default`.

Simply run the following command and you will have an out-of-the-box PXE-bootable server that runs TFTP and serves files out of the `netboot` directory!
```bash
$ sudo python -m pypxe.server
```
If you require the ability to handle DHCP PXE requests then you can either enable the built-in DHCP server (after configuring, of course)...
```bash
$ sudo python -m pypxe.server --dhcp
```
...or start `pypxe.server` in ProxyDHCP mode rather than a full DHCP server to prevent DHCP conflicts on your network...
```bash
$ sudo python -m pypxe.server --dhcp-proxy
```

#### PyPXE Server Arguments

The following are arguments that can be passed to `pypxe.server` when running from the command line:

##### Main Arguments

|Argument|Description|Default|
|---|---|---|
|__`--ipxe`__|Enable iPXE ROM|`False`|
|__`--no-ipxe`__|Disable iPXE ROM|`True`|
|__`--http`__|Enable built-in HTTP server|`False`|
|__`--no-http`__|Disable built-in HTTP server|`True`|
|__`--dhcp`__|Enable built-in DHCP server|`False`|
|__`--dhcp-proxy`__|Enable built-in DHCP server in proxy mode (implies `--dhcp`)|`False`|
|__`--tftp`__|Enable built-in TFTP server which is enabled by default|`True`|
|__`--no-tftp`__|Disable built-in TFTP server which is enabled by default|`False`|
|__`--debug`__|Enable selected services in DEBUG mode; services are selected by passing the name in a comma separated list. **Options are: http, tftp and dhcp**; one can also prefix an option with `-` to prevent debugging of that service; for example, the following will enable debugging for all services _except_ the DHCP service `--debug all,-dhcp`. _This mode adds a level of verbosity so that you can see what's happening in the background._|`''`|
|__`--verbose`__|Enable selected services in verbose mode; services are selected by passing the name in a comma separated list. Follows the same syntax for selecting service as `--debug`._|`''`|
|__`--config`__|Load configuration from JSON file. (see [`example_cfg.json`](example_cfg.json))|`None`|
|__`--static-config`__|Load DHCP lease configuration from JSON file. (see [`example_leases.json`](example_leases.json))|`None`|
|__`--save-leases`__|Saves allocated leases on `HUP`, `INT`(`^C`), `ALRM` and `TERM`. Loads on start if the file exists already|`None`|
|__`--syslog`__|Specify a syslog server|`None`|
|__`--syslog-port`__|Specify a syslog server port|`514`|


##### DHCP Service Arguments

|Argument|Description|Default|
|---|---|---|
|__`--dhcp-server-ip DHCP_SERVER_IP`__|Specify DHCP server IP address|`192.168.2.2`|
|__`--dhcp-server-port DHCP_SERVER_PORT`__|Specify DHCP server port|`67`|
|__`--dhcp-begin DHCP_OFFER_BEGIN`__|Specify DHCP lease range start|`192.168.2.100`|
|__`--dhcp-end DHCP_OFFER_END`__|Specify DHCP lease range end|`192.168.2.150`|
|__`--dhcp-subnet DHCP_SUBNET`__|Specify DHCP subnet mask|`255.255.255.0`|
|__`--dhcp-router DHCP_ROUTER`__|Specify DHCP lease router|`192.168.2.1`|
|__`--dhcp-dns DHCP_DNS`__|Specify DHCP lease DNS server|`8.8.8.8`|
|__`--dhcp-broadcast DHCP_BROADCAST`__|Specify DHCP broadcast address|`''`|
|__`--dhcp-fileserver DHCP_FILESERVER`__|Specify DHCP file server IP address|`192.168.2.2`|
|__`--dhcp-whitelist`__|Only serve clients specified in the static lease file (`--static-config`)|`False`|

##### TFTP Service Arguments

|Argument|Description|Default|
|---|---|---|
|__`--tftp-server-ip TFTP_SERVER_IP`__|Specify TFTP server IP address|`0.0.0.0`|

##### HTTP Service Arguments

|Argument|Description|Default|
|---|---|---|
|__`--http-server-ip HTTP_SERVER_IP`__|Specify HTTP server IP address|`0.0.0.0`|
|__`--http-port HTTP_PORT`__|Specify HTTP server Port|80|

##### File Name/Directory Arguments

|Argument|Description|Default|
|---|---|---|
|__`--netboot-dir NETBOOT_DIR`__|Specify the local directory where network boot files will be served|`'netboot'`|
|__`--netboot-file NETBOOT_FILE`__|Specify the PXE boot file name|_automatically set based on what services are enabled or disabled, see [`DOCUMENTATION.md`](DOCUMENTATION.md) for further explanation_|


##### Network Block Device Arguments
|Argument|Description|Default|
|---|---|---|
|__`--nbd NBD_BLOCK_DEVICE`__|Specify the block device to be served by NBD and enable NBD. This can be a disk image.|`''`|
|__`--nbd-write`__|Open the block device for write access. UNSAFE: Multiple clients can cause corruption|`False`|
|__`--nbd-cow`__|When write is enabled, create a *volatile* file per client with their changes. Clients can write but changes are not shared or kept.|`True (Only applies if write is on)`|
|__`--nbd-cow-in-mem`__|Client volatile changes are stored in RAM rather than on disk. WARNING: High RAM usage (up to sizeof(block device)*clients)|`False`|
|__`--nbd-copy-to-ram`__|Disk image is copied to RAM on start to speed up access. Changes are lost when write is used without cow.|`False`|
|__`--nbd-server`__|The NBD server IP address to bind to|`0.0.0.0`|
|__`--nbd-port`__|The NBD server port to bind to|`10809`|


## Notes
* `Core.iso` located in `netboot` is from the [TinyCore Project](http://distro.ibiblio.org/tinycorelinux/) and is provided as an example to network boot from using PyPXE
* `chainload.kpxe` located in `netboot` is the `undionly.kpxe` from the [iPXE Project](http://ipxe.org/)
* `ldlinux.c32`, `libutil.c32`, `pxelinux.0`, `menu.c32`, and `memdisk` located in `netboot` are from the [SYSLINUX Project](http://www.syslinux.org/) version [6.02](http://www.syslinux.org/wiki/index.php/Syslinux_6_Changelog#Changes_in_6.02)

