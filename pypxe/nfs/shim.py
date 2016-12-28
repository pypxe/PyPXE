import sys
import logging
from pypxe import helpers
import multiprocessing
import threading
import time

sys_logger = logging.getLogger('PyPXE')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s %(message)s')
handler.setFormatter(formatter)
sys_logger.addHandler(handler)
sys_logger.setLevel(logging.INFO)

try:
        pipelock = multiprocessing.Lock()
        portmapperend, otherend = multiprocessing.Pipe()

        import portmapper
        portmapper_logger = helpers.get_child_logger(sys_logger, 'NFS.PORTMAPPER')
        portmapperd = portmapper.PORTMAPPERD(logger = portmapper_logger, mode_debug = True, pipelock = pipelock, pipe = portmapperend)
        portmapperdthread = threading.Thread(target = portmapperd.listen)
        portmapperdthread.daemon = True
        portmapperdthread.start()

        import mount
        mount_logger = helpers.get_child_logger(sys_logger, 'NFS.MOUNT')
        mountd = mount.MOUNTD(logger = mount_logger, mode_debug = True, pipelock = pipelock, pipe = otherend)
        mountdthread = threading.Thread(target = mountd.listen)
        mountdthread.daemon = True
        mountdthread.start()

        import nfs
        nfs_logger = helpers.get_child_logger(sys_logger, 'NFS.NFS')
        nfsd = nfs.NFSD(logger = nfs_logger, mode_debug = True, pipelock = pipelock, pipe = otherend)
        nfsdthread = threading.Thread(target = nfsd.listen)
        nfsdthread.daemon = True
        nfsdthread.start()

        while all(map(lambda x:x.isAlive(), [portmapperdthread, mountdthread, nfsdthread])):
            time.sleep(1)
except KeyboardInterrupt:
    sys.exit('\nShutting down...')
