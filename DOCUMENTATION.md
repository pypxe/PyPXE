**NOTE:** This documentation is unfinished and is still a work in progress.

#Background
>The Preboot eXecution Environment (PXE, also known as Pre-Execution Environment; sometimes pronounced "pixie") is an environment to boot computers using a network interface independently of data storage devices (like hard disks) or installed operating systems.
-[Wikipedia](https://en.wikipedia.org/wiki/Preboot_Execution_Environment) 

PXE allows computers to boot from a binary image stored on a server, rather than the local hardware. Broadly speaking, a DHCP server informs a client of the TFTP server and filename from which to boot. 

___

#PyPXE Services

##DHCP In the standard DHCP mode, the server has been implemented from [RFC2131](http://www.ietf.org/rfc/rfc2131.txt), [RFC2132](http://www.ietf.org/rfc/rfc2132.txt), and the [DHCP Wikipedia Entry](https://en.wikipedia.org/wiki/Dynamic_Host_Configuration_Protocol).  

The DHCP server is in charge of assigning new clients with IP addresses, and informing them of the location of the TFTP server and filename. The top half of the DHCP request, as seen on the Wikipedia entry consists of some network information, followed by 192 legacy null bytes, and then the magic cookie.  

After the magic cookie there are optional fields. These fields are defined by the field ID, a length byte and then the option data. Every DHCP packet has an option 53 field. This field specifies the packet type, be it DISCOVERY, OFFER, REQUEST or ACKNOWLEDGEMENT.  

The Discovery and Request packets are those sent by the client to the broadcast address (IPv4 255.255.255.255). The Offer and Acknowledgement packets are sent from the server to the broadcast address. These four packets make up the four way handshake.  

The Offer and Acknowledgement packets both contain the same option data for each client. This can include the router, subnet mask, lease time, and dhcp server.

Also included in these options are our PXE options. The minimum required option fields are option 66 and option 67. Option 66 denotes the IP of the TFTP server, and option 67 denotes the filename of the file to retrieve and boot.  

Once the four way handshake is complete, the client will send a TFTP read request to the given IP address requesting the given filename.

###ProxyDHCP

##TFTP
We have only implemented the read OPCODE for the TFTP server, as PXE does not use write. The main TFTP protocol is defined in [RFC1350](http://www.ietf.org/rfc/rfc1350.txt)

###blksize
The blksize option, as defined in [RFC2348](http://www.ietf.org/rfc/rfc2348.txt) allows the client to specify the block size for each transfer packet. The blksize option is passed along with the read opcode, following the filename and mode. The format is blksize, followed by a null byte, followed by the ASCII base-10 representation of the blksize (i.e 512 rather than 0x200), followed by another null byte.

##HTTP
We have implemented GET and HEAD, as there is no requirement for any other methods. The referenced RFCs are [RFC2616](http://www.ietf.org/rfc/rfc2616.txt) and [RFC7230](http://www.ietf.org/rfc/rfc7230.txt).  

The HEAD method is used by some PXE ROMs to find the Content-Length before the GET is sent.

##Additional Information
The function ```chr(0)``` is used in multiple places throughout the servers. This denotes a NULL byte, or ```\x00```