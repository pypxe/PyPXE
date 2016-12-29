# TODO
 - Make NFS UDP too
 - Fix READDIRPLUS modifications to self.filehandles, it's being lost very regularly for some reason
    Maybe nfs `self` should have a Queue of new file handles that is fixed up by the decorator?
 - Finish Implement NFS3
 - statd is 100024 is LOCK manager

# Thread layout
```
shim.py
|
|--portmapper.py--PORTMAPPERUDP
|               |-PORTMAPPERTCP--CLIENT 1
|                              |-...
|                              |-CLIENT n
|
|--mount.py--MOUNTUDP
|          |-MOUNTTCP--CLIENT 1
|                    |-...
|                    |-CLIENT n
|
|--nfs.py--NFSTCP--CLIENT 1
|                |-...
|                |-CLIENT n
```
