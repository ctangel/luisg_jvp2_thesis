#A simple test to demonstrate Xbee connectivity from two pre-registered
#and pre-configured Xbee devices

import serial
import time

ser = serial.Serial("/dev/ttyUSB0", baudrate=9600)

while True:
    data = ser.read(1)
    print (data)