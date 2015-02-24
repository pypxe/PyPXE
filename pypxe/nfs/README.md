#NFS Daemon
##RFCs
- [NFSv4.1 RFC5661](https://tools.ietf.org/html/rfc5661)
- [RPCv2 RFC5531](https://tools.ietf.org/html/rfc5531)
- [XDR RFC4506](https://tools.ietf.org/html/rfc4506)

# Notes
The Linux Kernel cannot natively boot NFSv4.1, so it is necessary to create
a suitable initrd

# Issues

* A bad client could possibly perform directory traversal out of the root.
  UNTESTED

# Booting

1. Follow
   https://wiki.archlinux.org/index.php/Diskless_system#Client_installation
   up to but not including `NBD`. Note, you can do it in a directory, it
   does not have to be a disk image.

2. Copy `/boot/{vmlinuz-linux, initramfs-linux.img}` to `netboot/` (pypxe-server's `-a`)

3. Modify `nfsrpc.py->class NFS->def __init__()->self.shared["root"]` to point to
   the directory from step 1.

4. Add a boot option to  `pxelinux.cfg/default` containing:
    `KERNEL vmlinuz-linux`, `APPEND initrd=initramfs-linux.img ip=dhcp nfsroot=192.168.0.3:/ ro`
    Where the nfsroot address is the host of `test.py`

5. You might want to add `tmpfs /var tmpfs defaults 0 0` to the root's
   fstab for systemd

5. Run `pypxe-server.py` and `test.py`, netboot your client.

# TODO
The following is a list of things left to do. Order doesn't matter so much
except for dependent items.

* Finish operations (operation.py)

* Implement locking (OPEN/READ/CLOSE etc.) RFC5661§9

* Implement Read Only properly (Documentation unknown, RFC5661§15.4 defines where
  NFS4ERR_ROFS can be used)

* Rewrite OPEN (Feels brittle currently)

* Profile (Our boot is slower than kernel NFS boot)
