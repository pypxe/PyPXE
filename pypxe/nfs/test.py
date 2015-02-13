import nfsrpc
#sudo mount -t nfs localhost:/ tmp
nfs = nfsrpc.NFS()
nfs.listen()
