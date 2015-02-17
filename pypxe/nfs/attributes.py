import struct
import os
#This is used in various places (GETATTR/READDIR), and is quite large
#So I've split it into a new file
#Huge benefit from extending this
#(See RFC5661 - 5.6/7 for details)
#Implemented = REQUIRED & Kernel requested
class Attributes:
    def __init__(self, fh, state, req):
        self.clientid = state['current']
        self.fh = state[self.clientid]['fh']
        self.path = state['fhs'][fh]
        self.pathstat = os.stat(self.path)
        self.attr_pos = self.extractbits(req)
        self.respbitmask = self.packbits([attr for attr in self.attr_pos if attr in self.attributes])
        self.packedattr = ''.join([self.attributes[attr](self) for attr in self.attr_pos if attr in self.attributes])
        self.packedattrlen = len(self.packedattr)

    def extractbits(self, attr_req):
        offset = 0
        attr_pos = []
        for attr in attr_req:
            attr_pos += [i+offset for i,x in enumerate(bin(attr)[2:][::-1]) if int(x)]
            offset += 32
        return attr_pos

    def packbits(self, bitmask):
        '''
        Takes a list of bit offsets, converts them to packed integers
        '''
        #Create one big long with the bitmask
        bitmaskint = reduce(lambda x,y:x|1<<y, bitmask, 0)
        #convert into 32bit ints
        ints = []
        while bitmaskint:
            ints.append(bitmaskint&0xffffffff)
            bitmaskint >>= 32
        #pack with prefixed length
        return struct.pack("!I%dI" % len(ints), len(ints), *ints)

    attributes = {}

    #Bitmask length, Attributes. RFC5661-5.6
    attributes[0] = lambda self:self.packbits(self.attributes.keys())

    #RFC3010-18: enum nfs_ftype4
    #bitwise OR stat.S_IF* 61440
    #{stat.S_IFSOCK : NF4SOCK,
    #stat.S_IFLNK : NF4LNK,
    #stat.S_IFBLK : NF4BLK,
    #stat.S_IFREG : NF4REG,
    #stat.S_IFDIR : NF4DIR,
    #stat.S_IFCHR : NF4CHR,
    #stat.S_IFIFO : NF4FIFO}
    #Returns the nfs_ftype4
    attributes[1] = lambda self:struct.pack("!I",{49152:6, 40960:5, 32768:1, 24576:3, 16384:2, 8192:4, 4096:7}[self.pathstat.st_mode&61440])

    #FH4_VOLATILE_ANY "The filehandle may expire at any time" - RFC5661-4.2.3
    attributes[2] = lambda self:struct.pack("!I", 2)

    #change, last modified works, st_mtime returns float, so might as well use it all
    attributes[3] = lambda self:struct.pack("!d", self.pathstat.st_mtime)

    #size, uint64
    attributes[4] = lambda self:struct.pack("!Q", self.pathstat.st_size)

    #support hard links?
    attributes[5] = lambda self:struct.pack("!I", 1)

    #support symbolic links?
    attributes[6] = lambda self:struct.pack("!I", 1)

    #has named attribs?
    attributes[7] = lambda self:struct.pack("!I", 1)

    #major/minor uint64 filesystem id, is this okay (kernel gives these vals)?
    attributes[8] = lambda self:struct.pack("!qq", 0, 0)

    #handles are unique?
    attributes[9] = lambda self:struct.pack("!I", 1)

    #Lease time. Documentation sparse, 1hr
    attributes[10] = lambda self:struct.pack("!I", 3600)

    #Error from attrib readdir
    attributes[11] = lambda self:struct.pack("!I", 0)

    #object filehandle
    attributes[19] = lambda self:struct.pack("!I", 128)+self.fh

    #number uniquely identifying file on filesystem. Not perfect but should work.
    attributes[20] = lambda self:self.fh[:8]

    #Mode. Only want bottom 0xfff mask for perms
    attributes[33] = lambda self:struct.pack("!I", self.pathstat.st_mode&0xfff)

    #Number of hard links
    attributes[35] = lambda self:struct.pack("!I", self.pathstat.st_nlink)

    #Owner name. This is what the kernel did. could do pwd.getpwuid(self.pathstat.st_uid).pw_name
    attributes[36] = lambda self:struct.pack("!Icbbb", 1, "0", 0, 0, 0)

    #Group name. See 36
    attributes[37] = lambda self:struct.pack("!Icbbb", 1, "0", 0, 0, 0)

    #Major/Minor device number. useless if not BLK or CHR
    attributes[41] = lambda self:struct.pack("!II", os.major(self.pathstat.st_dev), os.minor(self.pathstat.st_dev))

    #used size, uint64
    attributes[45] = lambda self:struct.pack("!Q", self.pathstat.st_size)

    #Time accessed. Should also send nanoseconds, but tricky to access
    attributes[47] = lambda self:struct.pack("!QI", self.pathstat.st_atime, 0)

    #Time metadata changed
    attributes[52] = lambda self:struct.pack("!QI", self.pathstat.st_ctime, 0)

    #Time modified
    attributes[53] = lambda self:struct.pack("!QI", self.pathstat.st_mtime, 0)

    #unsure on this one, copying attributes[1]
    attributes[75] = lambda self:struct.pack("!I",{49152:6, 40960:5, 32768:1, 24576:3, 16384:2, 8192:4, 4096:7}[self.pathstat.st_mode&61440])
