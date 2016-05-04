# Background
>The Preboot eXecution Environment (PXE, also known as Pre-Execution Environment; sometimes pronounced "pixie") is an environment to boot computers using a network interface independently of data storage devices (like hard disks) or installed operating systems. -[Wikipedia](https://en.wikipedia.org/wiki/Preboot_Execution_Environment)

PXE allows computers to boot from a binary image stored on a server, rather than the local hardware. Broadly speaking, a DHCP server informs a client of the TFTP server and filename from which to boot.

## DHCP
In the standard DHCP mode, the server has been implemented from [RFC2131](http://www.ietf.org/rfc/rfc2131.txt), [RFC2132](http://www.ietf.org/rfc/rfc2132.txt), and the [DHCP Wikipedia Entry](https://en.wikipedia.org/wiki/Dynamic_Host_Configuration_Protocol).  

The DHCP server is in charge of assigning new clients with IP addresses, and informing them of the location of the TFTP server and filename they should look for. The top half of the DHCP request, as seen on the Wikipedia entry, consists of some network information, followed by 192 legacy null bytes, and then the magic cookie.  

After the magic cookie, there are optional fields. These fields are defined by the field ID, a length byte and then the option data. Every DHCP packet has an option 53 field. This field specifies the packet type, be it DISCOVERY, OFFER, REQUEST or ACKNOWLEDGEMENT.  

The DISCOVERY and REQUEST packets are those sent by the client to the broadcast address (IPv4: 255.255.255.255) where the client sends this data on port 68 and the server receives it on port 68. The OFFER and ACKNOWLEDGEMENT packets are sent from the server to the broadcast address where the server sends this data on port 67 and the client receives it on port 68. These four packets make up the four-way handshake.  

The OFFER and ACKNOWLEDGEMENT packets both contain the same option data for each client. This can include the router, subnet mask, lease time, and DHCP server IP address.

Also included in these options are our PXE options. The minimum required option fields are option 66 and option 67. Option 66 denotes the IP of the TFTP server, and option 67 denotes the filename of the file to retrieve and boot.  

Once the four way handshake is complete, the client will send a TFTP read request to the given fileserver IP address requesting the given filename.

By default only requests declaring the 'PXEClient' value dhcp option 60 are served, this is defined by [PXE specifications](http://www.pix.net/software/pxeboot/archive/pxespec.pdf)  If you're using PyPXE as a library you can change this behavior extending the *DHCP* class and overwriting the *validateReq* method.

### ProxyDHCP
ProxyDHCP mode is useful for when you either cannot (or do not want to) change the main DHCP server on a network. The bulk of ProxyDHCP information can be found in the [Intel PXE spec](http://www.pix.net/software/pxeboot/archive/pxespec.pdf). The main idea behind ProxyDHCP is that the main network DHCP server can hand out the IP leases while the ProxyDHCP server hands out the PXE information to each client. Therefore, slightly different information is sent in the ProxyDHCP packets.

There are multiple ways to implement ProxyDHCP: broadcast, multicast, unicast or lookback. Lookback is the simplest implementation and this is what we have chosen to use. When we receive a DHCP DISCOVER from a client, we respond with a DHCP OFFER but the OFFER packet is sent without a few fields we would normally send in standard DHCP mode (this includes an offered IP address, along with any other network information such as router, DNS server(s), etc.). What we include in this OFFER packet (which isn't in a normal DHCP packet), is a vendor-class identifier of 'PXEClient' - this string identifies the packet as being relevant to PXE booting.

There are a few vendor-specific options under the DHCP option 43:
* The first of these options is PXE discovery control; this is a bitmask defined in the PXE spec. When bit 3 is set, the PXE client will look backwards in the packet for the filename. The filename is located in the standard 'DHCP Boot Filename' area, previously referred to as 'legacy'. This is a NULL-terminated string located at offset 150 in the DHCP packet (before the DHCP magic cookie).
* The second vendor-specific option that is used is the PXE menu prompt. Although not visible, this is required by the spec and causes problems if it is missing. The main use for this is for the other DISCOVERY modes.  

The client should receive two DHCP OFFER packets in ProxyDHCP mode: the first from the main DHCP server and the second from the ProxyDHCP server. Once both are received, the client will continue on with the DHCP handshake and, after it is complete, the client will boot using the settings in the DHCP OFFER from the ProxyDHCP server.

## TFTP
We have only implemented the read OPCODE for the TFTP server, as PXE does not use write. Only *octet* transfer mode is supported. The main TFTP protocol is defined in [RFC1350](http://www.ietf.org/rfc/rfc1350.txt)

### blksize
The blksize option, as defined in [RFC2348](http://www.ietf.org/rfc/rfc2348.txt) allows the client to specify the block size for each transfer packet. The blksize option is passed along with the read opcode, following the filename and mode. The format is blksize, followed by a null byte, followed by the ASCII base-10 representation of the blksize (i.e 512 rather than 0x200), followed by another null byte.

## HTTP
We have implemented GET and HEAD, as there is no requirement for any other methods. The referenced RFCs are [RFC2616](http://www.ietf.org/rfc/rfc2616.txt) and [RFC7230](http://www.ietf.org/rfc/rfc7230.txt).  

The HEAD method is used by some PXE ROMs to find the Content-Length before the GET is sent.

## NBD
NBD is similar to NFS in that it can act as a root device for Linux systems. Defined in the [specification](https://github.com/yoe/nbd/blob/master/doc/proto.txt), NBD allows access to block devices over the network by performing read and write requests on the block device itself.

This is different to NFS as it does not act as a filesystem, merely a single file. NBD supports read/write access along with copy-on-write support, both in memory and on disk. Read/write without copy-on-write is potentially dangerous if the file-system layer does not support multiple systems accessing it at the same time. Copy-on-write alleviates these potential problems by providing a volatile layer in which per-client changes are saved. Both the on-disk and in-memory configurations delete changes after the client disconnects, but the in-memory configuration may offer a speed increase as the changes are stored in the system RAM.

WARNING: The use of this option can potentially consume a large amount of RAM; up to the size of the disk image multiplied by the number of connected clients may be used. The same can be said for the on-disk configuration, where this configuration uses disk space rather than memory space. A further configuration option to store the original disk image in memory is provided to potentially allow for read/write speed up.

# PyPXE Services
The PyPXE library provides the following services for the purpose of creating a Python-based PXE environment: TFTP, HTTP, DHCP, and NBD. Each service must be imported independently as such:

* `from pypxe import tftp` or `import pypxe.tftp` imports the TFTP service
* `from pypxe import dhcp` or `import pypxe.dhcp` imports the DHCP service
* `from pypxe import http` or `import pypxe.http` imports the HTTP service
* `from pypxe import nbd` or `import pypxe.nbd` imports the NBD service

**See [`pypxe/server.py`](pypxe.server) for example usage on how to call, define, and setup the services.** When running any Python script that uses these classes, it should be run as a user with root privileges as they bind to interfaces and without root privileges the services will most likely fail to bind properly.

## TFTP Server `pypxe.tftp`

### Importing
The TFTP service can be imported _one_ of the following two ways:
```python
from pypxe import tftp
```
```python
import pypxe.tftp
```

### Usage
The TFTP server class, __`TFTPD()`__, is constructed with the following __keyword arguments__:

|Keyword Argument|Description|Default|Type|
|---|---|---|---|
|__`ip`__|This is the IP address that the TFTP server will bind to.|`'0.0.0.0'` (so that it binds to all available interfaces)| _string_|
|__`port`__|This it the port that the TFTP server will run on.|`69` (default port for TFTP)|_int_|
|__`netboot_directory`__|This is the directory that the TFTP server will serve files from similarly to that of `tftpboot`.|`'.'` (current directory)|_string_|
|__`mode_debug`__|This indicates whether or not the TFTP server should be started in debug mode or not.|`False`|_bool_|
|__`mode_verbose`__|This indicates whether or not the TFTP server should be started in verbose mode or not.|`False`|_bool_|
|__`logger`__|A [Logger](https://docs.python.org/2/library/logging.html#logger-objects) object used for logging messages, if `None` a local [StreamHandler](https://docs.python.org/2/library/logging.handlers.html#streamhandler) instance will be created.|`None`|[_Logger_](https://docs.python.org/2/library/logging.html#logger-objects)|
|__`default_retries`__|The number of data retransmissions before dropping a connection.|`3`|_int_|
|__`timeout`__|The time in seconds before re-sending an un-acknowledged data block.|`5`|_int_|

## DHCP Server `pypxe.dhcp`

### Importing
The DHCP service can be imported _one_ of the following two ways:
```python
from pypxe import dhcp
```
```python
import pypxe.dhcp
```

### Usage
The DHCP server class, __`DHCPD()`__, is constructed with the following __keyword arguments__:

|Keyword Argument|Description|Default|Type|
|---|---|---|---|
|__`ip`__|This is the IP address that the DHCP server itself binds to.|`'192.168.2.2'`|_string_|
|__`port`__|This it the port that the TFTP server will run on.|`67` (default port to listen for DHCP requests)|_int_|
|__`offer_from`__|This specifies the beginning of the range of IP addresses that the DHCP server will hand out to clients.|`'192.168.2.100'`|_string_|
|__`offer_to`__|This specifies the end of the range of IP addresses that the DHCP server will hand out to clients.|`'192.168.2.150'`|_string_|
|__`subnet_mask`__|This specifies the subnet mask that the DHCP server will specify to clients.|`'255.255.255.0'`|_string_|
|__`router`__|This specifies the IP address of the router that the DHCP server will specify to clients.|`'192.168.2.1'`|_string_|
|__`dns_server`__|This specifies the DNS server that the DHCP server will specify to clients. Only one DNS server can be passed.|`'8.8.8.8'` ([Google Public DNS](https://developers.google.com/speed/public-dns/))|_string_|
|__`broadcast`__|This specifies the broadcast address the DHCP will broadcast packets to. It is derived from __`ip`__ and __`subnet_mask`__, unless set explicitly in CLI or in JSON config file. This is necessary in selecting the right NIC for broadcast when you have multiple.|`''`|_string_|
|__`file_server`__|This is the IP address of the file server containing network boot files that the DHCP server will specify to clients.|`'192.168.2.2'`|_string_|
|__`file_name`__|This specifies the file name that the client should look for on the remote server.|`'pxelinux.0'`|_string_|
|__`use_ipxe`__|This indicates whether or not iPXE is being used and adjusts itself accordingly.|`False`|_bool_|
|__`use_http`__|This indicates whether or not the built-in HTTP server is being used and adjusts itself accordingly.|`False`|_bool_|
|__`mode_proxy`__|This indicates whether or not the DHCP server should be started in ProxyDHCP mode or not.|`False`|_bool_|
|__`static_config`__|This specifies a static configuration dictionary so that it can give specific leases to specific MAC addresses.|`{}`|_dict_|
|__`whitelist`__|This indicates whether or not the DHCP server should use the static configuration dictionary as a whitelist; effectively, the DHCP server will only give out leases to those specified in the `static_config` dictionary.|`False`|_bool_|
|__`mode_debug`__|This indicates whether or not the DHCP server should be started in debug mode or not.|`False`|_bool_|
|__`mode_verbose`__|This indicates whether or not the DHCP server should be started in verbose mode or not.|`False`|_bool_|
|__`logger`__|A [Logger](https://docs.python.org/2/library/logging.html#logger-objects) object used for logging messages, if `None` a local [StreamHandler](https://docs.python.org/2/library/logging.handlers.html#streamhandler) instance will be created.|`None`|[_Logger_](https://docs.python.org/2/library/logging.html#logger-objects)|

## HTTP Server `pypxe.http`

### Importing
The HTTP service can be imported _one_ of the following two ways:
```python
from pypxe import http
```
```python
import pypxe.http
```

### Usage
The HTTP server class, __`HTTPD()`__, is constructed with the following __keyword arguments__:

|Keyword Argument|Description|Default|Type|
|---|---|---|---|
|__`ip`__|This is the IP address that the HTTP server will bind to.|`'0.0.0.0'` (so that it binds to all available interfaces)|_string_|
|__`port`__|This it the port that the HTTP server will run on.|`80` (default port for HTTP)|_int_|
|__`netboot_directory`__|This is the directory that the HTTP server will serve files from similarly to that of `tftpboot`.|`'.'` (current directory)|_string_|
|__`mode_debug`__|This indicates whether or not the HTTP server should be started in debug mode or not.|`False`|_bool_|
|__`mode_verbose`__|This indicates whether or not the HTTP server should be started in verbose mode or not.|`False`|_bool_|
|__`logger`__|A [Logger](https://docs.python.org/2/library/logging.html#logger-objects) object used for logging messages, if `None` a local [StreamHandler](https://docs.python.org/2/library/logging.handlers.html#streamhandler) instance will be created.|`None`|[_Logger_](https://docs.python.org/2/library/logging.html#logger-objects)|

## NBD Server `pypxe.nbd`

### Importing
The NBD service can be imported _one_ of the following two ways:
```python
from pypxe import http
```
```python
import pypxe.nbd
```

### Usage
The NBD server class, __`NBD()`__, is constructed with the following __keyword arguments__:

|Keyword Argument|Description|Default|Type|
|---|---|---|---|
|__`ip`__|This is the IP address that the NBD server will bind to.|`'0.0.0.0'` (so that it binds to all available interfaces)|_string_|
|__`port`__|This it the port that the NBD server will run on.|`10809` (default port for NBD)|_int_|
|__`block_device`__|The filename of the block device to be used as the root device.|`''`|_string_|
|__`write`__|Enable write support on the block device.|`False`|_bool_|
|__`cow`__|Enable copy-on-write support on the block device.|`True`|_bool_|
|__`in_mem`__|Enable _in-memory_ copy-on-write support on the block device. `False` causes changes to be stored on disk.|`False`|_bool_|
|__`copy_to_ram`__|Copy the disk image to RAM when the service starts.|`False`|_bool_|
|__`mode_debug`__|This indicates whether or not the NBD server should be started in debug mode or not.|`False`|_bool_|
|__`mode_verbose`__|This indicates whether or not the NBD server should be started in verbose mode or not.|`False`|_bool_|
|__`logger`__|A [Logger](https://docs.python.org/2/library/logging.html#logger-objects) object used for logging messages, if `None` a local [StreamHandler](https://docs.python.org/2/library/logging.handlers.html#streamhandler) instance will be created.|`None`|[_Logger_](https://docs.python.org/2/library/logging.html#logger-objects)|


## Additional Information
* The function `chr(0)` is used in multiple places throughout the servers. This denotes a `NULL` byte, or `\x00`
* Python 2.6 does not include the `argparse` module, it is included in the standard library as of 2.7 and newer. The `argparse` module is required to take in command line arguments and `pypxe.server` will not run without it.
* The TFTP server currently does not support transfer of large files, this is a known issue (see #35). Instead of using TFTP to transfer large files (roughly 33MB or greater) it is recommended that you use the HTTP server to do so. iPXE supports direct boot from HTTP and certain kernels (once you've booted into `pxelinux.0` via TFTP) support fetching files via HTTP as well.
