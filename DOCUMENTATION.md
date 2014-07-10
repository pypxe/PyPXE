#PXE

##DHCP
###ProxyDHCP

##TFTP
###blksize

##HTTP
We have implemented GET and HEAD, as there is no requirement for any other
methods. The referenced RFCs are [RFC2616](http://www.ietf.org/rfc/rfc2616.txt) and [RFC7230](http://www.ietf.org/rfc/rfc7230.txt).  
The HEAD method is used by some PXE ROMs to find the Content-Length before
the GET is sent.
