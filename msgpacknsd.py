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

	def add_service(self, name, port, extra_info=None, features=()):
		response = {"service": name, "port": port}
		if extra_info:
			response["extra_info"] = extra_info
		service = {"name": name, "response": response, "features": features}
		with self._service_lock:
			self.services[name] = service

	def start(self):
		if sys.platform == "win32":
			ip_addresses = socket.gethostbyname_ex('')[2]
		else:
			ip_addresses = [""]
		for ip_address in ip_addresses:
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
			required_features = msg.get("features", [])
			with self._service_lock:
				service = self.services.get(service_name)
			if service:
				has_features = len(set(service["features"]) - set(required_features)) == 0
				if has_features:
					print 'sending discovery response to', address
					print service["response"]
					sock.sendto(msgpack.packb(service["response"]), address)
