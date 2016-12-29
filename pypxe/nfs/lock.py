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
    def __init__(self, **server_settings):
        # should be swappable for real rpcbind
        self.mode_verbose = server_settings.get('mode_verbose', False) # verbose mode
        self.mode_debug = server_settings.get('mode_debug', False) # debug mode
        self.logger = server_settings.get('logger', None)

        # setup logger
        if self.logger == None:
            self.logger = logging.getLogger('LOCK.{0}'.format(self.PROTO))
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        if self.mode_debug:
            self.logger.setLevel(logging.DEBUG)
        elif self.mode_verbose:
            self.logger.setLevel(logging.INFO)
        else:
            self.logger.setLevel(logging.WARN)

        self.rpcnumber = 100021
        # we only need to keep track of our own program
        self.programs = {self.rpcnumber: programs.programs[self.rpcnumber]}

        self.logger.info("Started")

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

class LOCKDTCP(LOCK):
    def __init__(self, **server_settings):
        LOCK.__init__(self, **server_settings)
        self.PROTO = "TCP"
        # find out what port it should be listening on
        port = server_settings.get("port", 4045)
        # address can be passed to here from cli, and also to portmapper for bind addr
        addr = ""
        # prog, vers, proto, port
        self.registerPort(self.rpcnumber, 4, RPC.IPPROTO.IPPROTO_TCP4, port)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((addr, port))
        self.sock.listen(4)

class LOCKDUDP(LOCK):
    def __init__(self, **server_settings):
        LOCK.__init__(self, **server_settings)
        self.PROTO = "UDP"
        port = server_settings.get("port", 4045)
        # address can be passed to here from cli, and also to portmapper for bind addr
        addr = ""
        # prog, vers, proto, port
        self.registerPort(self.rpcnumber, 4, RPC.IPPROTO.IPPROTO_UDP4, port)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((addr, port))

class LOCKD:
    def __init__(self, **server_settings):
        self.logger = server_settings.get('logger', None)
        tcp_settings = server_settings.copy()
        tcp_settings["logger"] = helpers.get_child_logger(self.logger, "TCP")
        TCP = LOCKDTCP(**tcp_settings)

        udp_settings = server_settings.copy()
        udp_settings["logger"] = helpers.get_child_logger(self.logger, "UDP")
        UDP = LOCKDUDP(**udp_settings)

        self.TCP = threading.Thread(target = TCP.listen)
        self.TCP.daemon = True
        self.UDP = threading.Thread(target = UDP.listen)
        self.UDP.daemon = True

    def listen(self):
        self.TCP.start()
        self.UDP.start()
        while all(map(lambda x: x.isAlive(), [self.TCP, self.UDP])):
            time.sleep(1)
