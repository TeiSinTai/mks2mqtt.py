# -*- coding: utf-8 -*-
import socket
import select
import time
import sys
import paho.mqtt.client as mqtt


printer_mks = ('192.168.231.25', 8080)
mqtt_server = ('192.168.233.33', 1883)
mqtt_basetopic = "mksmqtt/{}/".format(printer_mks[0])
update_interval = 5 # interval between updates

buffer_size = 4096
delay = 0.0001


curExtruder0Temp = 0
tgtExtruder0Temp = 0
curExtruder1Temp = 0
tgtExtruder1Temp = 0
curBedTemp = 0
tgtBedTemp = 0
progress = 0
current_file = {'name': '', 'size':0} # M994 name and size
file_loaded = False
printer_status = "idle" # also "printing" (even when paused)
firmware = None #M115 request
print_status = "IDLE" # directly from M997 IDLE/PRINTING/PAUSE
#(idle/started/paused/aborted/finished) (how we get aborted?..)

printing_time = '00:00:00' #elapsedPrintTime (hh:mm:ss)


updated = {}
updated['M997'] = 0 #(print status, cacheable, 5s)
updated['M105'] = 0 #(temperature, cacheable, 5s) also M991
updated['M27'] = 0 #(print progress, cacheable, 5s)
updated['M992'] = 0 #(elapsed print time, cacheable, 5s?)
updated['M994'] = 0 #(current printed file, cacheable for all print time...)


class TheServer:
    server_list = []
    client_list = []
    printer_list = []
    prcon_time = 0
    prcon_state = 'offline' # also 'online' and 'transfer'
    update_status = 1 # 0 - update in progress, timestamp - time of last successful update, 1 - starting value

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
            self.mqtt_publish("prcon_status","online")
            self.mqtt_publish("event","printer is now online")
            print("Printer online")
        except Exception as e:
            print(e)
            #FIXME only print when first error
            self.mqtt_publish("prcon_status","offline")
            self.prcon_time = time.time() + reconnect_time

    def main_loop(self):
        self.server_list.append(self.server)
        while 1:
            self.ts = time.time()
            if self.prcon_state == 'offline' and self.ts > self.prcon_time:
                self.printer_connect(30)
            if self.prcon_state == 'online' and self.ts > self.update_status > 0:
                self.printer_update()
            if self.prcon_state == 'online' and self.update_status == 0:
                self.check_update()

            ss = select.select
            inputready, outputready, exceptready = ss(self.server_list + self.client_list, [], [], delay) # with timeout
            for self.s in inputready:
                if self.s == self.server:
                    self.on_client_accept()
                    break
                try:
                    self.data = self.s.recv(buffer_size)
                except ConnectionResetError:
                    self.on_client_close()
                    break
                except OSError:
                    self.on_client_close()
                    break
                if len(self.data) == 0:
                    self.on_client_close()
                    break
                else:
                    self.on_client_recv()
            if self.prcon_state != 'offline':
                inputready, outputready, exceptready = ss(self.printer_list, [], [], delay) # with timeout
                for self.s in inputready:
                    try:
                        self.data = self.s.recv(buffer_size)
                    except ConnectionResetError:
                        self.on_printer_close()
                        break
                    except OSError:
                        self.on_printer_close()
                        break
                    if len(self.data) == 0:
                        self.on_printer_close()
                        break
                    else:
                        self.on_printer_recv()
            time.sleep(delay)

    def on_client_accept(self):
        clientsock, clientaddr = self.server.accept()
        print(clientaddr, "has connected")
        self.mqtt_publish("event","client {} connected".format(clientaddr))
        self.client_list.append(clientsock)

    def on_client_close(self):
        print(self.s.getpeername(), "has disconnected")
        self.mqtt_publish("event","client {} disconnected".format(self.s.getpeername()))
        #remove objects from client_list
        self.client_list.remove(self.s)
        self.s.close()

    def on_printer_close(self):
        #remove objects from printer_list
        self.printer_list.remove(self.s)
        #close socket
        self.s.close()
        #FIXME add disconnect feedback
        self.mqtt_publish("prcon_status","offline")
        self.mqtt_publish("event","printer is now offline")
        print("Printer offline")
        self.prcon_state = 'offline'

    def on_client_recv(self):
        data = self.data
        peer = self.s.getpeername()
        cmd = self.parse_request(data)
        if cmd == '':
            return
        print(peer, ">>", cmd)
        if self.prcon_state == 'online':
            self.printer_list[0].send("{}\r\n".format(cmd).encode("ascii"))
            return
        #if self.prcon_state == 'transfer':
        #    #silently drop input while filelist transfer is happening
        #    return
        if self.prcon_state == 'offline':
            self.s.send(b'failed\r\n')

    def on_printer_recv(self):
        data = self.data
        peer = self.s.getpeername()
        self.parse_response(data)
        for client in self.client_list:
            client.send(data)

    def printer_update(self):
        global updated, printer_status
        updated['M105'] = 0
        updated['M992'] = 0
        updated['M994'] = 0
        updated['M997'] = 0
        updated['M27'] = 0
        self.update_status = 0
        if printer_status == 'idle':
            cmd = b"M997\r\nM105\r\n"
        else:
            #FIXME request file only once?
            cmd = b"M997\r\nM105\r\nM27\r\nM992\r\nM994\r\n"
        try:
            self.printer_list[0].send(cmd)
        except Exception as e:
            print(e)
            self.on_printer_close()

    def check_update(self):
        global updated, printer_status, update_interval
        #if printer_status == 'idle' and updated['M105'] > 0 and updated['M997'] > 0:
        if updated['M105'] > 0 and updated['M997'] > 0:
            self.update_status = self.ts + update_interval
        #if printer_status == 'printing' and updated['M105'] > 0 and updated['M997'] > 0 and updated['M992'] > 0 and updated['M27'] > 0 and updated['M994'] > 0:
        #    self.update_status = self.ts + update_interval

    def parse_request(self,data):
        global curExtruder0Temp,tgtExtruder0Temp,curExtruder1Temp,tgtExtruder1Temp,curBedTemp,tgtBedTemp,progress,current_file,file_loaded,printer_status,firmware,print_status,updated
        unparsed = set()
        for s in data.decode("ascii").splitlines():
            if s == "M105":
                self.s.send("ok\r\nT:{0} /{1} B:{2} /{3} T0:{0} /{1} T1:{4} /{5} @:0 B@:0\r\n".format(int(curExtruder0Temp), int(tgtExtruder0Temp), int(curBedTemp), int(tgtBedTemp), int(curExtruder1Temp), int(tgtExtruder1Temp)).encode("ascii"))
                continue
            if s == "M997":
                self.s.send("ok\r\nM997 {}\r\n".format(print_status).encode("ascii"))
                continue
            if s == "M994":
                self.s.send("ok\r\nM994 1:/{};{}\r\n".format(current_file['name'], current_file['size']).encode("ascii"))
                continue
            if s == "M992":
                self.s.send("ok\r\nM992 {}\r\n".format(printing_time).encode("ascii"))
                continue
            if s == "M27":
                self.s.send("ok\r\nM27 {}\r\n".format(int(progress)).encode("ascii"))
                continue
            if s.startswith("M23"):
                #get selected filename directly from select command of client. 
                current_file['name'] = s[s.find("M23") + len("M23"):len(s)].replace(" ", "")
                self.mqtt_publish("current_file",current_file['name'])
            unparsed.add(s) 
        return "\r\n".join(unparsed)

    def parse_response(self,data):
        global curExtruder0Temp,tgtExtruder0Temp,curExtruder1Temp,tgtExtruder1Temp,curBedTemp,tgtBedTemp,progress,current_file,file_loaded,printer_status,firmware,print_status,printing_time,updated
        for s in data.decode("ascii").splitlines():
            #if self.prcon_state == 'online' and 'Begin file list' in s:
            #    self.prcon_state = 'transfer'
            #    continue
            #if 'End file list' in s:
            #    self.prcon_state = 'online'
            #    continue
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
                print("T:", curExtruder0Temp, " B:",curBedTemp)
                updated['M105'] = self.ts
                self.mqtt_publish("curExtruder0Temp",curExtruder0Temp)
                self.mqtt_publish("curExtruder1Temp",curExtruder1Temp)
                self.mqtt_publish("tgtExtruder0Temp",tgtExtruder0Temp)
                self.mqtt_publish("tgtExtruder1Temp",tgtExtruder1Temp)
                self.mqtt_publish("curBedTemp",curBedTemp)
                self.mqtt_publish("tgtBedTemp",tgtBedTemp)
                continue
            if self.prcon_state == 'online' and s.startswith("M997 "):
                if "IDLE" in s:
                    if printer_status == 'printing':
                        # We finished (or aborted)
                        self.mqtt_publish("event","Finished printing")
                        print("Finished printing {}".format(current_file['name']))
                        progress = 0
                        printing_time = '00:00:00'
                    self.mqtt_publish("printer_status","idle")
                    self.mqtt_publish("print_status","IDLE")
                    printer_status = 'idle'
                    print_status = 'IDLE' 
                    updated['M997'] = time.time()
                elif "PRINTING" in s:
                    if printer_status == 'idle':
                        # Started print. We use filename from M23 (probably), and fill progress and time elapsed from defaults
                        # also, we must set updated[] for M27, M994 and M992 - because we didn't ask for them, but check_update() now think that we did.
                        print("Started printing {}".format(current_file['name']))
                        self.mqtt_publish("event","Started printing {}".format(current_file['name']))
                        updated['M27'] = time.time()
                        updated['M994'] = time.time()
                        updated['M992'] = time.time()
                        progress = 0
                        printing_time = '00:00:00'
                    #FIXME detect pause end
                    self.mqtt_publish("printer_status","printing")
                    self.mqtt_publish("print_status","PRINTING")
                    printer_status = 'printing'
                    print_status = 'PRINTING'
                    updated['M997'] = time.time()
                elif "PAUSE" in s:
                    #FIXME detect pause start
                    self.mqtt_publish("printer_status","printing")
                    self.mqtt_publish("print_status","PAUSE")
                    printer_status = 'printing'
                    print_status = 'PAUSE'
                    updated['M997'] = time.time()
                continue
            if self.prcon_state == 'online' and s.startswith("M994 ") and s.rfind("/") != -1:
                current_file['name'] = s[s.rfind("/") + 1:s.rfind(";")]
                current_file['size'] = s[s.rfind(";") + 1:]
                # M994 1:/esp32cam_print1.gcode;-788190462
                # it looks like decoding uint as int... Oh well, it doesn't matter anyway, we can't use it meaningfully
                self.mqtt_publish("current_file",current_file['name'])
                self.mqtt_publish("current_file_size",current_file['size'])
                updated['M994'] = time.time()
                continue
            if self.prcon_state == 'online' and s.startswith("M27 "):
                progress = float(s[s.find("M27") + len("M27"):len(s)].replace(" ", ""))
                updated['M27'] = time.time()
                self.mqtt_publish("progress",progress)
                continue
            if self.prcon_state == 'online' and s.startswith("M992 "):
                tm = s[s.find("M992") + len("M992"):len(s)].replace(" ", "")
                mms = tm.split(":")
                printing_time = tm
                self.mqtt_publish("printing_time",tm)
                #printing_time = int(mms[0]) * 3600 + int(mms[1]) * 60 + int(mms[2])
                updated['M992'] = time.time()
                continue
            if s == 'ok':
                continue
            if s == 'File selected':
                continue
            print("<<<",s)

    def mqtt_publish(self,topic,payload):
        global mqttc, mqtt_basetopic
        mqttc.publish("{}{}".format(mqtt_basetopic,topic),payload)

### MQTT parts

# The callback for when the client receives a CONNACK response from the server.
def on_mqtt_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    # FIXME make subscriptions to printer related topics:
    #client.subscribe("$SYS/#")
    # FIXME set status available?? program status, not printer???

# The callback for when a PUBLISH message is received from the server.
def on_mqtt_message(client, userdata, msg):
    print(msg.topic+" "+str(msg.payload))

mqttc = mqtt.Client()
mqttc.on_connect = on_mqtt_connect
mqttc.on_message = on_mqtt_message

mqttc.connect(mqtt_server[0], mqtt_server[1], 60)
mqttc.loop_start()

if __name__ == '__main__':
        server = TheServer('', 8080)
        try:
            server.main_loop()
        except KeyboardInterrupt:
            print("Ctrl C - Stopping server")
            # FIXME add mqtt setting disconnect status
            mqttc.loop_stop()
            sys.exit(1)
