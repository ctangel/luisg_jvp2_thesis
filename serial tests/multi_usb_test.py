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

# Xbee Variables
xbee = {
    "baud": 9600,
    "VID": "0403", # The Vendor ID of Zigbee Xbee Pro S1 model
    "PID": "6015", # The Product ID of Zigbee Xbee Pro S1 model
    "port": None
}

# Pixhawk Variables
pixhawk = {
    "baud": 115200,
    "VID": "26ac", # The Vendor ID of the Pixhawk Flight Controller
    "PID": "0011", # The Product ID of the Pixhawk Flight Contorller
    "port": None
}

# Helper Functions
def find_device(device):
    """ Function searched system's open ports for the provided device. 
        If found it returns true else, it returns false """
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == int(device.VID, 16) and port.pid == int(device.PID, 16):
            device.port = port.device
            return True
    return False

# --- ESTABLISH CONNECTION ---

# Search for Pixhawk
print(">>> Connecting to UAV... <<<")
if find_device(pixhawk):
    vehicle = connect(pixhawk.port, baud=pixhawk.baud, wait_ready=True)
else:
    print "Pixhawk not found... Exiting test"
    exit()

# Search for Xbee
print(">>> Establishing Xbee serial port <<<")
if find_device(xbee):
    xbee_ser = serial.Serial(xbee.port, baud_rate=xbee.baud, timeout=readTimeout)
else:
    print "Xbee not found... Existing test"
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
