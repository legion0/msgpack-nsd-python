from msgpacknsd import NSDServer
import time

server = NSDServer()
server.add_service("GM", 35202)
server.start()

time.sleep(100)

server.stop()