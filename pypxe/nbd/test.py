import nbd
# kernel cmdline options:
# https://wiki.archlinux.org/index.php/Syslinux#Pxelinux
# initrd build config:
# https://wiki.archlinux.org/index.php/Diskless_system#Bootstrapping_installation
args = {
        'blockdevice':'blank.img',
        'mode_debug':True,
        'mode':'rw'
        }

nbd.NBD(**args).listen()
