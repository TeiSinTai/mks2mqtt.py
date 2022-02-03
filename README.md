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
## commands used in existing work by Blooof
- M997 print status 
- M994 current printing file (when printing)
- M992 elapsed print time (when printing)
- M27 job completion in percent
- M105 temperature report

## commands that should be interesting
- M114 current position - didn't work in my tests?

## important commands to take notice of
- M28 - file upload - basically, all other commands after it are being put into file, and we wouldn't be getting good responses to them
- M29 finish file upload

# MQTT
Topic list TBD

# Home assistant
I want this to work with Home Assistant, so I plan to include HA MQTT discovery - basically, some MQTT JSON publishes that tie other MQTT topics into HA.
Also, tie in "availability" in HA with connection status.

## sensor list
- sensor: current extruder temperature (class: temperature)
- sensor: current bed temperature (class: temperature)
- sensor: target extruder temperature (class: temperature)
- sensor: target bed temperature (class: temperature)
- binary_sensor: status idle(OFF)/printing(ON)
- sensor: elapsed print time

TBD:
- current filename
- stop/pause/start as buttons
- can we do emergency stop?

## notes to self - planned automations
- job end notification (simple) - just fire when idle after printing
- wait for bed cooldown after job

# Existing projects
https://github.com/Blooof/Mks2MqttReporter 

I didn't test it, but believe it should work. So, pros - it exist and works. Cons - I think it would work only when other clients (i.e. Cura) are disconnected, 
and can actually prevent them from working. Also, my personal language preferences for home infrastructure exclude Java. Otherwise, I would be using this for inspiration.

# Credits
Initial proxy.py code would be imported from https://voorloopnul.com/blog/a-python-proxy-in-less-than-100-lines-of-code/ (under IDC license).

# done:
- initial research.

# planned "milestones"
- v0.1 import proxy.py as a start, test with printer and Cura, record all interactions
- v0.20 switch from packet flow to lines (add linebreak detection)
- v0.30 cmd/response parse 
- v0.40 add mqtt reporting
- v0.45 add mqtt discovery for HA
- v0.50 add scheduled commands (when no client is connected, check on printer anyway)
- v0.60 add MQTT suscribe and sending commands on MQTT input
- v0.70 add multiplexing (multiple clients)
