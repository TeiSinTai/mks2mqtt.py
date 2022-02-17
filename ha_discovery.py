# -*- coding: utf-8 -*-
import time
import sys
import json
import paho.mqtt.publish as publish
import re

printer_mks = ('192.168.231.25', 8080)
mqtt_server = ('192.168.233.33', 1883)
mqtt_basetopic = "mksmqtt/{}/".format(printer_mks[0])
mqtt_retain = False # use False while testing, then switch to True
ha_basetopic = "homeassistant/"
printer_name = "Flying Bear Reborn"
printer_model = "Reborn"
printer_manufacturer = "Flying Bear"
use_second_extruder = False


printer_id = "{}_{}".format(printer_name,printer_mks[0])
printer_id = printer_id.replace(' ','_')
printer_id = printer_id.replace('.','-')

# The ID of the node must only consist of characters from the character class [a-zA-Z0-9_-] (alphanumerics, underscore and hyphen).

r = re.compile(r'[^a-zA-z0-9_-]+')
printer_id = r.sub('', printer_id)

msgs = list()

full_device = dict()
short_device = dict()
full_device['identifiers'] = [printer_id]
short_device['identifiers'] = [printer_id]
full_device['name'] = printer_name
full_device['model'] = printer_model
full_device['manufacturer'] = printer_manufacturer

curExtruder0Temp = dict()
curExtruder0Temp['name'] = "Extruder 0 temperature"
curExtruder0Temp['unique_id'] = "{}_cE0".format(printer_id)
curExtruder0Temp['state_topic'] = "{}curExtruder0Temp".format(mqtt_basetopic)
curExtruder0Temp['device_class'] = "temperature"
curExtruder0Temp['unit_of_measurement'] = "°C"
curExtruder0Temp['device'] = full_device
msg=dict()
msg['topic'] = "{}sensor/{}/curExtruder0Temp/config".format(ha_basetopic,printer_id)
msg['payload'] = json.dumps(curExtruder0Temp)
msg['retain'] = mqtt_retain
msgs.append(msg)

tgtExtruder0Temp = dict()
tgtExtruder0Temp['name'] = "Extruder 0 target temperature"
tgtExtruder0Temp['unique_id'] = "{}_tE0".format(printer_id)
tgtExtruder0Temp['state_topic'] = "{}tgtExtruder0Temp".format(mqtt_basetopic)
tgtExtruder0Temp['device_class'] = "temperature"
tgtExtruder0Temp['unit_of_measurement'] = "°C"
tgtExtruder0Temp['device'] = short_device
msg=dict()
msg['topic'] = "{}sensor/{}/tgtExtruder0Temp/config".format(ha_basetopic,printer_id)
msg['payload'] = json.dumps(tgtExtruder0Temp)
msg['retain'] = mqtt_retain
msgs.append(msg)

if use_second_extruder:
    curExtruder1Temp = dict()
    curExtruder1Temp['name'] = "Extruder 1 temperature"
    curExtruder1Temp['unique_id'] = "{}_cE1".format(printer_id)
    curExtruder1Temp['state_topic'] = "{}curExtruder1Temp".format(mqtt_basetopic)
    curExtruder1Temp['device_class'] = "temperature"
    curExtruder1Temp['unit_of_measurement'] = "°C"
    curExtruder1Temp['device'] = short_device
    msg=dict()
    msg['topic'] = "{}sensor/{}/curExtruder1Temp/config".format(ha_basetopic,printer_id)
    msg['payload'] = json.dumps(curExtruder1Temp)
    msg['retain'] = mqtt_retain
    msgs.append(msg)

    tgtExtruder1Temp = dict()
    tgtExtruder1Temp['name'] = "Extruder 1 target temperature"
    tgtExtruder1Temp['unique_id'] = "{}_tE1".format(printer_id)
    tgtExtruder1Temp['state_topic'] = "{}tgtExtruder1Temp".format(mqtt_basetopic)
    tgtExtruder1Temp['device_class'] = "temperature"
    tgtExtruder1Temp['unit_of_measurement'] = "°C"
    tgtExtruder1Temp['device'] = short_device
    msg=dict()
    msg['topic'] = "{}sensor/{}/tgtExtruder1Temp/config".format(ha_basetopic,printer_id)
    msg['payload'] = json.dumps(tgtExtruder1Temp)
    msg['retain'] = mqtt_retain
    msgs.append(msg)


curBedTemp = dict()
curBedTemp['name'] = "Bed temperature"
curBedTemp['unique_id'] = "{}_cB".format(printer_id)
curBedTemp['state_topic'] = "{}curBedTemp".format(mqtt_basetopic)
curBedTemp['device_class'] = "temperature"
curBedTemp['unit_of_measurement'] = "°C"
curBedTemp['device'] = short_device
msg=dict()
msg['topic'] = "{}sensor/{}/curBedTemp/config".format(ha_basetopic,printer_id)
msg['payload'] = json.dumps(curBedTemp)
msg['retain'] = mqtt_retain
msgs.append(msg)

tgtBedTemp = dict()
tgtBedTemp['name'] = "Bed target temperature"
tgtBedTemp['unique_id'] = "{}_tB".format(printer_id)
tgtBedTemp['state_topic'] = "{}tgtBedTemp".format(mqtt_basetopic)
tgtBedTemp['device_class'] = "temperature"
tgtBedTemp['unit_of_measurement'] = "°C"
tgtBedTemp['device'] = short_device
msg=dict()
msg['topic'] = "{}sensor/{}/tgtBedTemp/config".format(ha_basetopic,printer_id)
msg['payload'] = json.dumps(tgtBedTemp)
msg['retain'] = mqtt_retain
msgs.append(msg)

printing_time = dict()
printing_time['name'] = "Time spent printing"
printing_time['unique_id'] = "{}_time".format(printer_id)
printing_time['state_topic'] = "{}printing_time".format(mqtt_basetopic)
printing_time['device_class'] = "timestamp"
printing_time['device'] = short_device
msg=dict()
msg['topic'] = "{}sensor/{}/printing_time/config".format(ha_basetopic,printer_id)
msg['payload'] = json.dumps(printing_time)
msg['retain'] = mqtt_retain
msgs.append(msg)

prcon_status = dict()
prcon_status['name'] = "Printer connection"
prcon_status['unique_id'] = "{}_prcon_status".format(printer_id)
prcon_status['state_topic'] = "{}prcon_status".format(mqtt_basetopic)
prcon_status['device_class'] = "connectivity"
prcon_status['device'] = short_device
prcon_status['payload_on'] = "online"
prcon_status['payload_off'] = "offline"
msg=dict()
msg['topic'] = "{}binary_sensor/{}/prcon_status/config".format(ha_basetopic,printer_id)
msg['payload'] = json.dumps(prcon_status)
msg['retain'] = mqtt_retain
msgs.append(msg)

printer_status = dict()
printer_status['name'] = "Printer status"
printer_status['unique_id'] = "{}_printer_status".format(printer_id)
printer_status['state_topic'] = "{}printer_status".format(mqtt_basetopic)
printer_status['device_class'] = "running"
printer_status['device'] = short_device
printer_status['payload_on'] = "printing"
printer_status['payload_off'] = "idle"
msg=dict()
msg['topic'] = "{}binary_sensor/{}/printer_status/config".format(ha_basetopic,printer_id)
msg['payload'] = json.dumps(printer_status)
msg['retain'] = mqtt_retain
msgs.append(msg)

printer_paused = dict()
printer_paused['name'] = "Printer paused"
printer_paused['unique_id'] = "{}_printer_paused".format(printer_id)
printer_paused['state_topic'] = "{}printer_paused".format(mqtt_basetopic)
printer_paused['device_class'] = "problem"
printer_paused['device'] = short_device
printer_paused['payload_on'] = "true"
printer_paused['payload_off'] = "false"
msg=dict()
msg['topic'] = "{}binary_sensor/{}/printer_paused/config".format(ha_basetopic,printer_id)
msg['payload'] = json.dumps(printer_paused)
msg['retain'] = mqtt_retain
msgs.append(msg)

progress = dict()
progress['name'] = "Print progress"
progress['unique_id'] = "{}_progress".format(printer_id)
progress['state_topic'] = "{}progress".format(mqtt_basetopic)
progress['icon'] = "mdi:progress-download"
progress['unit_of_measurement'] = "%"
progress['device'] = short_device
msg=dict()
msg['topic'] = "{}sensor/{}/progress/config".format(ha_basetopic,printer_id)
msg['payload'] = json.dumps(progress)
msg['retain'] = mqtt_retain
msgs.append(msg)

current_file = dict()
current_file['name'] = "File being printed"
current_file['unique_id'] = "{}_file".format(printer_id)
current_file['state_topic'] = "{}current_file".format(mqtt_basetopic)
current_file['icon'] = "mdi:printer-3d"
current_file['device'] = short_device
msg=dict()
msg['topic'] = "{}sensor/{}/current_file/config".format(ha_basetopic,printer_id)
msg['payload'] = json.dumps(current_file)
msg['retain'] = mqtt_retain
msgs.append(msg)

# TODO : add heat sensors (bed, extruder0, extruder1) - binary_sensor, device_class heat, trigger on temp > 36?

## Adding events

event = dict()
event['automation_type'] = "trigger"
event['topic'] = "{}event".format(mqtt_basetopic)
event['device'] = short_device

event['name'] = "Printer is online"
event['type'] = "online"
event['subtype'] = "printer"
event['payload'] = "printer is now online"

msg=dict()
msg['topic'] = "{}device_automation/{}/printerOnline/config".format(ha_basetopic,printer_id)
msg['payload'] = json.dumps(event)
msg['retain'] = mqtt_retain
msgs.append(msg)

event['name'] = "Printer is offline"
event['type'] = "offline"
event['subtype'] = "printer"
event['payload'] = "printer is now offline"

msg=dict()
msg['topic'] = "{}device_automation/{}/printerOffline/config".format(ha_basetopic,printer_id)
msg['payload'] = json.dumps(event)
msg['retain'] = mqtt_retain
msgs.append(msg)

event['name'] = "Finished printing"
event['type'] = "finished"
event['subtype'] = "print"
event['payload'] = "Finished printing"

msg=dict()
msg['topic'] = "{}device_automation/{}/printFinished/config".format(ha_basetopic,printer_id)
msg['payload'] = json.dumps(event)
msg['retain'] = mqtt_retain
msgs.append(msg)

event['name'] = "Started printing"
event['type'] = "started"
event['subtype'] = "print"
event['payload'] = "Started printing"

msg=dict()
msg['topic'] = "{}device_automation/{}/printStarted/config".format(ha_basetopic,printer_id)
msg['payload'] = json.dumps(event)
msg['retain'] = mqtt_retain
msgs.append(msg)

publish.multiple(msgs, hostname=mqtt_server[0], port=mqtt_server[1])