import nbd
args = {
        'blockdevice':'arch.img',
        'mode_debug':True,
        'write':True,
        'cow':True,
        'inmem':True,
        'copytoram':True
        }
# rw and multiple clients not safe
# rcow/ro and multiple clients OK

nbd.NBD(**args).listen()
