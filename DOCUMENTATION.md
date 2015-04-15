#Background
>The Preboot eXecution Environment (PXE, also known as Pre-Execution Environment; sometimes pronounced "pixie") is an environment to boot computers using a network interface independently of data storage devices (like hard disks) or installed operating systems. -[Wikipedia](https://en.wikipedia.org/wiki/Preboot_Execution_Environment) 

PXE allows computers to boot from a binary image stored on a server, rather than the local hardware. Broadly speaking, a DHCP server informs a client of the TFTP server and filename from which to boot. 

##DHCP
In the standard DHCP mode, the server has been implemented from [RFC2131](http://www.ietf.org/rfc/rfc2131.txt), [RFC2132](http://www.ietf.org/rfc/rfc2132.txt), and the [DHCP Wikipedia Entry](https://en.wikipedia.org/wiki/Dynamic_Host_Configuration_Protocol).  

The DHCP server is in charge of assigning new clients with IP addresses, and informing them of the location of the TFTP server and filename they should look for. The top half of the DHCP request, as seen on the Wikipedia entry, consists of some network information, followed by 192 legacy null bytes, and then the magic cookie.  

After the magic cookie, there are optional fields. These fields are defined by the field ID, a length byte and then the option data. Every DHCP packet has an option 53 field. This field specifies the packet type, be it DISCOVERY, OFFER, REQUEST or ACKNOWLEDGEMENT.  

The DISCOVERY and REQUEST packets are those sent by the client to the broadcast address (IPv4: 255.255.255.255) where the client sends this data on port 68 and the server receives it on port 68. The OFFER and ACKNOWLEDGEMENT packets are sent from the server to the broadcast address where the server sends this data on port 67 and the client receives it on port 68. These four packets make up the four-way handshake.  

The OFFER and ACKNOWLEDGEMENT packets both contain the same option data for each client. This can include the router, subnet mask, lease time, and DHCP server IP address.

Also included in these options are our PXE options. The minimum required option fields are option 66 and option 67. Option 66 denotes the IP of the TFTP server, and option 67 denotes the filename of the file to retrieve and boot.  

Once the four way handshake is complete, the client will send a TFTP read request to the given fileserver IP address requesting the given filename.

###ProxyDHCP
ProxyDHCP mode is useful for when you either cannot (or do not want to) change the main DHCP server on a network. The bulk of ProxyDHCP information can be found in the [Intel PXE spec](http://www.pix.net/software/pxeboot/archive/pxespec.pdf). The main idea behind ProxyDHCP is that the main network DHCP server can hand out the IP leases while the ProxyDHCP server hands out the PXE information to each client. Therefore, slightly different information is sent in the ProxyDHCP packets.

There are multiple ways to implement ProxyDHCP: broadcast, multicast, unicast or lookback. Lookback is the simplest implementation and this is what we have chosen to use. When we receive a DHCP DISCOVER from a client, we respond with a DHCP OFFER but the OFFER packet is sent without a few fields we would normally send in standard DHCP mode (this includes an offered IP address, along with any other network information such as router, DNS server(s), etc.). What we include in this OFFER packet (which isn't in a normal DHCP packet), is a vendor-class identifier of 'PXEClient' - this string identifies the packet as being relevant to PXE booting.

There are a few vendor-specific options under the DHCP option 43:
* The first of these options is PXE discovery control; this is a bitmask defined in the PXE spec. When bit 3 is set, the PXE client will look backwards in the packet for the filename. The filename is located in the standard 'DHCP Boot Filename' area, previously referred to as 'legacy'. This is a NULL-terminated string located at offset 150 in the DHCP packet (before the DHCP magic cookie).
* The second vendor-specific option that is used is the PXE menu prompt. Although not visible, this is required by the spec and causes problems if it is missing. The main use for this is for the other DISCOVERY modes.  

The client should receive two DHCP OFFER packets in ProxyDHCP mode: the first from the main DHCP server and the second from the ProxyDHCP server. Once both are received, the client will continue on with the DHCP handshake and, after it is complete, the client will boot using the settings in the DHCP OFFER from the ProxyDHCP server.

##TFTP
We have only implemented the read OPCODE for the TFTP server, as PXE does not use write. The main TFTP protocol is defined in [RFC1350](http://www.ietf.org/rfc/rfc1350.txt)

###blksize
The blksize option, as defined in [RFC2348](http://www.ietf.org/rfc/rfc2348.txt) allows the client to specify the block size for each transfer packet. The blksize option is passed along with the read opcode, following the filename and mode. The format is blksize, followed by a null byte, followed by the ASCII base-10 representation of the blksize (i.e 512 rather than 0x200), followed by another null byte.

##HTTP
We have implemented GET and HEAD, as there is no requirement for any other methods. The referenced RFCs are [RFC2616](http://www.ietf.org/rfc/rfc2616.txt) and [RFC7230](http://www.ietf.org/rfc/rfc7230.txt).  

The HEAD method is used by some PXE ROMs to find the Content-Length before the GET is sent.

#PyPXE Services
The PyPXE library provies the following services for the purpose of creating a Python-based PXE environment: TFTP, HTTP, and DHCP. Each service must be imorted independently as such:

* `from pypxe import tftp` or `import pypxe.tftp` imports the TFTP service
* `from pypxe import dhcp` or `import pypxe.dhcp` imports the DHCP service
* `from pypxe import http` or `import pypxe.http` imports the HTTP service

**See [`pypxe-server.py`](pypxe-server.py) in the root of the repo for example usage on how to call, define, and setup the services.** When running any Python script that uses these classes, it should be run as a user with root privileges as they bind to interfaces and without root privileges the services will most likely fail to bind properly.

##TFTP Server `pypxe.tftp`

###Importing
The TFTP service can be imported _one_ of the following two ways:
```python
from pypxe import tftp
```
```python
import pypxe.tftp
```

###Usage
The TFTP server class, __`TFTPD()`__, is constructed with the following __keyword arguments__:
* __`ip`__
  * Description: This is the IP address that the TFTP server will bind to.
  * Default: `'0.0.0.0'` (so that it binds to all available interfaces)
  * Type: _string_
* __`port`__
  * Description: This it the port that the TFTP server will run on.
  * Default: `69` (default port for TFTP)
  * Type: _int_
* __`netbootDirectory`__
  * Description: This is the directory that the TFTP server will serve files from similarly to that of `tftpboot`.
  * Default: `'.'` (current directory)
  * Type: _string_
* __`mode_debug`__
  * Description: This indicates whether or not the TFTP server should be started in debug mode or not.
  * Default: `False`
  * Type: bool
* __`logger`__
  * Description: A [Logger](https://docs.python.org/2/library/logging.html#logger-objects) object used for logging messages, if `None` a local [StreamHandler](https://docs.python.org/2/library/logging.handlers.html#streamhandler) instance will be created
  * Default: `None` 

##DHCP Server `pypxe.dhcp`

###Importing
The DHCP service can be imported _one_ of the following two ways:
```python
from pypxe import dhcp
```
```python
import pypxe.dhcp
```

###Usage
The DHCP server class, __`DHCPD()`__, is constructed with the following __keyword arguments__:
* __`ip`__
  * Description: This is the IP address that the DHCP server itself binds to.
  * Default: `'192.168.2.2'`
  * Type: _string_
* __`port`__
  * Description: This it the port that the TFTP server will run on.
  * Default: `67` (default port to listen for DHCP requests)
  * Type: _int_
* __`offerfrom`__ 
  * Description: This specifies the beginning of the range of IP addreses that the DHCP server will hand out to clients.
  * Default: `'192.168.2.100'`
  * Type: _string_
* __`offerto`__
  * Description: This specifies the end of the range of IP addresses that the DHCP server will hand out to clients.
  * Default: `'192.168.2.150'`
  * Type: _string_
* __`subnetmask`__
  * Description: This specifies the subnet mask that the DHCP server will specify to clients.
  * Default: `'255.255.255.0'`
  * Type: _string_
* __`router`__
  * Description: This specifies the IP address of the router that the DHCP server will specify to clients.
  * Default: `'192.168.2.1'`
  * Type: _string_
* __`dnsserver`__
  * Description: This specifies the DNS server that the DHCP server will specify to clients. Only one DNS server can be passed.
  * Default: `'8.8.8.8'` ([Google Public DNS](https://developers.google.com/speed/public-dns/))
  * Type: _string_
* __`broadcast`__
  * Description: This specifies the broadcast address the DHCP will broadcast packets to.
  * Default: `'<broadcast>'`
  * Type: _string_
* __`fileserver`__
  * Description: This is the IP address of the file server containing network boot files that the DHCP server will specify to clients.
  * Default: `'192.168.2.2'`
  * Type: _string_
* __`filename`__
  * Description: This specifies the file name that the client should look for on the remote server.
  * Default: `'pxelinux.0'`
  * Type: _string_
* __`useipxe`__
  * Description: This indicates whether or not iPXE is being used and adjusts itself accordingly.
  * Default: `False`
  * Type: _bool_
* __`usehttp`__
  * Description: This indicates whether or not the built-in HTTP server is being used and adjusts itself accordingly.
  * Default: `False`
  * Type: _bool_
* __`mode_proxy`__
  * Description: This indicates whether or not the DHCP server should be started in ProxyDHCP mode or not.
  * Default: `False`
  * Type: _bool_
* __`mode_debug`__
  * Description: This indicates whether or not the DHCP server should be started in debug mode or not.
  * Default: `False`
  * Type: _bool_
* __`logger`__
  * Description: A [Logger](https://docs.python.org/2/library/logging.html#logger-objects) object used for logging messages, if `None` a local [StreamHandler](https://docs.python.org/2/library/logging.handlers.html#streamhandler) instance will be created
  * Default: `None` 

##HTTP Server `pypxe.http`

###Importing
The HTTP service can be imported _one_ of the following two ways:
```python
from pypxe import http
```
```python
import pypxe.http
```

###Usage
The HTTP server class, __`HTTPD()`__, is constructed with the following __keyword arguments__:
* __`ip`__
  * Description: This is the IP address that the HTTP server will bind to.
  * Default: `'0.0.0.0'` (so that it binds to all available interfaces)
  * Type: _string_
* __`port`__
  * Description: This it the port that the HTTP server will run on.
  * Default: `80` (default port for HTTP)
  * Type: _int_
* __`netbootDirectory`__
  * Description: This is the directory that the HTTP server will serve files from similarly to that of `tftpboot`.
  * Default: `'.'` (current directory)
  * Type: _string_
* __`mode_debug`__
  * Description: This indicates whether or not the HTTP server should be started in debug mode or not.
  * Default: `False`
  * Type: bool
* __`logger`__
  * Description: A [Logger](https://docs.python.org/2/library/logging.html#logger-objects) object used for logging messages, if `None` a local [StreamHandler](https://docs.python.org/2/library/logging.handlers.html#streamhandler) instance will be created
  * Default: `None` 

##Additional Information
* The function `chr(0)` is used in multiple places throughout the servers. This denotes a `NULL` byte, or `\x00`
* Python 2.6 does not include the `argparse` module, it is included in the standard library as of 2.7 and newer. The `argparse` module is required to take in command line arguments and `pypxe-server.py` will not run without it.
* The TFTP server currently does not support transfer of large files, this is a known issue (see #35). Instead of using TFTP to transfer large files (roughly 33MB or greater) it is recommended that you use the HTTP server to do so. iPXE supports direct boot from HTTP and certain kernels (once you've booted into `pxelinux.0` via TFTP) support fetching files via HTTP as well.
