Pure Python2 PXE (DHCP/TFTP/HTTP) server.

Supports iPXE chainloading, and therefore iPXE scripts.

Edit the server.py settings to your preferred network settings or run with --help
Example TinyCore iso included along with relevant configs in netboot/
chainload.kpxe is the undionly.kpxe from the iPXE project (http://ipxe.org)

Each server (TFTP/HTTP/DHCP) is in it's own class in it's own file. These can be used
independently. See server.py for example usage

To run:

    sudo python2 server.py

WARNING:
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
