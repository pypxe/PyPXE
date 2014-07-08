##Pure Python2 PXE (DHCP/TFTP/HTTP) server.

Supports iPXE chainloading, and therefore iPXE scripts.

Edit the server.py settings to your preferred network settings or run with --help
Example TinyCore iso included along with relevant configs in netboot/
chainload.kpxe is the undionly.kpxe from the iPXE project (http://ipxe.org)

Each server (TFTP/HTTP/DHCP) is in it's own class in it's own file. These can be used
independently. See server.py for example usage

To run:

    sudo python2 server.py

--help:
```
usage: server.py [-h] [--dhcp | --proxydhcp | --no-dhcp] [--ipxe | --no-ipxe]
                 [--http | --no-http] [-s DHCP_SERVER_IP]
                 [-f DHCP_FILESERVER_IP] [-b DHCP_OFFER_BEGIN]
                 [-e DHCP_OFFER_END] [-n DHCP_SUBNET] [-r DHCP_ROUTER]
                 [-d DHCP_DNS] [-a NETBOOT] [-i DHCP_FILENAME]

Set options at runtime. Defaults are in server.py

optional arguments:
  -h, --help            show this help message and exit
  --dhcp                Use builtin DHCP server (default: True)
  --proxydhcp           Use builtin DHCP server in proxy mode (default: True)
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

**WARNING:**
Neither of these servers are fully compliant. They work for PXE.
Any other uses are purely coincidental. Use at your own risk.


License:
```
The MIT License (MIT)

Copyright (c) 2014 PsychoMario

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
