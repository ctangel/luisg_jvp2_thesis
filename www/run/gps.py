#! /usr/bin/python
'''
 * runbase.py
 *
 * Runs on a device (drone or base) and continuously scans for messages send
 * decryptes them.
 *
 * Author: Luis Gonzalez-Yante
 *
'''
import hashlib
import os
import threading
import random
import string
import json
import math
from geopy import distance
import binascii
import time
try:
    import gps
except:
    from gps3 import gps3 as gps
import serial.tools.list_ports
import subprocess as sp
import Comms

# Global Variables
dev_id          = None
glob_id         = None
base_alt        = 5
dev_coor        = None

# GPS Device Information
GPS = {
    "vid": ["067B","10C4"],
    "pid": ["2303","EA60"],
    "port": None,
    "session": `None`
}

def find_device(device):
    """ Searches system's open ports for the provided device.
        If found, returns true, else false."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
      for i in range(len(device['vid'])):
          if port.vid == int(device['vid'][i], 16) and port.pid == int(device['pid'][i], 16):
              device['port'] = port.device
              return True
    return False

def get_bearing(origin, target):
    """ Returns the bearing (0 - 360 deg) the path between the two supplied GPS cooridates will
        take the drone towards """
    lat1 = math.radians(origin.get('lat'))
    lng1 = math.radians(origin.get('lng'))
    lat2 = math.radians(target.get('lat'))
    lng2 = math.radians(target.get('lng'))
    y = math.sin(lng2-lng1) * math.cos(lat2);
    x = (math.cos(lat1) * math.sin(lat2)) - (math.sin(lat1) * math.cos(lat2) * math.cos(lng2-lng1));
    brng = math.degrees(math.atan2(y, x));
    deg = 360 - ((brng + 360) % 360);
    return ((brng + 360) % 360);

def get_new_coor(coor, brng, d):
    """ Returns the new coordinates of a location d kilometers in brng bearing from coordinates
        (lat, lng1) """
    lat1 = math.radians(coor.get('lat'))
    lng1 = math.radians(coor.get('lng'))
    R = 6371.0
    lat2 = math.asin((math.sin(lat1)*math.cos(d/R)) + (math.cos(lat1)*math.sin(d/R)*math.cos(math.radians(brng)) ));
    lng2 = lng1 + math.atan2(math.sin(math.radians(brng))*math.sin(d/R)*math.cos(lat1), math.cos(d/R) - (math.sin(lat1)*math.sin(lat2)));
    return {"lat":math.degrees(lat2), "lng":math.degrees(lng2)}

def get_distance(coor1, coor2):
    pos1 = (coor1.get('lat'), coor1.get('lng'))
    pos2 = (coor2.get('lat'), coor2.get('lng'))
    return distance.distance(pos1, pos2).kilometers


def get_coordinates():
    data = {'lat': None, 'lng': None, 'alt':None}
    if GPS.get('session') != None:
        while True:
            time.sleep(1)
            report = GPS['session'].next()
            print report
            if report != None:
                report = json.loads(report)
                if report.get('class') == "TPV":
                    if report.get('lat') != None and report.get('lon') != None:
                        data['lat'] = report.get('lat')
                        data['lng'] = report.get('lon')
                        data['alt'] = report.get('alt')
                        break
    return data

def startGPS(device):
    """ Sets up and establishes a connection with the provided gps device.
        If connection is successful, it returns true, else false"""
    # Checking if GPS is Connected to Socket
    try:
        os.system("gpsd %s" % (device['port']))
    except:
        # GPS Failed to Connect to Socket
        return False

    # Checking if gps session is valid
    while True:
        time.sleep(1) 
        device['session'] = gps.GPSDSocket()
        device['session'].connect()
        device['session'].watch()
        try:
            break
        except:
            pass
    while True:
        time.sleep(1)
        report = device['session'].next()
        if report != None:
            report = json.loads(report)
            if report.get('class') == "TPV":
                break
    return True

#
#   Start Script
#

# Get ID Name
try:
    with open("id.pub") as fn:
        dev_id = fn.read()
except:
    exit("id.pub was not found")

# Get Global Id
try:
    with open("global.pub") as fn:
        glob_id = fn.read()
except:
    exit("global.pub was not found")

print "/*** Starting Base"
print "\tdev_id  \t%s" % dev_id
print "\tglob_id \t%s" % glob_id

# Find GPS
if find_device(GPS):
    if not startGPS(GPS):
        exit("GPS Failed to Connect")
else:
    exit("GPS not found")

if GPS.get('session') == None:
    print '\tGPS not found'
else:
    print "\tGPS found at %s" % GPS.get('port')

dev_coor = get_coordinates()
print "\tStarting Position"
print "\t\tlatitude:  %f" % dev_coor.get('lat')
print "\t\tlongitude: %f" % dev_coor.get('lng')
print "\t\taltitude:  %f" % dev_coor.get('alt')
