#All the following functions are individually defined
#in RFC5661 sections 18.*

nfs_opnum4 = {}
nfs_opnum4_append = lambda f,x: nfs_opnum4.__setitem__(x,f)


def ACCESS():
    #3
    return
nfs_opnum4_append(ACCESS, 3)

def CLOSE():
    #4
    return
nfs_opnum4_append(CLOSE, 4)

def COMMIT():
    #5
    return
nfs_opnum4_append(COMMIT, 5)

def CREATE():
    #6
    return
nfs_opnum4_append(CREATE, 6)

def GETATTR():
    #9
    return
nfs_opnum4_append(GETATTR, 9)

def GETFH():
    #10
    return
nfs_opnum4_append(GETFH, 10)

def LOCK():
    #12
    return
nfs_opnum4_append(LOCK, 12)

def LOCKT():
    #13
    return
nfs_opnum4_append(LOCKT, 13)

def LOCKU():
    #14
    return
nfs_opnum4_append(LOCKU, 14)

def LOOKUP():
    #15
    return
nfs_opnum4_append(LOOKUP, 15)

def LOOKUPP():
    #16
    return
nfs_opnum4_append(LOOKUPP, 16)

def NVERIFY():
    #17
    return
nfs_opnum4_append(NVERIFY, 17)

def OPEN():
    #18
    return
nfs_opnum4_append(OPEN, 18)

def OPEN_DOWNGRADE():
    #21
    return
nfs_opnum4_append(OPEN_DOWNGRADE, 21)

def PUTFH():
    #22
    return
nfs_opnum4_append(PUTFH, 22)

def PUTPUBFH():
    #23
    return
nfs_opnum4_append(PUTPUBFH, 23)

def PUTROOTFH():
    #24
    return
nfs_opnum4_append(PUTROOTFH, 24)

def READ():
    #25
    return
nfs_opnum4_append(READ, 25)

def READDIR():
    #26
    return
nfs_opnum4_append(READDIR, 26)

def READLINK():
    #27
    return
nfs_opnum4_append(READLINK, 27)

def REMOVE():
    #28
    return
nfs_opnum4_append(REMOVE, 28)

def RENAME():
    #29
    return
nfs_opnum4_append(RENAME, 29)

def RESTOREFH():
    #31
    return
nfs_opnum4_append(RESTOREFH, 31)

def SAVEFH():
    #32
    return
nfs_opnum4_append(SAVEFH, 32)

def SECINFO():
    #33
    return
nfs_opnum4_append(SECINFO, 33)

def SETATTR():
    #34
    return
nfs_opnum4_append(SETATTR, 34)

def VERIFY():
    #37
    return
nfs_opnum4_append(VERIFY, 37)

def WRITE():
    #38
    return
nfs_opnum4_append(WRITE, 38)

def BACKCHANNEL_CTL():
    #40
    return
nfs_opnum4_append(BACKCHANNEL_CTL, 40)

def BIND_CONN_TO_SESSION():
    #41
    return
nfs_opnum4_append(BIND_CONN_TO_SESSION, 41)

def EXCHANGE_ID():
    #42
    return
nfs_opnum4_append(EXCHANGE_ID, 42)

def CREATE_SESSION():
    #43
    return
nfs_opnum4_append(CREATE_SESSION, 43)

def DESTROY_SESSION():
    #44
    return
nfs_opnum4_append(DESTROY_SESSION, 44)

def FREE_STATEID():
    #45
    return
nfs_opnum4_append(FREE_STATEID, 45)

def LAYOUTCOMMIT():
    #49
    return
nfs_opnum4_append(LAYOUTCOMMIT, 49)

def SECINFO_NO_NAME():
    #52
    return
nfs_opnum4_append(SECINFO_NO_NAME, 52)

def SEQUENCE():
    #53
    return
nfs_opnum4_append(SEQUENCE, 53)

def SET_SSV():
    #54
    return
nfs_opnum4_append(SET_SSV, 54)

def TEST_STATEID():
    #55
    return
nfs_opnum4_append(TEST_STATEID, 55)

def DESTROY_CLIENTID():
    #57
    return
nfs_opnum4_append(DESTROY_CLIENTID, 57)

def RECLAIM_COMPLETE():
    #58
    return
nfs_opnum4_append(RECLAIM_COMPLETE, 58)
