import signal
import socket
import threading

class Server():

	def __init__(self, config):
		# Force shutdown
		signal.signal(signal.SIGINT, self.shutdown)

		# Creation
		self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		# Reusing the same port
		self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

		#Binding part
		self.serverSocket.bind((config['HOST_NAME'], config['BIND_PORT']))

		# Become a server socket
		self.serverSocket.listen(20)
		self.__clients = {}

		self.clientNames = {}
		self.clientNum = 0


		# Continuos loop for incoming connections
		while True:
			
			# Establishing connection with socket
			(clientSocket, client_address) = self.serverSocket.accept()

			# Handling this client to a new thread
			th = threading.Thread(name = self._getClientName(client_address), target = self.proxy_thread, args = (clientSocket, client_address, config))
			th.setDaemon(True)
			
			th.start()

		self.serverSocket

	def proxy_thread(self, clientSocket, client_address, config):
			# Obtaining request
			req = clientSocket.recv(config['MAX_REQUEST_LEN'])
			str_req = str(req)

			# String parsing
			url = str_req.split('\n')[0].split(' ')[1]
			print(url)

			#removing the http part
			http_pos = url.find("://")
			if http_pos != -1:
				url = url[(http_pos+3):]

			# Port number from the request
			port_pos = url.find(":")

			try:     
				port_num = int(url[(port_pos+1):]) 
			except:     
				port_num = 80

			webserver = url[:port_pos]

			#Establishing conn betweem proxy server and the requested server
			proxy_client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			proxy_client_sock.settimeout(config['CONNECTION_TIMEOUT'])
			proxy_client_sock.connect((webserver,port_num))
			proxy_client_sock.sendall(req)

			#Redirecting data from server to the client
			while True:
				data = proxy_client_sock.recv(config['MAX_REQUEST_LEN'])
				print(data)
				if (len(data) > 0):
					clientSocket.send(data)
				else:
					break



	def _getClientName(self, addr):
		if addr not in self.clientNames.keys():
			self.clientNum += 1
			self.clientNames[addr] = str(self.clientNum)
		return self.clientNames[addr]

	def shutdown(self):
		print("Server is now closing")
		print("Forcefully closing all currently active threads")

		for i in threading.enumerate():
			i.join()

		exit(0)


config = {'HOST_NAME': '127.0.0.1', 
		  'BIND_PORT': 20100,
		  'MAX_REQUEST_LEN': 100000,
		  'CONNECTION_TIMEOUT': 20
		 }
server = Server(config)