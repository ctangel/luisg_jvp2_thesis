"""
getPixhawkPort.py
Author: James Poindexter

Date Created: Sunday March 25, 2018
Date Last Modified: Sunday March 25, 2018

Returns the COM port path of the pixhawk flight controller, assuming it is
plugged into the computer.

Adapted from code written in multi_usb_test.py
"""
import serial.tools.list_ports

# Pixhawk Variables
pixhawk = {
    "baud": 115200,
    "VID": "26ac", # The Vendor ID of the Pixhawk Flight Controller
    "PID": "0011", # The Product ID of the Pixhawk Flight Contorller
    "port": None
}

# Helper Functions
def find_device(device):
    """
        Function searched system's open ports for the provided device.
        If found it return the file path. Otherwise, return FAIL
    """
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == int(device['VID'], 16) and port.pid == int(device['PID'], 16):
            return port.device
    return "FALSE"

print find_device(pixhawk)
