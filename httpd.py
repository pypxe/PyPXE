import socket, struct, os

class HTTPD:
	'''This class implements a HTTP Server, limited to GET and HEAD, from RFC2616, RFC7230'''
	def __init__( self, ip = '0.0.0.0', port = 80, netbootDirectory = '.' ):
		self.sock = socket.socket( socket.AF_INET, socket.SOCK_STREAM )
		self.sock.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
		self.sock.bind( ( ip, port ) )
		self.sock.listen( 1 )
		os.chdir ( netbootDirectory ) #start in network boot file directory
	def handlereq( self, connection, addr ):
		'''Handle HTTP request'''
		request = connection.recv( 1024 )
		startline = request.split( '\r\n' )[0].split( '' )
		method = startline[0]
		target = startline[1]

		if not os.path.exists( target ) or not os.path.isfile( target ):
			status = '404 Not Found'
		elif method not in ( 'GET', 'HEAD' ):
			status = '501 Not Implemented'
		else:
			status = '200 OK'
		response = 'HTTP/1.1 %s\r\n' % status
		if status[:3] in ( '404', '501' ):
			#fail out
			connection.send( response )
			connection.close()
			return

		response += 'Content-Length: %d\r\n' % os.path.getsize( target )
		response += '\r\n'
		if method == 'HEAD':
			connection.send( response )
			connection.close()
			return

		handle = open( target )
		response += handle.read()
		handle.close()
		connection.send( response )
		connection.close()
		print 'http://%s -> %s:%d' % ( target, addr[0], addr[1] )

	def listen( self ):
		'''This method is the main loop that listens for requests'''
		while True:
			conn, addr = self.sock.accept()
			self.handlereq( conn, addr )