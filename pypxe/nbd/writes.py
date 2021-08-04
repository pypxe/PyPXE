import io
from .. import helpers

class COW:
    def basepages(self, offset, length):
        # basepages is (page base addr, inter page offset, length of data in page)
        # it's unlikely we'll ever need sub 4096 reads, but just in case
        basepages = []

        # first chunk, not necessarily at page boundary
        basepages.append((offset - (offset % 4096), offset % 4096, 4096 - (offset % 4096)))
        length -= 4096 - (offset % 4096)
        offset += 4096

        # all following FULL chunks, definite page boundary and full size
        while length >= 4096:
            basepages.append((offset, 0, 4096))
            length -= 4096
            offset += 4096

        # final non-full chunk, definite offset, variable length
        if length > 0:
            basepages.append((offset, 0, length))

        return basepages

    def read(self, offset, length):
        basepages = self.basepages(offset, length)

        # this probably wants to be 2nd debug level
        self.logger.debug('{0} reading {1} bytes from {2}. Pages: {3}'.format(self.addr, length, hex(offset), len(basepages)))

        data = ''
        for major, minor, length in basepages:
            if major in self.pages:
                # major is the nth page in the file
                off = self.pages.index(major)
                self.fh.seek(off * 4096 + minor)
                data += self.fh.read(length)
            else:
                # This is a race condition. If another thread seeks after we've
                # seeked, but before we read, the seek is changed and the data
                # is wrong.
                # Lock is shared between all clients. Only applies to imagefd,
                # self.fd is unique and per client.
                self.seek_lock.acquire()
                self.imagefd.seek(major + minor)
                data += self.imagefd.read(length)
                self.seek_lock.release()
        return data

    def write(self, offset, data):
        basepages = self.basepages(offset, len(data))

        # this probably wants to be 2nd debug level
        self.logger.debug('{0} writing {1} bytes to {2}. Pages: {3}'.format(self.addr, len(data), hex(offset), len(basepages)))

        for major, minor, length in basepages:
            if major in self.pages:
                # we already have a copied page, so we can just overwrite it
                self.fh.seek(major + minor)
                self.fh.write(data[:length])
                data = data[length:]
            else:
                # we don't have this page, so copy it first. then add to the list
                self.seek_lock.acquire()

                # on the page boundary
                self.imagefd.seek(major)
                cpdata = self.imagefd.read(4096)
                self.seek_lock.release()

                # append to EOF
                self.fh.seek(0, 2)
                self.fh.write(cpdata)
                self.pages.append(major)

                # we've got a copy of the page now, we just need to write it
                off = self.pages.index(major)
                self.fh.seek(off * 4096 + minor)
                self.fh.write(data[:length])
                data = data[length:]

class DiskCOW(COW):
    def __init__(self, addr, imagefd, logger, seek_lock):
        # optional argset for disk diff path
        self.addr = addr
        self.imagefd = imagefd
        self.seek_lock = seek_lock
        self.logger = helpers.get_child_logger(logger, 'FS')
        self.logger.info('Copy-On-Write for {addr} in PyPXE_NBD_COW_{addr[0]}_{addr[1]}'.format(addr = addr))

        # never want readonly cow, also definitely creating file
        self.fh = open('PyPXE_NBD_COW_{addr[0]}_{addr[1]}'.format(addr = addr), 'w+b')

        # pages is a list of the addresses for which we have different pages
        # should all be multiples of 4096
        self.pages = []

class MemCOW(COW):
    def __init__(self, addr, imagefd, logger, seek_lock):
        self.addr = addr
        self.imagefd = imagefd
        self.seek_lock = seek_lock
        self.logger = helpers.get_child_logger(logger, 'FS')
        self.logger.info('Copy-On-Write for {0} in Memory'.format(addr))

        # BytesIO looks exactly the same as a file, perfect for in memory disk
        self.fh = io.BytesIO()

        # pages is a list of the addresses for which we have different pages
        # should all be multiples of 4096
        self.pages = []

class RW:
    def __init__(self, addr, imagefd, logger, seek_lock):
        self.addr = addr
        self.seek_lock = seek_lock
        self.imagefd = imagefd
        self.logger = helpers.get_child_logger(logger, 'FS')
        self.logger.debug('File for {0}'.format(addr))

    def read(self, offset, length):
        self.logger.debug('{0} reading {1} bytes from [{2}]'.format(self.addr, length, hex(offset)))
        self.seek_lock.acquire() # see COW.read() for lock reason
        self.imagefd.seek(offset)
        data = self.imagefd.read(length)
        self.seek_lock.release()
        return data

    def write(self, offset, data):
        self.logger.debug('{0} writing {1} bytes to {2}'.format(self.addr, len(data), hex(offset)))
        self.seek_lock.acquire()
        self.imagefd.seek(offset)
        self.imagefd.write(data)
        self.seek_lock.release()

def write(cow, in_mem):
    '''Class signatures are identical so we can transparently use either.'''
    if cow and in_mem:
        return MemCOW
    elif cow and not in_mem:
        return DiskCOW
    else:
        return RW
