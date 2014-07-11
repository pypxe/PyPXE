#To Do

- [ ] Add ```-debug``` prints to DHCP/TFT/HTTP (such as 404, OFFER/ACK, etc. w/ filename)
  - [X] DHCP Server ```--dhcp-debug```
  - [ ] TFTP Server ```--tftp-debug```
  - [ ] HTTP Server ```-http-debug```
- [X] Implement [PEP8](http://legacy.python.org/dev/peps/pep-0008/) style guidelines across entire project
- [ ] Turn longer functions to kwargs vs positional
- [X] Remove hard-coded ```/24``` in DHCPD (Psychomario)
- [X] Add ```--no-tftp``` option to ```server.py```