import io

class COW:
    def basepages(self, offset, length):
        # basepages is (page base addr, inter page offset, length of data in page)
        # it's unlikely we'll ever need sub 4096 reads, but just in case.
        # I have observed sub 4096 writes so that justifies it.
        basepages = []

        # first chunk, not necessarily at page boundary
        basepages.append((offset - (offset % 4096), offset % 4096, 4096 - (offset % 4096)))
        length -= 4096 - (offset % 4096)
        offset += 4096

        # all following FULL chunks. definate page boundary and full size
        while length >= 4096:
            basepages.append((offset, 0, 4096))
            length -= 4096
            offset += 4096

        # final non-full chunk, definate offset, variable length
        if length > 0:
            basepages.append((offset, 0, length))

        return basepages

    def read(self, offset, length):
        basepages = self.basepages(offset, length)

        # this probably wants to be 2nd debug level
        self.logger.debug('%s reading %d bytes from %s. Pages: %s', self.addr, length, hex(offset), len(basepages))

        data = ""
        for major, minor, length in basepages:
            if major in self.pages:
                # major is the nth page in the file
                off = self.pages.index(major)
                self.fh.seek(off*4096 + minor)
                data += self.fh.read(length)
            else:
                # This is a race condition. If another thread seeks after we've
                # seeked, but before we read, the seek is changed and the data
                # is wrong.
                # Lock is shared between all clients. Only applies to imagefd,
                # self.fd is unique and per client.
                self.seeklock.acquire()
                self.imagefd.seek(major + minor)
                data += self.imagefd.read(length)
                self.seeklock.release()
        return data

    def write(self, offset, data):
        basepages = self.basepages(offset, len(data))

        # this probably wants to be 2nd debug level
        self.logger.debug('%s writing %d bytes to %s. Pages: %s', self.addr, len(data), hex(offset), len(basepages))

        for major, minor, length in basepages:
            if major in self.pages:
                # we already have a copied page, so we can just overwrite it
                self.fh.seek(major + minor)
                self.fh.write(data[:length])
                data = data[length:]
            else:
                # we don't have this page, so copy it first. then add to the list
                self.seeklock.acquire()
                # on the page boundary
                self.imagefd.seek(major)
                cpdata = self.imagefd.read(4096)
                self.seeklock.release()
                # append to EOF
                self.fh.seek(0, 2)
                self.fh.write(cpdata)
                self.pages.append(major)
                # we've got a copy of the page now, we just need to write it
                off = self.pages.index(major)
                self.fh.seek(off*4096 + minor)
                self.fh.write(data[:length])
                data = data[length:]

class DiskCOW(COW):
    def __init__(self, addr, imagefd, logger, seeklock):
        # Optional argset for:
        #   disk diff path
        self.addr = addr
        self.imagefd = imagefd
        self.seeklock = seeklock
        self.logger = logger.getChild('FS')
        self.logger.debug('Copy-On-Write for %s in PyPXE_NBD_COW_%s_%s', addr, *addr)

        #never want readonly cow, also definately creating file
        self.fh = open('PyPXE_NBD_COW_%s_%s' % addr, 'w+b')
        # pages is a list of the addresses for which we have different pages
        # should all be multiples of 4096.
        self.pages = []

class MemCOW(COW):
    def __init__(self, addr, imagefd, logger, seeklock):
        self.addr = addr
        self.imagefd = imagefd
        self.seeklock = seeklock
        self.logger = logger.getChild('FS')
        self.logger.debug('Copy-On-Write for %s in Memory', addr)

        #BytesIO looks exactly the same as a file, perfect for in memory disk
        self.fh = io.BytesIO()
        # pages is a list of the addresses for which we have different pages
        # should all be multiples of 4096.
        self.pages = []

class RW:
    def __init__(self, addr, imagefd, logger, seeklock):
        self.addr = addr
        self.seeklock = seeklock
        self.imagefd = imagefd
        self.logger = logger.getChild('FS')
        self.logger.debug('File for %s', addr)

    def read(self, offset, length):
        # this probably wants to be 2nd debug level
        self.logger.debug('%s reading %d bytes from %s', self.addr, length, hex(offset))
        # see COW.read() for lock reason
        self.seeklock.acquire()
        self.imagefd.seek(offset)
        data = self.imagefd.read(length)
        self.seeklock.release()
        return data

    def write(self, offset, data):
        # this probably wants to be 2nd debug level
        self.logger.debug('%s writing %d bytes to %s', self.addr, len(data), hex(offset))
        self.seeklock.acquire()
        self.imagefd.seek(offset)
        self.imagefd.write(data)
        self.seeklock.release()

def write(cow, inmem):
    '''Class signatures are identical so we can transparently
       use either.'''
    if cow and inmem:
        return MemCOW
    elif cow and not inmem:
        return DiskCOW
    else:
        return RW
