#!/usr/bin/python
import socket
import select
import time
import sys

buffer_size = 4096
delay = 0.0001
printer_mks = ('192.168.231.25', 8080)


curExtruder0Temp = 0
tgtExtruder0Temp = 0
curExtruder1Temp = 0
tgtExtruder1Temp = 0
curBedTemp = 0
tgtBedTemp = 0
progress = 0
current_file = "" # M994
file_loaded = False
printer_status = "idle" # also "printing"
firmware = None #M115 request
print_status = "idle" #(idle/started/paused/aborted/finished) (how we get aborted?..)

#elapsedPrintTime (hh:mm:ss)


updated = {}
updated['M997'] = 0 #(print status, cacheable, 5s)
updated['M105'] = 0 #(temperature, cacheable, 5s) also M991
updated['M27'] = 0 #(print progress, cacheable, 5s)
updated['M992'] = 0 #(elapsed print time, cacheable, 5s?)


class TheServer:
    server_list = []
    client_list = []
    printer_list = []
    prcon_time = 0
    prcon_state = 'offline' # also 'online' and 'transfer'

    def __init__(self, host, port):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(200)
	self.printer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def printer_connect(self, reconnect_time):
        try:
            self.printer.connect(printer_mks)
            self.printer_list.append(self.printer)
	    self.prcon_time = 0
	    self.prcon_state = 'online'
        except Exception, e:
            print e
	    self.prcon_time = time.time() + reconnect_time

    def main_loop(self):
        self.server_list.append(self.server)
        while 1:
	    if self.prcon_state == 'offline' and time.time() > self.prcon_time:
		self.printer_connect(30)
            time.sleep(delay)
            ss = select.select
            inputready, outputready, exceptready = ss(self.server_list + self.client_list, [], [], 5)
            for self.s in inputready:
                if self.s == self.server:
                    self.on_client_accept()
                    break
                self.data = self.s.recv(buffer_size)
                if len(self.data) == 0:
                    self.on_client_close()
                    break
                else:
                    self.on_client_recv()
	    if self.prcon_state != 'offline':
        	inputready, outputready, exceptready = ss(self.printer_list, [], [], 0.1)
        	for self.s in inputready:
		    self.data = self.s.recv(buffer_size)
		    if len(self.data) == 0:
                	self.on_printer_close()
                	break
		    else:
                	self.on_printer_recv()

    def on_client_accept(self):
        clientsock, clientaddr = self.server.accept()
        print clientaddr, "has connected"
        self.client_list.append(clientsock)

    def on_client_close(self):
        print self.s.getpeername(), "has disconnected"
        #remove objects from client_list
        self.client_list.remove(self.s)
	self.s.close()

    def on_printer_close(self):
        #remove objects from printer_list
        self.printer_list.remove(self.s)
	#close socket
	self.s.close()
	#FIXME add disconnect feedback
	self.prcon_state = 'offline'

    def on_client_recv(self):
        data = self.data
	peer = self.s.getpeername()
	#parse_data(data)
	#FIXME parse client command
        #print peer, ">>", data
	if self.prcon_state == 'online':
	    self.printer_list[0].send(data)
	    return
	if self.prcon_state == 'transfer':
	    #silently drop input while filelist transfer is happening
	    pass
	if self.prcon_state == 'offline':
	    self.s.send('failed\r\n')

    def on_printer_recv(self):
        data = self.data
	peer = self.s.getpeername()
	self.parse_response(data)
	#FIXME parse client command
        #print peer, ">>", data
	for client in self.client_list:
	    client.send(data)

    def parse_response(self,data):
	global curExtruder0Temp,tgtExtruder0Temp,curExtruder1Temp,tgtExtruder1Temp,curBedTemp,tgtBedTemp,progress,current_file,file_loaded,printer_status,firmware,print_status,updated
	for s in data.splitlines():
	    if self.prcon_state == 'online' and 'Begin file list' in s:
		self.prcon_state = 'transfer'
		continue
	    if self.prcon_state == 'transfer' and 'End file list' in s:
		self.prcon_state = 'online'
		continue
	    if self.prcon_state == 'online' and "T" in s and "B" in s and "T0" in s:
		t0_temp = s[s.find("T0:") + len("T0:"):s.find("T1:")]
		t1_temp = s[s.find("T1:") + len("T1:"):s.find("@:")]
		bed_temp = s[s.find("B:") + len("B:"):s.find("T0:")]
		curExtruder0Temp = float(t0_temp[0:t0_temp.find("/")])
		tgtExtruder0Temp = float(t0_temp[t0_temp.find("/") + 1:len(t0_temp)])
		curExtruder1Temp = float(t1_temp[0:t1_temp.find("/")])
		tgtExtruder1Temp = float(t1_temp[t1_temp.find("/") + 1:len(t1_temp)])
		curBedTemp = float(bed_temp[0:bed_temp.find("/")])
		tgtBedTemp = float(bed_temp[bed_temp.find("/") + 1:len(bed_temp)])
		print "T:", curExtruder0Temp, " B:",curBedTemp
		updated['M105'] = time.time()
		continue
	    if self.prcon_state == 'online' and s.startswith("M997 "):
        	if "IDLE" in s:
		    if printer_status == 'printing':
			# We finished (or aborted)
			pass
		    printer_status = 'idle'
		    print_status = 'idle' 
		    updated['M997'] = time.time()
        	elif "PRINTING" in s:
		    printer_status = 'printing'
		    print_status = 'started'
		    updated['M997'] = time.time()
        	elif "PAUSE" in s:
		    printer_status = 'printing'
		    print_status = 'paused'
		    updated['M997'] = time.time()
        	continue
	    if self.prcon_state == 'online' and s.startswith("M994 ") and s.rfind("/") != -1:
    		current_file = s[s.rfind("/") + 1:s.rfind(";")]
        	continue
	    if self.prcon_state == 'online' and s.startswith("M27 "):
		progress = float(s[s.find("M27") + len("M27"):len(s)].replace(" ", ""))
		updated['M27'] = time.time()
		continue
	    if self.prcon_state == 'online' and s.startswith("M992 "):
        	tm = s[s.find("M992") + len("M992"):len(s)].replace(" ", "")
        	mms = tm.split(":")
    		#printing_time = int(mms[0]) * 3600 + int(mms[1]) * 60 + int(mms[2])
		updated['M992'] = time.time()
		continue

if __name__ == '__main__':
        server = TheServer('', 8080)
        try:
            server.main_loop()
        except KeyboardInterrupt:
            print "Ctrl C - Stopping server"
            sys.exit(1)
