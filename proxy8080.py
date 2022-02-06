#!/usr/bin/python
import socket
import select
import time
import sys

buffer_size = 4096
delay = 0.0001
forward_to = ('192.168.231.25', 8080)

prcon_state = 'online' # also 'offline' and 'transfer'

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


class Forward:
    def __init__(self):
        self.forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def start(self, host, port):
        try:
            self.forward.connect((host, port))
            return self.forward
        except Exception, e:
            print e
            return False

class TheServer:
    input_list = []
    channel = {}

    def __init__(self, host, port):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen(200)

    def main_loop(self):
        self.input_list.append(self.server)
        while 1:
            time.sleep(delay)
            ss = select.select
            inputready, outputready, exceptready = ss(self.input_list, [], [])
            for self.s in inputready:
                if self.s == self.server:
                    self.on_accept()
                    break

                self.data = self.s.recv(buffer_size)
                if len(self.data) == 0:
                    self.on_close()
                    break
                else:
                    self.on_recv()

    def on_accept(self):
        forward = Forward().start(forward_to[0], forward_to[1])
        clientsock, clientaddr = self.server.accept()
        if forward:
            print clientaddr, "has connected"
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
        else:
            print "Can't establish connection with remote server.",
            print "Closing connection with client side", clientaddr
            clientsock.close()

    def on_close(self):
        print self.s.getpeername(), "has disconnected"
        #remove objects from input_list
        self.input_list.remove(self.s)
        self.input_list.remove(self.channel[self.s])
        out = self.channel[self.s]
        # close the connection with client
        self.channel[out].close()  # equivalent to do self.s.close()
        # close the connection with remote server
        self.channel[self.s].close()
        # delete both objects from channel dict
        del self.channel[out]
        del self.channel[self.s]

    def on_recv(self):
        data = self.data
	peer = self.s.getpeername()
	parse_data(data)
        # here we can parse and/or modify the data before send forward
        #print peer, ">>", data
        self.channel[self.s].send(data)


def parse_data(data):
    global prcon_state,curExtruder0Temp,tgtExtruder0Temp,curExtruder1Temp,tgtExtruder1Temp,curBedTemp,tgtBedTemp,progress,current_file,file_loaded,printer_status,firmware,print_status,updated
    for s in data.splitlines():
	if prcon_state == 'online' and 'Begin file list' in s:
	    prcon_state = 'transfer'
	    continue
	if prcon_state == 'transfer' and 'End file list' in s:
	    prcon_state = 'online'
	    continue
	if prcon_state == 'online' and "T" in s and "B" in s and "T0" in s:
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
	if prcon_state == 'online' and s.startswith("M997 "):
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
        if prcon_state == 'online' and s.startswith("M994 ") and s.rfind("/") != -1:
    	    current_file = s[s.rfind("/") + 1:s.rfind(";")]
            continue
	if prcon_state == 'online' and s.startswith("M27 "):
	    progress = float(s[s.find("M27") + len("M27"):len(s)].replace(" ", ""))
	    updated['M27'] = time.time()
	    continue
	if prcon_state == 'online' and s.startswith("M992 "):
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
