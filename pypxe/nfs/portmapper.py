import rpcbind
import struct
import time
import programs

def padtomultiple(string, boundary):
    while len(string) % boundary:
        string += "\x00"
    return string

class RPC(rpcbind.RPCBase, programs.RPC):
    pass

class PORTMAPPER(rpcbind.RPCBIND):
    autoregister = False
    def process(self, **arguments):
        PORTMAPPERPROCS = {
            RPC.PMAPPROC.NULL : self.NULL,
            RPC.PMAPPROC.SET : self.SET,
            RPC.PMAPPROC.UNSET : self.UNSET,
            RPC.PMAPPROC.GETADDR : self.GETADDR,
            RPC.PMAPPROC.DUMP : self.DUMP
        }
        PORTMAPPERPROCS[arguments["proc"]](**arguments)

    def NULL(self, **arguments):
        self.makeRPCHeader("", RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)
        pass

    def SET(self, body = None, **arguments):
        if arguments["vers"] in (2, 3):
            [
                program,
                version,
                protocol,
                port
            ] = struct.unpack("!IIII", body.read(4*4))
            protocol = RPC.IPPROTO.IPPROTO_TCP4 if protocol == 6 else RPC.IPPROTO.IPPROTO_UDP4
            self.logger.debug("SET for program {0} on port {1}/{2}".format(program, port, protocol))
            if program in self.programs:
                self.programs[program]["port"][protocol] = port
                self.programs[program]["address"][protocol] = "0.0.0.0"
            else:
                self.programs[program] = {}
                self.programs[program]["port"] = {}
                self.programs[program]["port"][protocol] = port
                self.programs[program]["version"] = [version]
                self.programs[program]["owner"] = "superuser"
                self.programs[program]["address"] = {}
                self.programs[program]["address"][protocol] = "0.0.0.0"
                self.makeRPCHeader(struct.pack("!I", int(True)), RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)
                pass
            self.makeRPCHeader(struct.pack("!I", int(True)), RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)

        elif arguments["vers"] == 4:
            [program, version, protocollen] = struct.unpack("!III", body.read(4*3))

            protocol = body.read(protocollen)
            # calculate and discard padding
            body.read((4 - (protocollen % 4))&~4)

            [addrlen] = struct.unpack("!I", body.read(4))
            addr = body.read(addrlen)
            body.read((4 - (addrlen % 4))&~4)

            if protocol.endswith('6'):
                # ::1.123.456
                ip = addr.split('.')[0]
                if ip == "::": ip += "1"
                port = reduce(lambda x, y: (x<<8) + int(y), addr.split('.')[1:], 0)
            else:
                # 0.0.0.0.123.456
                ip = '.'.join(addr.split('.')[:4])
                port = reduce(lambda x, y: (x<<8) + int(y), addr.split('.')[4:], 0)

            [ownerlen] = struct.unpack("!I", body.read(4))
            owner = body.read(ownerlen)
            body.read((4 - (ownerlen % 4))&~4)

            if owner not in ("0", "superuser"):
                self.makeRPCHeader(struct.pack("!I", int(True)), RPC.reply_stat.MSG_DENIED, RPC.reject_stat.AUTH_ERROR, **arguments)
                return

            if program in self.programs:
                self.programs[program]["port"][protocol] = port
                if version not in self.programs[program]["version"]:
                    self.programs[program]["version"].append(version)
                self.programs[program]["address"][protocol] = ip
                self.makeRPCHeader(struct.pack("!I", int(True)), RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)
            else:
                self.programs[program] = {}
                self.programs[program]["port"] = {}
                self.programs[program]["port"][protocol] = port
                self.programs[program]["version"] = [version]
                self.programs[program]["owner"] = owner if owner != "0" else "superuser"
                self.programs[program]["address"] = {}
                self.programs[program]["address"][protocol] = ip
                self.makeRPCHeader(struct.pack("!I", int(True)), RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)

            self.logger.debug("SET for program {0} on {1}/{2}".format(program, port, protocol))

    def UNSET(self, body = None, **arguments):
        if arguments["vers"] in (2, 3):
            [
                program,
                version,
                proto,
                port
            ] = struct.unpack("!IIII", body.read(4*4))
            self.logger.debug("UNSET for program {0} on port {1}/{2}".format(program, port, "tcp" if proto == 6 else "udp"))
            if program in self.programs:
                del self.programs[program]["address"][RPC.IPPROTO.IPPROTO_TCP4 if proto == 6 else RPC.IPPROTO.IPPROTO_UDP4]
                # only unset port if it's the last proto
                if not self.programs[program]["address"]:
                    self.programs[program]["port"] = 0
                self.makeRPCHeader(struct.pack("!I", int(True)), RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)
            else:
                self.makeRPCHeader(struct.pack("!I", int(True)), RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.PROG_UNAVAIL, **arguments)

        elif arguments["vers"] == 4:
            [program, protocollen] = struct.unpack("!II", body.read(4*2))

            protocol = body.read(protocollen)
            # calculate and discard padding
            body.read((4 - (protocollen % 4))&~4)

            [addrlen] = struct.unpack("!I", body.read(4))
            addr = body.read(addrlen)
            body.read((4 - (addrlen % 4))&~4)

            [ownerlen] = struct.unpack("!I", body.read(4))
            owner = body.read(ownerlen)
            body.read((4 - (ownerlen % 4))&~4)

            if owner not in ("0", "superuser"):
                self.makeRPCHeader(struct.pack("!I", int(True)), RPC.reply_stat.MSG_DENIED, RPC.reject_stat.AUTH_ERROR, **arguments)
                return

            self.logger.debug("UNSET for program {0}".format(program))

            if program in self.programs:
                if protocol and protocol != "\x00"*len(protocol):
                    del self.programs[program]["address"][RPC.IPPROTO.IPPROTO_TCP4 if protocol == "tcp" else RPC.IPPROTO.IPPROTO_UDP4]
                else:
                    self.programs[program]["address"] = {}
                # only unset port if it's the last proto
                if not self.programs[program]["address"]:
                    self.programs[program]["port"] = 0
                self.makeRPCHeader(struct.pack("!I", int(True)), RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)
            else:
                self.makeRPCHeader(struct.pack("!I", int(True)), RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)


    def GETADDR(self, body = None, **arguments):
        [
            program,
            version,
            proto,
            port
        ] = struct.unpack("!IIII", body.read(4*4))
        if program in self.programs and (RPC.IPPROTO.IPPROTO_UDP4 if proto == 17 else RPC.IPPROTO.IPPROTO_TCP4) in self.programs[program]["port"]:
            self.makeRPCHeader(
                    struct.pack("!I", self.programs[program]["port"][RPC.IPPROTO.IPPROTO_UDP4 if proto == 17 else RPC.IPPROTO.IPPROTO_TCP4]),
                    RPC.reply_stat.MSG_ACCEPTED,
                    RPC.accept_stat.SUCCESS,
                    **arguments)
        else:
            self.makeRPCHeader("", RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.PROG_UNAVAIL, **arguments)


    def DUMP(self, **arguments):
        mappings = []
        # only list enabled programs
        for program in self.programs:
            # sort by bind address. Makes the rpcinfo output look nicer
            for address in sorted(self.programs[program]["address"], key=lambda x:self.programs[program]["address"][x]):
                for version in self.programs[program]["version"]:
                    mapping = struct.pack(
                            "!II",
                            program,
                            version
                            )
                    if arguments["vers"] == 3:
                        protocol = padtomultiple(address, 4)
                        r_addr = padtomultiple("{address}.{port}".format(address = self.programs[program]["address"][address], port = self.programs[program]["port"][address]), 4)
                        owner = padtomultiple(self.programs[program]["owner"], 4)

                        # auto pad to 4 byte boundaries
                        mapping += struct.pack("!I", len(protocol)) + protocol
                        mapping += struct.pack("!I", len(r_addr)) + r_addr
                        mapping += struct.pack("!I", len(owner)) + owner

                    elif arguments["vers"] == 2:
                        if address.endswith("6"):
                            # can't show IPV6 address in v2 portmapper, so skip
                            continue
                        mapping += struct.pack("!I", 6 if address.startswith("tcp") else 17)
                        mapping += struct.pack("!I", self.programs[program]["port"][RPC.IPPROTO.IPPROTO_TCP4 if address.startswith("tcp") else RPC.IPPROTO.IPPROTO_UDP4])

                    mappings.append(mapping)

        # value follows == 0x00000001
        resp = struct.pack("!I", 1)
        resp += struct.pack("!I", 1).join(mappings)
        # no value follows == 0x00000000
        resp += struct.pack("!I", 0)
        self.makeRPCHeader(resp, RPC.reply_stat.MSG_ACCEPTED, RPC.accept_stat.SUCCESS, **arguments)

class PORTMAPPERD(rpcbind.DAEMON):
    def __init__(self, **server_settings):
        self.logger = server_settings.get('logger', None)

        server_settings["programs"] = programs.programs

        del server_settings["logger"]
        udp_settings = server_settings.copy()

        self.programs = server_settings["programs"]
        self.addr = self.programs[100000]["address"]["TCP4"]
        self.port = self.programs[100000]["port"]["TCP4"]

        self.createTCP4Thread(PORTMAPPER, server_settings)
        self.createUDP4Thread(PORTMAPPER, server_settings)

    def listen(self):
        self.TCP4.start()
        self.UDP4.start()
        while all(map(lambda x: x.isAlive(), [self.TCP4, self.UDP4])):
            time.sleep(1)
