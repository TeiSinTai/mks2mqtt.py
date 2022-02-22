# mks2mqtt.py
MKS (3D printer WiFi add-on) to MQTT bridge, with included socket proxy

Working version achieved at 0.5.2.

## Files
- ha_discovery.py - python script to send JSON MQTT messages to tie in topics used by this project into Home Assistant throught it's MQTT Discovery
- proxy80.py - simple tcp proxy for port 80, temporarily in separate file
- proxy8080.py - main file (for now), to be merged with proxy80.py 

## Setup and run
Code written for Python 3 

Depends on Paho MQTT Client library (pip install paho-mqtt). All settings right now are done inside the code, at the top of the each script.

Runs just with python proxy8080.py

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
- v0.5.1 add mqtt discovery for HA
- v0.5.2 fixed printing_time representation, improved stability
- moved most description and text to wiki

# planned "milestones"
- v0.6 add modes - standalone/proxy8080
- v0.6.1 merge with proxy80
- v0.7 add MQTT suscribe and sending commands on MQTT input
- v0.8 add command line switches instead of constants (printer address, mode, mqtt server), or even config file
