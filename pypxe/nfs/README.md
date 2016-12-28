# TODO
 - Implement NFS3
 - Implement Lock thing
 - Find out and implement RPC 100024 STAT if not LOCK

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

# IPC
```
         portmapper.py
             /\
            /  \
           /    \
          /      \
         /        \
mount{TCP,UDP}    NFS
```
