import os, sys, fileinput #for file management
import serial
from xbee import XBee as XB
from time import sleep #for serial communication
import serial.tools.list_ports as stlp

xbee = {
    "baud": 9600,
    "VID": "1027", # The Vendor ID of Zigbee Xbee Pro S1 model
    "PID": "24597", # The Product ID of Zigbee Xbee Pro S1 model
    "port": None
}

ser = serial.Serial('/dev/cu.usbserial-DN02Z6QG', baudrate=xbee['baud'])

data = ""
while True:
    data += ser.read()
    if len(data) == 33:
        break
print data
