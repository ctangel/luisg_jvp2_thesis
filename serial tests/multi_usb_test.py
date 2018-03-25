"""
mutli_usb_test.py
Author: James Poindexter
Date Last Modified: Friday March 23, 2018

Purpose: With the Pixhawk and an XBEE component plugged into the raspberry
pi at the same time, attempt to pull data from the pixhawk and send the data
to another pi unit once requested
This will test the simultaneous usage of both components over serial
Makes heavy usage from test_connection.py, derived from Tiziano Fiorenzani

To connect to the Pixhawk, the test goes through all known possible /tty* file
paths to establish a correct connection
"""

import serial
import time
from dronekit import connect, VehicleMode
import serial.tools.list_ports
import sys

# Global variables
characterMin = 2
N_attempts = 3
readTimeout = 3 #in seconds
portFound = False

# Xbee Variables
xbee_baud = 9600
xbee_connectionString = ""
CONST_xbeeVID = "0403" #The Vendor ID of the Zigbee Xbee Pro S1 model
CONST_xbeePID = "6015" #The Product ID of the Zigbee Xbee Pro S1 model
CONST_xbeeHWID = CONST_xbeeVID + ":" + CONST_xbeePID

# Pixhawk Variables
pixhawk_baud = 115200
pixhawk_connectionString = ""
CONST_pixhawkVID = "26ac" #The Vendor ID of the Pixhawk Flight Controller
CONST_pixhawkPID = "0011" #The Product ID of the Pixhawk Flight Controller
CONST_pixhawkHWID = CONST_pixhawkVID + ":" + CONST_pixhawkPID

# --- ESTABLISH CONNECTION ---
portFound = False
ports = list(serial.tools.list_ports.comports()) #get list of all open comports

# Search for Pixhawk
print(">>> Connecting to UAV... <<<")
for p in ports:
    lst = p[2].split("VID:PID=")[1].split(" ")
    #First element is the VID:PID, second element is the SNR as 'SNR=...'

    if CONST_pixhawkHWID in lst[0]:
        pixhawk_connectionString = p[0]
        vehicle = connect(pixhawk_connectionString, baud=pixhawk_baud, wait_ready=True)
        portFound = True
        break
if portFound == False:
    print "Pixhawk not found. Exiting test"
    exit()

print(">>> Establishing Xbee serial port <<<")
portFound = False
for p in ports:
    lst = p[2].split("VID:PID=")[1].split(" ")
    #First element is the VID:PID, second element is the SNR as 'SNR=...'

    if CONST_xbeeHWID in lst[0]:
        xbee_connectionString = p[0]
        xbee_ser = serial.Serial(xbee_connectionString, baud_rate=xbee_baud, timeout=readTimeout)
        portFound = True
        break

if portFound == False:
    print "Xbee not found. Exiting test"
    vehicle.close()
    exit()

# --- FUNCTIONALITY ---
"""
Listen and wait for characterMin characters, any kind of character.
If characterMin characters are recevied, print the attitude of the vehicle
and send a message to the host Xbee.
If less than characterMin characters are received, print "TIMEOUT: not enough
information received" and send a message to the host Xbee.

Do this for N_attempts, and then close the program
"""
print(">>> Beginning test <<<")
counter = 0
while True:
    data = xbee_ser.read(characterMin) #returns the bytes received
    #print 'Byte count: ' + str(len(data))

    if len(data) < characterMin:
        print "TIMEOUT: not enough information received"
        xbee_ser.write(b'not enough\n')
    else:
        print(vehicle.attitude)
        print 'Data: ' + data
        xbee_ser.write(b'OK')
    counter += 1
    if counter >= N_attempts:
        xbee_ser.close()
        vehicle.close()
        exit()
