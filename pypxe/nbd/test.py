import nbd

args = {
        'blockdevice':'blank.img',
        'mode_debug':True,
        'mode':'w'
        }

nbd.NBD(**args).listen()
