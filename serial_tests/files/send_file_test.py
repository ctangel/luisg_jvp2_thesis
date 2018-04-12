import os, sys, fileinput #for file management
import serial
from time import sleep #for serial communication
import serial.tools.list_ports as stlp

xbee = {
    "baud": 9600,
    "VID": "1027", # The Vendor ID of Zigbee Xbee Pro S1 model
    "PID": "24597", # The Product ID of Zigbee Xbee Pro S1 model
    "port": None
}

ser = serial.Serial('/dev/cu.usbserial-DN02Z3LS', baudrate=xbee['baud'])

#Open file
fIn = open('./sample3.pub', 'r')
contents = fIn.read()

ser.write(contents)
ser.write(b'\n')
t = 1.0 + len(contents)/100.0
sleep(t)
