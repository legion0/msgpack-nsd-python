from msgpacknsd import NSDServer
import time, socket

machine_name = socket.gethostbyaddr(socket.gethostname())[0]

server = NSDServer()
server.add_service("GM", 35202, extra_info={"machine_name": machine_name})
server.start()

time.sleep(20)

server.stop()