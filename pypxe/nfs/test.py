import nfsrpc
#sudo mount -t nfs localhost:/ tmp
rpc = nfsrpc.RPC()
rpc.listen()
