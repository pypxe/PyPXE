class RPC:
    class PMAPPROC:
        NULL    = 0
        SET     = 1
        UNSET   = 2
        GETADDR = 3
        DUMP    = 4

    class MOUNT_PROC:
        NULL    = 0
        MNT     = 1
        DUMP    = 2
        UMNT    = 3
        UMNTALL = 4
        EXPORT  = 5

    class NFS_PROC:
        NFSPROC3_NULL        = 0
        NFSPROC3_GETATTR     = 1
        NFSPROC3_SETATTR     = 2
        NFSPROC3_LOOKUP      = 3
        NFSPROC3_ACCESS      = 4
        NFSPROC3_READLINK    = 5
        NFSPROC3_READ        = 6
        NFSPROC3_WRITE       = 7
        NFSPROC3_CREATE      = 8
        NFSPROC3_MKDIR       = 9
        NFSPROC3_SYMLINK     = 10
        NFSPROC3_MKNOD       = 11
        NFSPROC3_REMOVE      = 12
        NFSPROC3_RMDIR       = 13
        NFSPROC3_RENAME      = 14
        NFSPROC3_LINK        = 15
        NFSPROC3_READDIR     = 16
        NFSPROC3_READDIRPLUS = 17
        NFSPROC3_FSSTAT      = 18
        NFSPROC3_FSINFO      = 19
        NFSPROC3_PATHCONF    = 20
        NFSPROC3_COMMIT      = 21

    class LOCK_PROC:
        NLMPROC4_NULL        = 0
        NLMPROC4_TEST        = 1
        NLMPROC4_LOCK        = 2
        NLMPROC4_CANCEL      = 3
        NLMPROC4_UNLOCK      = 4
        NLMPROC4_GRANTED     = 5
        NLMPROC4_TEST_MSG    = 6
        NLMPROC4_LOCK_MSG    = 7
        NLMPROC4_CANCEL_MSG  = 8
        NLMPROC4_UNLOCK_MSG  = 9
        NLMPROC4_GRANTED_MSG = 10
        NLMPROC4_TEST_RES    = 11
        NLMPROC4_LOCK_RES    = 12
        NLMPROC4_CANCEL_RES  = 13
        NLMPROC4_UNLOCK_RES  = 14
        NLMPROC4_GRANTED_RES = 15
        NLMPROC4_SHARE       = 16
        NLMPROC4_UNSHARE     = 17
        NLMPROC4_NM_LOCK     = 18
        NLMPROC4_FREE_ALL    = 19

    class IPPROTO:
        IPPROTO_TCP4 = "tcp"
        IPPROTO_UDP4 = "udp"
        IPPROTO_TCP6 = "tcp6"
        IPPROTO_UDP6 = "udp6"

owner = "PyPXE"
programs = {
    100000: { # portmapper
            "version": [2, 3, 4],
            "procedures": [
                RPC.PMAPPROC.NULL,
                RPC.PMAPPROC.SET,
                RPC.PMAPPROC.UNSET,
                RPC.PMAPPROC.GETADDR,
                RPC.PMAPPROC.DUMP
            ],
            "protocol": [RPC.IPPROTO.IPPROTO_TCP4, RPC.IPPROTO.IPPROTO_UDP4],
            "port": {
                RPC.IPPROTO.IPPROTO_TCP4: 111,
                RPC.IPPROTO.IPPROTO_UDP4: 111,
                RPC.IPPROTO.IPPROTO_TCP6: 111,
                RPC.IPPROTO.IPPROTO_UDP6: 111,
            },
            "owner": owner,
            "address": {
                RPC.IPPROTO.IPPROTO_TCP4: "0.0.0.0",
                RPC.IPPROTO.IPPROTO_UDP4: "0.0.0.0",
                RPC.IPPROTO.IPPROTO_TCP6: "::1",
                RPC.IPPROTO.IPPROTO_UDP6: "::1",
            }
        },
    100003: { # nfs
            "version": [3],
            "procedures": [
                RPC.NFS_PROC.NFSPROC3_NULL,
                RPC.NFS_PROC.NFSPROC3_GETATTR,
                RPC.NFS_PROC.NFSPROC3_SETATTR,
                RPC.NFS_PROC.NFSPROC3_LOOKUP,
                RPC.NFS_PROC.NFSPROC3_ACCESS,
                RPC.NFS_PROC.NFSPROC3_READLINK,
                RPC.NFS_PROC.NFSPROC3_READ,
                RPC.NFS_PROC.NFSPROC3_WRITE,
                RPC.NFS_PROC.NFSPROC3_CREATE,
                RPC.NFS_PROC.NFSPROC3_MKDIR,
                RPC.NFS_PROC.NFSPROC3_SYMLINK,
                RPC.NFS_PROC.NFSPROC3_MKNOD,
                RPC.NFS_PROC.NFSPROC3_REMOVE,
                RPC.NFS_PROC.NFSPROC3_RMDIR,
                RPC.NFS_PROC.NFSPROC3_RENAME,
                RPC.NFS_PROC.NFSPROC3_LINK,
                RPC.NFS_PROC.NFSPROC3_READDIR,
                RPC.NFS_PROC.NFSPROC3_READDIRPLUS,
                RPC.NFS_PROC.NFSPROC3_FSSTAT,
                RPC.NFS_PROC.NFSPROC3_FSINFO,
                RPC.NFS_PROC.NFSPROC3_PATHCONF,
                RPC.NFS_PROC.NFSPROC3_COMMIT
            ],
            "protocol": [RPC.IPPROTO.IPPROTO_TCP4],
            "port": {
            },
            "owner": owner,
            "address": {
            }
        },
    100005: { # mountd
            "version": [3],
            "procedures": [
                RPC.MOUNT_PROC.NULL,
                RPC.MOUNT_PROC.MNT,
                RPC.MOUNT_PROC.DUMP,
                RPC.MOUNT_PROC.UMNT,
                RPC.MOUNT_PROC.UMNTALL,
                RPC.MOUNT_PROC.EXPORT
            ],
            "protocol": [RPC.IPPROTO.IPPROTO_TCP4],
            "port": {
            },
            "owner": owner,
            "address": {
            }
        },
    100021: { # lock
            "version": [4],
            "procedures": [
            ],
            "protocol": [RPC.IPPROTO.IPPROTO_TCP4],
            "port": {
            },
            "owner": owner,
            "address": {
            }
        }
    }
