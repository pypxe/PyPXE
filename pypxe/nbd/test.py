import nbd

args = {
        'blockdevice':'blank.img',
        'mode_debug':True,
        'mode':'r'
        }

nbd.NBD(**args).listen()
