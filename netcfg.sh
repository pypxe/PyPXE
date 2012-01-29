#!/bin/bash
if [[ "X"$1 == "X" ]]; then
    echo -ne "Usage: $0 <int>\n\te.g $0 eth0\n"
    exit 1
fi
cidr2mask() {
  local i mask=""
  local full_octets=$(($1/8))
  local partial_octet=$(($1%8))

  for ((i=0;i<4;i+=1)); do
    if [ $i -lt $full_octets ]; then
      mask+=255
    elif [ $i -eq $full_octets ]; then
      mask+=$((256 - 2**(8-$partial_octet)))
    else
      mask+=0
    fi  
    test $i -lt 3 && mask+=.
  done

  echo $mask
}
ipaddr=$(ip addr show $1 | grep inet | sed "s/ brd.*//;s/.*inet //;s/\/.*//")
broadcast=$(ip addr show $1 | grep inet.\*brd | sed "s/.*brd\ //;s/\ scope.*//g")
offerfrom=$(echo $ipaddr | sed "s/[0-9]*$//;s/$/100/")
offerto=$(echo $ipaddr | sed "s/[0-9]*$//;s/$/150/")
subnetmask=$(cidr2mask $(ip addr show $1 | grep inet | sed "s/ brd.*//;s/.*inet //;s/.*\///"))
router=$(ip route | grep $1 | grep default | sed "s/.*via\ //;s/\ dev.*//")
nameserver=$(cat /etc/resolv.conf|grep nameserver|head -n1|sed s/nameserver\ //)
network=$(echo $ipaddr | sed "s/[0-9]*$//")
sed -i "s/^serverhost=.*/serverhost='$ipaddr'/" dhcpd.py
sed -i "s/^tftpserver=.*/tftpserver='$ipaddr'/" dhcpd.py
sed -i "s/^offerfrom=.*/offerfrom='$offerfrom'/" dhcpd.py
sed -i "s/^offerto=.*/offerto='$offerto'/" dhcpd.py
sed -i "s/^subnetmask=.*/subnetmask='$subnetmask'/" dhcpd.py
sed -i "s/^broadcast=.*/broadcast='$broadcast'/" dhcpd.py
sed -i "s/^router=.*/router='$router'/" dhcpd.py
sed -i "s/^dnsserver=.*/dnsserver='$nameserver'/" dhcpd.py
sed -i "s/^for\ ip\ in\ \['[0-9]*.[0-9]*.[0-9]*.'/for\ ip\ in\ \['$network'/" dhcpd.py
