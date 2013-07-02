import socket, struct, sys, msgpack, threading

_PORT = 33333
_MULTICAST_GROUP_NAME = '224.0.0.1'
_MULTICAST_GROUP = socket.inet_aton(_MULTICAST_GROUP_NAME)

class NSDServer():
	def __init__(self):
		self.services = {}
		self._threads = []
		self._stop_event = threading.Event()
		self._service_lock = threading.Lock()

	def add_service(self, name, port, features=None):
		with self._service_lock:
			self.services[name] = {"features": features, "port": port}

	def start(self):
		ip_addresses = socket.gethostbyname_ex('')[2]
		ip_address = ip_addresses[0]
		ip_address = "" # XXX

		thread = threading.Thread(target=self._listening_thread, args=(ip_address,))
		self._threads.append(thread)
		thread.start()

	def stop(self):
		print "shutdown signal received"
		self._stop_event.set()
		for thread in self._threads:
			thread.join()

	def _listening_thread(self, ip_address):
		# Create the socket
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
		sock.settimeout(1)
		# Bind to the server address
		sock.bind((ip_address, _PORT))

		# Tell the operating system to add the socket to the multicast group
		# on all interfaces.
		if (ip_address == ''):
			mreq = struct.pack('4sL', _MULTICAST_GROUP, socket.INADDR_ANY)
			sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
		else:
			iface = socket.inet_aton(ip_address) # listen for multicast packets on this interface.
			sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, _MULTICAST_GROUP+iface)

		# Receive/respond loop
		print "waiting to receive discovery request on group %s iface %s" % (_MULTICAST_GROUP_NAME, ip_address)
		while True:
			if self._stop_event.is_set():
				break
			try:
				data, address = sock.recvfrom(4096)
			except socket.timeout:
				continue
			print 'received %s bytes from %s' % (len(data), address)
			msg = msgpack.unpackb(data)
			service_name = msg["service"]
			with self._service_lock:
				service = self.services.get(service_name)
			if service:
				print 'sending discovery response to', address
				sock.sendto(msgpack.packb({"service": "GM", "port": service["port"]}), address)
