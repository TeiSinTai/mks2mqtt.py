# mks2mqtt.py
MKS (3D printer WiFi add-on) to MQTT translator, with included socket proxy

# Initial ideas and info
All my tests are done with Flying Bear Reborn.

MKS is, basically, a TCP socket proxy to serial port on printer board, with subset of G-code as language. Standard port is 8080.

Testing suggests that MKS is single client oriented, when someone is already connected, additional clients can only work 
while there is a gap between commands being sent on main channel. Otherwise additional clients are disconnected as data comes from main connection.

Thus a good approach to monitor printer through MKS would be to create a TCP proxy sitting between MKS and any other client (for example, Cura) with 
additional scheduled commands inserted whenever there is a pause (for example, when Cura is disconnected). While it is connected, we can get all information
we need from MKS responses to Cura requests.

# G-code commands and caveats

Official documentation for WiFi module: https://github.com/makerbase-mks/MKS-WIFI/blob/master/Transfer%20protocal%20%20between%20ESP%20and%20MCU.docx

## commands used in existing work by Blooof
- M997 print status 
- M994 current printing file (when printing)
- M992 elapsed print time (when printing)
- M27 job completion in percent
- M105 temperature report
## commands that Cura uses, in addition to M997, M994, M992, M27, M105
- M20 file list
- M23 select file from SD card
- M24 start or resume SD print

FIXME there are more, in Cura interface there are buttons for motor control (homing, moving, lock/unlock, fans on/off...)

## commands that should be interesting 
- M114 current position - didn't work in my tests (not in documentation)
- M25 pause SD print
- M112 emergency stop (not in doc)
- M412 filament runout sensor status - didn't work in my tests (not in doc)
- M524 abort SD print (not in doc)
- M26 stop SD print
- M115 get firmware version. Useless, doesn't contain version number, only can be ROBIN, TFT24, TFT28. Flying Bear Reborn have TFT28.
- M991 (copy of M105)

## Full list of supported commands (actually, not full)
- M20 request, difficult to cache (file list, with directory traversing)
- M23 command (select file)
- M24 command (start/resume)
- M25 command (pause)
- M26 command (stop)
- M27 request (print progress, cacheable, 5s)
- M105 request (temperature, cacheable, 5s)
- M115 request (firmware, cacheable forever)
- M991 request (temperature, cacheable, 5s)
- M992 request (elapsed print time, cacheable, 5s?)
- M994 request (current file, cacheable while printing!)
- M997 request (print status, cacheable, 5s)

# MQTT
Base topic set to mksmqtt/__printer_ip__/

## Topic list
- prcon_status (online, offline) - status of printer connection
- event 
- current_file
- current_file_size
- curExtruder0Temp
- tgtExtruder0Temp
- curExtruder1Temp (when available, i.e. non-zero)
- tgtExtruder1Temp (when curExtruder1Temp non-zero)
- curBedTemp
- tgtBedTemp
- printer_status ("idle", "printing")
- print_status ("IDLE", "PRINTING", "PAUSE")
- progress
- printing_time

## Event (.../event) list
- "printer is now online"
- "printer is now offline"
- "client __client_IP__ connected"
- "client __client_ip__ disconnected"
- "Finished printing"
- "Started printing __filename__"

## Not implemented (yet)
- file_loaded (yes/no)
- firmware

# Home assistant
I want this to work with Home Assistant, so I plan to include HA MQTT discovery - basically, some MQTT JSON publishes that tie other MQTT topics into HA.
Also, tie in "availability" in HA with connection status.

## sensor list
- availability 
- sensor: current extruder temperature (class: temperature)
- sensor: current bed temperature (class: temperature)
- sensor: target extruder temperature (class: temperature) ??
- sensor: target bed temperature (class: temperature) ??
- sensor: elapsed print time (class: timestamp ??)
- sensor: print progress (%)
- switch: idle/running (pause/resume)
- binary_sensor: file loaded (Idle/Loaded)
- generic(None): current filename 
- generic(None): firmware
- device_automation: status updates!

So, printer starts unavailable. Goes to Available/Idle/Not_loaded. M23 loads file, changes state to A/I/Loaded. (Actually, maybe it also autostarts...) M24 starts - A/Running/L. M25 pauses - A/I/L again. M26 stops - A/I/N.


## notes to self - planned automations
- job end notification (simple) - just fire when idle after printing
- wait for bed cooldown after job

# Tests
## v0.1 test
Tests for printer and Cura interaction suggests, that 8080 is for G-code, and 80 is for file upload. And Cura doesn't have port configuration, so it's all or nothing deal.
Thus we need to emulate both, either as two part proxy, or through Nginx reverse proxy (or some other reverse proxy). Another option is using DNAT.

Otherwise, Cura happily connects through proxy for pronter control, and when additional 80 proxy is brought online, it uploads and start print job.

On the other hand, it means that all commands on main channel (port 8080) are live (and not a part of a file being uploaded), so we can simplify their analysis without creating 
"file being uploaded, ignore all commands except upload end" flag.

On connection Cura requests file list (M20).

While idle, Cura spams M105 and M997.

After uploading file, it sends M23 filename, M24, M20.

While printing, it spams M105, M997, M994, M992, M27.

# Ideas
We have clients with requests, printer with responses, four printer states (idle/printing/paused/not available), two client-side states (zero/non-zero attentive clients).

We have limited subset of g-code, so limited, that we can, in fact, cache printer replies...

As I want this to work with HA, we need to rework some statuses... Basically, we have 2 binary sensors and 1 switch.

Also, we have 3 modes: 
- standalone, when we connect to printer without listening to clients, 
- proxy_8080, when we connect to printer and listen to clients only on port 8080 (if clients want to upload files, they either should connect to printer directly, or someone need to provide means to do so outside of this app
- proxy_full, when there are two forwarded ports, 80 and 8080.

Basic flow should be:
- start, try to connect to printer (state "Not available"), listen for clients
- connected to printer - change availability state to available, start queue processing
- disconnected from printer - change availability to N/A, reconnect
- get client requests - parse, if status command - check update time, if less then cache_param for that request - return cached response, otherwise enqueue with client IP.
Filter commands according to state: when not available, block all, when printing - block M20, M115, M23. On blocked commands, return "failed". Maybe create a lock, so it can be done when needed...
- if there are commands in queue - take first, take notice of active request (client IP, command), send to printer
- if there aren't commands in buffer, and time from last update is more then active update_interval, request update (FIXME we need several commands for update)
- get printer response - parse, send to client (if it was client-requested), react to parsed response (change state Idle/Printing, set temperatures)
- on status change (idle/printing) change update_interval (idle update 30s, printing update >5s? configurable)


## Source analysis:
MKS Wifi module - source of response forming
https://github.com/makerbase-mks/MKS-WIFI/blob/master/firmware_source/MksWifi/MksWifi.ino

Cura plugin (also example of response analysis in python)
https://github.com/makerbase-mks/mks-wifi-plugin/blob/master/MKSWifiPlugin/MKSOutputDevice.py

when printing or paused, every 5 sec query 
    M27, M992, M994, M991, M997
or (with additional fw)
    M27, M992, M994, M991, M997, M115

when idle, every 5 sec query
    M991, M27, M997
or (with additional fw)
    M991, M27, M997, M115

Temperature format string:
    "T:%d /%d B:%d /%d T0:%d /%d T1:%d /%d @:0 B@:0\r\n"
- (int)gPrinterInf.curSprayerTemp[0]
- (int)gPrinterInf.desireSprayerTemp[0]
- (int)gPrinterInf.curBedTemp
- (int)gPrinterInf.desireBedTemp
- (int)gPrinterInf.curSprayerTemp[0]
- (int)gPrinterInf.desireSprayerTemp[0]
- (int)gPrinterInf.curSprayerTemp[1]
- (int)gPrinterInf.desireSprayerTemp[1])

Example:
    "T:23 /0 B:44 /60 T0:23 /0 T1:0 /0 @:0 B@:0"

MKS by itself parses incoming g-code, and when it is in defined subset - constructs a response with caching (5sec). Otherwise, it DOES send it to printer, but then if responses aren't in defined subset - they are dropped.

So, anything we do in addition to this subset, we have to do blind. 

As suggested by Cura plugin, any answers returned by MKS can be parsed without remembering what questions were asked.

# Existing projects
https://github.com/Blooof/Mks2MqttReporter 

I didn't test it, but believe it should work. So, pros - it exist and works. Cons - I think it would work only when other clients (i.e. Cura) are disconnected, 
and can actually prevent them from working. Also, my personal language preferences for home infrastructure exclude Java. Otherwise, I would be using this for inspiration.

# Credits
Initial proxy.py code imported from https://voorloopnul.com/blog/a-python-proxy-in-less-than-100-lines-of-code/ (under IDC license).

# done:
- initial research.
- v0.1 import proxy.py as a start, test with printer and Cura, record all interactions
- v0.2 add first (imperfect) parsing of responses.
- v0.3 decouple client and printer connections - make printer connection independent
- v0.4 add scheduled commands (when no client is connected, check on printer anyway). Also, fake partial printer presence for clients even when printer offline
- v0.4.1 parse cmd/send response based on cached data. Testing and clearing some bugs...
- v0.4.2 switching to print function (python3 compatible)
- v0.5 add mqtt reporting, also move to python3

# planned "milestones"
- v0.5.1 add mqtt discovery for HA
- v0.6 add modes - standalone/proxy8080
- v0.7 add MQTT suscribe and sending commands on MQTT input
- v0.8 add command line switches instead of constants (printer address, mode, mqtt server)
