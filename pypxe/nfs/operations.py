import os
import struct
#All the following functions are individually defined
#in RFC5661 sections 18.*

#Operation ID for COMPOUND as per rFC5661-16.2.1
nfs_opnum4 = {}
nfs_opnum4_append = lambda f,x: nfs_opnum4.__setitem__(x,f)

#Functions all accept request and response strings, and state dict
#They MUST cleanup the request string themselves (chop off the start)

def ACCESS(request, response, state):
    #3
    return
nfs_opnum4_append(ACCESS, 3)

def CLOSE(request, response, state):
    #4
    return
nfs_opnum4_append(CLOSE, 4)

def COMMIT(request, response, state):
    #5
    return
nfs_opnum4_append(COMMIT, 5)

def CREATE(request, response, state):
    #6
    return
nfs_opnum4_append(CREATE, 6)

def GETATTR(request, response, state):
    #9
    return
nfs_opnum4_append(GETATTR, 9)

def GETFH(request, response, state):
    #10
    return
nfs_opnum4_append(GETFH, 10)

def LOCK(request, response, state):
    #12
    return
nfs_opnum4_append(LOCK, 12)

def LOCKT(request, response, state):
    #13
    return
nfs_opnum4_append(LOCKT, 13)

def LOCKU(request, response, state):
    #14
    return
nfs_opnum4_append(LOCKU, 14)

def LOOKUP(request, response, state):
    #15
    return
nfs_opnum4_append(LOOKUP, 15)

def LOOKUPP(request, response, state):
    #16
    return
nfs_opnum4_append(LOOKUPP, 16)

def NVERIFY(request, response, state):
    #17
    return
nfs_opnum4_append(NVERIFY, 17)

def OPEN(request, response, state):
    #18
    return
nfs_opnum4_append(OPEN, 18)

def OPEN_DOWNGRADE(request, response, state):
    #21
    return
nfs_opnum4_append(OPEN_DOWNGRADE, 21)

def PUTFH(request, response, state):
    #22
    return
nfs_opnum4_append(PUTFH, 22)

def PUTPUBFH(request, response, state):
    #23
    return
nfs_opnum4_append(PUTPUBFH, 23)

def PUTROOTFH(request, response, state):
    #24
    return
nfs_opnum4_append(PUTROOTFH, 24)

def READ(request, response, state):
    #25
    return
nfs_opnum4_append(READ, 25)

def READDIR(request, response, state):
    #26
    return
nfs_opnum4_append(READDIR, 26)

def READLINK(request, response, state):
    #27
    return
nfs_opnum4_append(READLINK, 27)

def REMOVE(request, response, state):
    #28
    return
nfs_opnum4_append(REMOVE, 28)

def RENAME(request, response, state):
    #29
    return
nfs_opnum4_append(RENAME, 29)

def RESTOREFH(request, response, state):
    #31
    return
nfs_opnum4_append(RESTOREFH, 31)

def SAVEFH(request, response, state):
    #32
    return
nfs_opnum4_append(SAVEFH, 32)

def SECINFO(request, response, state):
    #33
    return
nfs_opnum4_append(SECINFO, 33)

def SETATTR(request, response, state):
    #34
    return
nfs_opnum4_append(SETATTR, 34)

def VERIFY(request, response, state):
    #37
    return
nfs_opnum4_append(VERIFY, 37)

def WRITE(request, response, state):
    #38
    return
nfs_opnum4_append(WRITE, 38)

def BACKCHANNEL_CTL(request, response, state):
    #40
    return
nfs_opnum4_append(BACKCHANNEL_CTL, 40)

def BIND_CONN_TO_SESSION(request, response, state):
    #41
    return
nfs_opnum4_append(BIND_CONN_TO_SESSION, 41)

def EXCHANGE_ID(request, response, state):
    '''
    The client uses the EXCHANGE_ID operation to register a particular
    client owner with the server.  The client ID returned from this
    operation will be necessary for requests that create state on the
    server and will serve as a parent object to sessions created by the
    client.
        - RFC5661-18.35.3
    '''
    verifier = request[:8] #RFC5661-3.1/2
    request = request[8:]
    client = {}

    [client['owneridlen']] = struct.unpack("!I", request[:4])
    request = request[4:]
    client['ownerid'] = request[:client['owneridlen']]
    #Pad to multiple of 4?
    offset = client['owneridlen'] % 4
    request = request[client['owneridlen']+offset:]

    client['flags'] = struct.unpack("!I", request[:4])
    request = request[4:]
    client['stateprotection'] = struct.unpack("!I", request[:4])
    request = request[4:]

    [client['impl_id']] = struct.unpack("!I", request[:4])
    request = request[4:]

    [client['domainlen']] = struct.unpack("!I", request[:4])
    request = request[4:]
    client['domain'] = request[:client['domainlen']]
    offset = client['domainlen'] % 4
    request = request[client['domainlen']+offset:]

    [client['namelen']] = struct.unpack("!I", request[:4])
    request = request[4:]
    client['name'] = request[:client['namelen']]
    offset = client['namelen'] % 4
    request = request[client['namelen']+offset:]

    client['date'] = struct.unpack("!II", request[:8])


    #EXCHANGE_ID, NFS4_OK
    response += struct.pack("!II", 42, 0)
    #clientid needs to be unique, 64 bit. RFC5661-2.4
    clientid = os.urandom(8)
    response += clientid
    #seqid, flags, state_protect
    response += struct.pack("!III", 0, 1<<16|1, 0)
    #minor id
    response += struct.pack("!d", 0)
    #major ID + padding (hardcoded)
    majorid = "PyPXE"
    response += struct.pack("!I", 5)
    response += majorid+"\x00\x00\x00"
    #scope
    response += struct.pack("!I", 5)
    response += majorid+"\x00\x00\x00"
    #eir_erver_impl_id
    response += struct.pack("!I", 0)

    #needed for caching
    client['seqid'] = [1,response]

    state[clientid] = client
    return request, response
nfs_opnum4_append(EXCHANGE_ID, 42)

def CREATE_SESSION(request, response, state):
    '''

    '''
    clientid = request[:8]
    request = request[8:]

    [sequenceid] = struct.unpack("!I", request[:4])
    request = request[4:]

    [flags] = struct.unpack("!I", request[:4])
    request = request[4:]

    fore_attrs = struct.unpack("!IIIIIII", request[:28])
    request = request[28:]
    back_attrs = struct.unpack("!IIIIIII", request[:28])
    request = request[28:]

    [callback] = struct.unpack("!I", request[:4])
    request = request[4:]

    #AUTH_SYS - THIS MAY BREAK
    [unknown, flavor, stamp] = struct.unpack("!III", request[:12])
    request = request[12:]

    [machinelen] = struct.unpack("!I", request[:4])
    request = request[4:]
    machinename = request[:machinelen]
    request = request[machinelen+machinelen%4:]

    [uid, gid] = struct.unpack("!II", request[:8])
    request = request[8:]

    error = 0
    if clientid not in state.keys():
        #NFS4ERR_STALE_CLIENTID
        error = 10022
        #Section 15.1
    if sequenceid == state[clientid]['seqid'][0]:
        #Cache
        return request, state[clientid]['seqid'][1]
    if sequenceid > state[clientid]['seqid'][0]+1:
        #NFS4ERR_SEQ_MISORDERED
        error = 10063

    sessid = os.urandom(16)

    state[clientid]['sessid'] = sessid

    #CREATE_SESSION, Error
    response += struct.pack("!II", 43, error)
    response += sessid
    response += struct.pack("!I", sequenceid)
    #not CREATE_SESSION4_FLAG_PERSIST or CREATE_SESSION4_FLAG_CONN_BACK_CHAN
    response += struct.pack("!I", 0)
    response += struct.pack("!IIIIIII", *fore_attrs)
    response += struct.pack("!IIIIIII", *back_attrs)

    if not error:
        state[clientid]['seqid'][0] += 1
        state[clientid]['seqid'][1] = response

    return request, response
nfs_opnum4_append(CREATE_SESSION, 43)

def DESTROY_SESSION(request, response, state):
    #44
    return
nfs_opnum4_append(DESTROY_SESSION, 44)

def FREE_STATEID(request, response, state):
    #45
    return
nfs_opnum4_append(FREE_STATEID, 45)

def LAYOUTCOMMIT(request, response, state):
    #49
    return
nfs_opnum4_append(LAYOUTCOMMIT, 49)

def SECINFO_NO_NAME(request, response, state):
    #52
    return
nfs_opnum4_append(SECINFO_NO_NAME, 52)

def SEQUENCE(request, response, state):
    '''
    The SEQUENCE operation is used by the server to implement session request
    control and the reply cache semantics.
        - RFC5661-18.46.3
    '''
    sessid = request[:16]
    request = request[16:]
    [seqid,
    slotid,
    highest_slotid,
    cachethis] = struct.unpack("!IIII", request[:16])
    request = request[16:]

    try:
        clientid = [i for i in state if state[i]['sessid'] == sessid][0]
    except IndexError:
        #We don't have the client id.
        print "INDEXERROR"
        return request, response

    #Retry and cached?
    if seqid == state[clientid]['seqid'][0] and state[clientid]['seqid'][1]:
        return request, state[clientid]['seqid'][1]

    response += struct.pack("!II", 53, 0)
    response += sessid
    response += struct.pack("!IIIII",
            seqid,
            slotid,
            highest_slotid,
            highest_slotid,
            0)

    #New request, or not cached.
    #would be handy to have operation count here, this is a workaround
    while request:
        print repr(request)
        [op] = struct.unpack("!I", request[:4])
        request = request[4:] #functions know who they are
        print "\t", op, nfs_opnum4[op].__name__
        #Functions always append to response. Refactor?
        request, response = nfs_opnum4[op](request, response, state)

    return request, response
nfs_opnum4_append(SEQUENCE, 53)

def SET_SSV(request, response, state):
    #54
    return
nfs_opnum4_append(SET_SSV, 54)

def TEST_STATEID(request, response, state):
    #55
    return
nfs_opnum4_append(TEST_STATEID, 55)

def DESTROY_CLIENTID(request, response, state):
    '''
    If there are sessions (both idle and non-idle), opens, locks, delegations,
    layouts, and/or wants (Section 18.49) associated with the unexpired lease of
    the client ID, the server MUST return NFS4ERR_CLIENTID_BUSY.
        - RFC5661-18.50.3
    '''
    clientid = request[:8]
    request = request[8:]
    try:
        del state[clientid]
    except:
        pass
    #DESTROY_CLIENTID, NFS4_OK
    response += struct.pack("!II", 57, 0)

    return request, response
nfs_opnum4_append(DESTROY_CLIENTID, 57)

def RECLAIM_COMPLETE(request, response, state):
    '''
    A RECLAIM_COMPLETE operation is used to indicate that the client has
    reclaimed all of the locking state that it will recover, when it is
    recovering state due to either a server restart or the transfer of a file
    system to another server.
        - RFC5661-18.51.3
    '''
    rca_one_fs = struct.unpack("!I", request[:4])
    request = request[4:]
    #Not using this (yet?)
    response += struct.pack("!II", 58, 0)
    response += struct.pack("!I", 0)

    return request, response
nfs_opnum4_append(RECLAIM_COMPLETE, 58)
