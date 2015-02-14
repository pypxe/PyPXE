#NFS Daemon
##RFCs
- [NFSv4.1 RFC5661](https://tools.ietf.org/html/rfc5661)
- [RPCv2 RFC5531](https://tools.ietf.org/html/rfc5531)
- [XDR RFC4506](https://tools.ietf.org/html/rfc4506)

###RPCv2
TCP 2049
RPC Program Number: 100003 (RFC5531§Appendix C)  
Relevant structs laid out in RFC5531§9.

####General Protocol
Request:

```
msg_type
    .0 (uint
rpc_msg
    .xid = Random (uint)
    .call_body
        .rpcvers = 2 (uint)
        .prog = 100003 (uint)
        .vers = 4 (uint)
        .proc = 1 (COMPOUND) (uint)
        .cred = ...
        .verf = ...
        COMPOUND4args
            Tag = (Left to implementer, see RFC5661§16.2.3) (utf8str_cs)
            .minorversion = 1 (uint32_t)
            Operation Count (uint)
            For Each Operation:
                nfs_opnum4 (See RFC5661§16.2.1) (uint)
                nfs_argop4
```


Response:

```
msg_type
    .1 (uint)
rpc_msg
    .xid = match
    .reply_body
        Reply state
        .accepted_reply
            .verf ...
            Accept State = 0
            COMPOUND4res
                .status = 0
                .tag (see above)
                Operation Count (uint)
                For Each Operation:
                    nfs_opnum4 (uint)
                    nfs_resop4 (See RFC5661§16.2.2)
```

#Notes
Need to implement RPCSEC_GSS as per RFC5661§2.2.1.1





##Required Operations for implementation (RFC5661§17)
**RFC5661§**|Operation|Description
--- | --- | ---
18.1|ACCESS|Check Access Rights
18.2|CLOSE|Close File
18.3|COMMIT|Commit Cached Data
18.4|CREATE|Create a Non-Regular File Object
18.7|GETATTR|Get Attributes
18.8|GETFH|Get Current Filehandle
18.10|LOCK|Create Lock
18.11|LOCKT|Test for Lock
18.12|LOCKU|Unlock File
18.13|LOOKUP|Lookup Filename
18.14|LOOKUPP|Lookup Parent Directory
18.15|NVERIFY|Verify Difference in Attributes
18.16|OPEN|Open a Regular File
18.18|OPEN_DOWNGRADE|Reduce Open File Access
18.19|PUTFH|Set Current Filehandle
18.20|PUTPUBFH|Set Public Filehandle
18.21|PUTROOTFH|Set Root Filehandle
18.22|READ|Read from File
18.23|READDIR|Read Directory
18.24|READLINK|Read Symbolic Link
18.25|REMOVE|Remove File System Object
18.26|RENAME|Rename Directory Entry
18.27|RESTOREFH|Restore Saved Filehandle
18.28|SAVEFH|Save Current Filehandle
18.29|SECINFO|Obtain Available Security
18.30|SETATTR|Set Attributes
18.31|VERIFY|Verify Same Attributes
18.32|WRITE|Write to File
18.33|BACKCHANNEL_CTL|Backchannel Control
18.34|BIND_CONN_TO_SESSION|Associate Connection with Session
18.35|EXCHANGE_ID|Instantiate Client ID
18.36|CREATE_SESSION|Create New
18.37|DESTROY_SESSION|Destroy a Session
18.38|FREE_STATEID|Free Stateid with No Locks
18.42|LAYOUTCOMMIT|Commit Writes Made Using a Layout
18.45|SECINFO_NO_NAME|Get Security on Unnamed Object
18.46|SEQUENCE|Supply Per-Procedure Sequencing and Control
18.47|SET_SSV|Update SSV for a Client ID
18.48|TEST_STATEID|Test Stateids for Validity
18.50|DESTROY_CLIENTID|Destroy a Client ID
18.51|RECLAIM_COMPLETE|Indicates Reclaims Finished
|**Callback Operations**|
20.8|CB_RECALL_SLOT|Change Flow Control Limits
19.1|CB_NULL|No Operation
19.2|CB_COMPOUND|Compound Operations
