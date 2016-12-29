import rpcbind
import logging
from pypxe import helpers
import socket
import threading
import time
import struct
import programs

class RPC(rpcbind.RPCBase):
    LOCK_PROC = programs.RPC.LOCK_PROC
    class IPPROTO:
        IPPROTO_TCP4 = 6
        IPPROTO_UDP4 = 17

class LOCK(rpcbind.RPCBIND):
    def process(self, **arguments):
        LOCK_PROCS = {
            RPC.LOCK_PROC.NLMPROC4_NULL: self.NULL,
            RPC.LOCK_PROC.NLMPROC4_TEST: self.TEST,
            RPC.LOCK_PROC.NLMPROC4_LOCK: self.LOCK,
            RPC.LOCK_PROC.NLMPROC4_CANCEL: self.CANCEL,
            RPC.LOCK_PROC.NLMPROC4_UNLOCK: self.UNLOCK,
            RPC.LOCK_PROC.NLMPROC4_GRANTED: self.GRANTED,
            RPC.LOCK_PROC.NLMPROC4_TEST_MSG: self.TEST_MSG,
            RPC.LOCK_PROC.NLMPROC4_LOCK_MSG: self.LOCK_MSG,
            RPC.LOCK_PROC.NLMPROC4_CANCEL_MSG: self.CANCEL_MSG,
            RPC.LOCK_PROC.NLMPROC4_UNLOCK_MSG: self.UNLOCK_MSG,
            RPC.LOCK_PROC.NLMPROC4_GRANTED_MSG: self.GRANTED_MSG,
            RPC.LOCK_PROC.NLMPROC4_TEST_RES: self.TEST_RES,
            RPC.LOCK_PROC.NLMPROC4_LOCK_RES: self.LOCK_RES,
            RPC.LOCK_PROC.NLMPROC4_CANCEL_RES: self.CANCEL_RES,
            RPC.LOCK_PROC.NLMPROC4_UNLOCK_RES: self.UNLOCK_RES,
            RPC.LOCK_PROC.NLMPROC4_GRANTED_RES: self.GRANTED_RES,
            RPC.LOCK_PROC.NLMPROC4_SHARE: self.SHARE,
            RPC.LOCK_PROC.NLMPROC4_UNSHARE: self.UNSHARE,
            RPC.LOCK_PROC.NLMPROC4_NM_LOCK: self.NM_LOCK,
            RPC.LOCK_PROC.NLMPROC4_FREE_ALL: self.FREE_ALL
        }
        LOCK_PROCS[arguments["proc"]](**arguments)

    def NULL(**arguments):
        self.logger.info("NULL")
        pass
    def TEST(**arguments):
        self.logger.info("TEST")
        pass
    def LOCK(**arguments):
        self.logger.info("LOCK")
        pass
    def CANCEL(**arguments):
        self.logger.info("CANCEL")
        pass
    def UNLOCK(**arguments):
        self.logger.info("UNLOCK")
        pass
    def GRANTED(**arguments):
        self.logger.info("GRANTED")
        pass
    def TEST_MSG(**arguments):
        self.logger.info("TEST_MSG")
        pass
    def LOCK_MSG(**arguments):
        self.logger.info("LOCK_MSG")
        pass
    def CANCEL_MSG(**arguments):
        self.logger.info("CANCEL_MSG")
        pass
    def UNLOCK_MSG(**arguments):
        self.logger.info("UNLOCK_MSG")
        pass
    def GRANTED_MSG(**arguments):
        self.logger.info("GRANTED_MSG")
        pass
    def TEST_RES(**arguments):
        self.logger.info("TEST_RES")
        pass
    def LOCK_RES(**arguments):
        self.logger.info("LOCK_RES")
        pass
    def CANCEL_RES(**arguments):
        self.logger.info("CANCEL_RES")
        pass
    def UNLOCK_RES(**arguments):
        self.logger.info("UNLOCK_RES")
        pass
    def GRANTED_RES(**arguments):
        self.logger.info("GRANTED_RES")
        pass
    def SHARE(**arguments):
        self.logger.info("SHARE")
        pass
    def UNSHARE(**arguments):
        self.logger.info("UNSHARE")
        pass
    def NM_LOCK(**arguments):
        self.logger.info("NM_LOCK")
        pass
    def FREE_ALL(**arguments):
        self.logger.info("FREE_ALL")
        pass

class LOCKD(rpcbind.DAEMON):
    def __init__(self, **server_settings):
        self.logger = server_settings.get('logger', None)

        server_settings["rpcnumber"] = 100021
        server_settings["programs"] = {server_settings["rpcnumber"]: programs.programs[server_settings["rpcnumber"]]}

        tcp_settings = server_settings.copy()
        udp_settings = server_settings.copy()

        self.port = server_settings.get("port", 4045)
        # address can be passed to here from cli, and also to portmapper for bind addr
        self.addr = ""

        self.createTCP4Thread(LOCK, server_settings)
        self.createUDP4Thread(LOCK, server_settings)

    def listen(self):
        self.TCP4.start()
        self.UDP4.start()
        while all(map(lambda x: x.isAlive(), [self.TCP4, self.UDP4])):
            time.sleep(1)
