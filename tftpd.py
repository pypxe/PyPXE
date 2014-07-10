import socket, struct, os
from collections import defaultdict

class TFTPD:
	'''
		This class implements a read-only TFTP server
		implemented from RFC1350 and RFC2348
	'''
	def __init__ ( self, ip = '0.0.0.0', port = 69, netbootDirectory = '.' ):
		self.ip = ip
		self.port = port
		self.sock = socket.socket( socket.AF_INET, socket.SOCK_DGRAM )
		self.sock.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
		self.sock.bind( ( self.ip, self.port ) )

		#key is (address, port) pair
		self.ongoing = defaultdict( lambda : { 'filename' : '', 'handle' : None, 'block' : 1, 'blksize' : 512 } )
		# Start in network boot file directory and then chroot, 
		# this simplifies target later as well as offers a slight security increase
		os.chdir ( netbootDirectory )
		os.chroot ( '.' )
	def filename( self, message ):
		'''
			The first null-delimited field after the OPCODE
			is the filename. This method returns the filename
			from the message.
		'''
		return message[2:].split( '\x00' )[0]

	def notFound( self, address ):
		'''
			short int 5 -> Error
			short int 1 -> File Not Found

			This method sends the message to the client
		'''
		response =  struct.pack( '!H', 5 ) #error code
		response += struct.pack( '!H', 1 ) #file not found
		response += 'File Not Found'
		self.sock.sendto( response, address )

	def sendBlock( self, address ):
		'''
			short int 3 -> Data Block
		'''
		descriptor = self.ongoing[ address ]
		#opcode 3 is DATA, also sent block number
		response =  struct.pack( '!H', 3 )
		response += struct.pack( '!H', descriptor[ 'block' ] )
		data = descriptor[ 'handle' ].read( descriptor[ 'blksize' ] )
		response += data
		self.sock.sendto( response, address )
		if len( data ) != descriptor[ 'blksize' ]:
			descriptor[ 'handle' ].close()
			print 'tftp://%s -> %s:%d' % ( descriptor[ 'filename' ], address[0], address[1] )
			self.ongoing.pop( address )
		else:
			descriptor[ 'block' ] += 1

	def read( self, address, message ):
		'''
		On RRQ OPCODE:
			file exists -> reply with file
			file does not exist -> reply with error
		'''
		filename = self.filename( message )
		if not os.path.exists( filename ):
			self.notFound( address )
			return
		self.ongoing[ address ][ 'filename' ] = filename
		self.ongoing[ address ][ 'handle' ] = open( filename, 'r' )
		options = message.split( chr( 0 ) )[ 3 : -1 ]
		options = dict( zip( options[0::2], options[1::2] ) )
		response = ''
		if 'blksize' in options:
			response += 'blksize\x00'
			response += options[ 'blksize' ]
			response += '\x00'
			self.ongoing[ address ][ 'blksize' ] = int( options[ 'blksize' ] )
		if 'tsize' in options:
			response += 'tsize\x00'
			response += str( os.path.getsize( self.ongoing[ address ][ 'filename' ] ) )
			response += '\x00'
		if response:
			response = struct.pack( '!H', 6 ) + response
			self.sock.sendto( response, address )
		self.sendBlock( address )

	def listen( self ):
		'''This method listens for incoming requests'''
		while True:
			message, address = self.sock.recvfrom( 1024 )
			opcode = struct.unpack( '!H', message[:2] )[0]
			if opcode == 1: #read the request
				 self.read( address, message )
			if opcode == 4:
				 if self.ongoing.has_key( address ):
					  self.sendBlock( address )
