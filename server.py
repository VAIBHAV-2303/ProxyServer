'''
	Multi-threaded HTTP proxy server
'''

import requests
import signal
import socket
import threading
import time
import struct
from time import strftime, gmtime

class Server():

	def __init__(self, config, blocked):
		
		# Force shutdown
		signal.signal(signal.SIGINT, self.shutdown)

		# Creation
		self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

		# Reusing the same port
		self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

		# Binding part
		self.serverSocket.bind((config['HOST_NAME'], config['BIND_PORT']))

		# Become a server socket
		self.serverSocket.listen(10)

		self.clientNum = 0

		self.reqDict = {}
		self.Memory = {}

		# Continuos loop for incoming connections
		while 1:
			
			# Establishing connection with socket
			(clientSocket, client_address) = self.serverSocket.accept()
			
			# Handling this client to a new thread
			th = threading.Thread(name = self._getClientName(client_address), target = self.proxy_thread, args = (clientSocket, config, blocked))
			th.setDaemon(True)
			th.start()

		self.serverSocket.close()

	def proxy_thread(self, clientSocket, config, blocked):
		
		# Obtaining request
		req = clientSocket.recv(config['MAX_REQUEST_LEN'])
		str_req = str(req)

		# String parsing
		try:
			url = str_req.split('\n')[0].split(' ')[1]
		except:
			exit(0)

		# Removing the http part
		http_pos = url.find("://")
		if http_pos != -1:
			url = url[(http_pos+3):]

		# Blocking blacklisted
		try:
			ipaddr = socket.gethostbyname(url.split('/')[0])
			if ipaddr in blocked:
				clientSocket.send(str.encode('Page blocked'))
				exit(0)
		except Exception as e:
			pass


		# If response modified or not
		try:
			resp = requests.get(url = url, headers = {'If-Modified-Since': strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime(0))})
			sc = resp.status_code
		except:
			try:
				resp = requests.get(url = 'http://'+url, headers = {'If-Modified-Since': strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime(0))})
				sc = resp.status_code
			except:
				sc = 200

		if url in self.Memory.keys() and sc == 304:
			# If exists in cache
			if time.time() - self.reqDict[url][1] > 300:
				self.reqDict[url][0] = 0
			else:
				self.reqDict[url][0] += 1

			# Sending from cache
			clientSocket.send(self.Memory[url])

		else:
			# Doesn't exist in cache
			if url in self.reqDict.keys():
				if time.time() - self.reqDict[url][1] > 300:
					self.reqDict[url][0] = 0
				else:
					self.reqDict[url][0] += 1
			else:
				self.reqDict[url] = [1, time.time()]

			# Port number from the request
			port_pos = url.find(":")
			try:
				port_num = int(url[(port_pos+1):])
			except:
				port_num = 80

			webserver = url[:port_pos]

			# Establishing conn betweem proxy server and the requested server
			proxy_client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			proxy_client_sock.settimeout(config['CONNECTION_TIMEOUT'])
			try:
				proxy_client_sock.connect((webserver,port_num))
			except:
				exit(0)
			proxy_client_sock.sendall(req)

			# Redirecting data from server to the client
			temp = b''
			while True:
				try:
					data = proxy_client_sock.recv(config['BUFFER_SIZE'])
				except:
					break

				if len(data) > 0:
					temp += data
					clientSocket.send(data)
				else:
					break

			try:
				# Inserting in cache
				if self.reqDict[url][0] >= 300:
					if len(self.Memory) == 300:
						self.Memory.pop(url, None)	
					self.Memory[url] = temp
			except:
				pass

		exit(0)

	# Serially giving numbers to client requests
	def _getClientName(self, addr):
		self.clientNum += 1
		return self.clientNum

	# Force shutting of server
	def shutdown(self, signum, frame):
		print("Server is now closing")
		print("Forcefully closing all currently active threads")
		exit(0)





config = {'HOST_NAME': '127.0.0.1', 
		  'BIND_PORT': 20100,
		  'MAX_REQUEST_LEN': 1000,
		  'BUFFER_SIZE': 1024*1024,
		  'CONNECTION_TIMEOUT': 20
		 }


# Generating the blocked ip addresses list
blocked = []
f = open('blacklist.txt', 'r')

for l in f:
	# Converting CIDR to IpAddresses
	(ip, cidr) = l.split('/')
	cidr = int(cidr) 
	host_bits = 32 - cidr
	i = struct.unpack('>I', socket.inet_aton(ip))[0]
	start = (i >> host_bits) << host_bits
	end = start | ((1 << host_bits))
	end += 1
	
	for i in range(start, end):
		blocked.append(socket.inet_ntoa(struct.pack('>I',i)))

server = Server(config, blocked)