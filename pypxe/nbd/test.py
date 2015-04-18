import nbd
# kernel cmdline options:
# https://wiki.archlinux.org/index.php/Syslinux#Pxelinux
# initrd build config:
# https://wiki.archlinux.org/index.php/Diskless_system#Bootstrapping_installation
args = {
        'blockdevice':'arch.img',
        'mode_debug':True,
        'write':True,
        'cow':True
        }
# rw and multiple clients not safe
# rcow/ro and multiple clients OK
# need a 'mode' and a 'cow' arg

nbd.NBD(**args).listen()
