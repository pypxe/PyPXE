import nbd

args = {
        'blockdevice':'blank.img',
        'mode_debug':True,
        'mode':'rw'
        }

nbd.NBD(**args).listen()
