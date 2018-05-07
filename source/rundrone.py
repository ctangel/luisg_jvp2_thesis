#! /usr/bin/python
'''
 * rundrone.py
 *
 * Runs on a device base and continuously scans for messages send
 * decryptes them.
 *
 * Author: Luis Gonzalez-Yante
 *
'''
import hashlib
import os
import random
import json
import binascii
import subprocess as sp
import threading
import string
import math
import time
import serial.tools.list_ports
import Comms
from dronekit import connect, VehicleMode, LocationGlobal, Command
from pymavlink import mavutil
import argparse, sys
from geopy import distance


# CODES
CONFIRM         = 'l'
DIRECT          = 'm'
ASK_DIRECT      = 'n'
RELEASE         = 'o'
SEND            = 'p'
MOVE            = 'q'
ABORT           = 'r'
TAKE_OFF        = 's'
CONFIRM_FP      = 't'
REPLY_STATUS    = 'w'
ACK             = 'y'
LAND            = 'z'

# Base Codes
IDLE            = 'a'
SEND_CONFIRM    = 'b'
SEND_DIRECT     = 'c'
RELEASE_MSG     = 'd'
FORWARD         = 'e'
RELEASE_ACC     = 'f'
PING            = 'g'
REPLY_PING      = 'h'
UPDATE          = 'i'
GLOBAL_PING     = 'j'
PROPOGATE       = 'k'
START_TAKE_OFF  = 'u'
SEND_FP         = 'v'
CHECK_STATUS    = 'x'

enc_file_name   = 'enc.pub'
dec_file_name   = 'dec.pub'
digest          = None
message         = ' '
data            = {'code': IDLE}
flight_plan     = []
flight_stop     = 1
bases           = {}
drones          = {}
PREV_STATE      = IDLE
run             = True
dev_id          = None
glob_id         = None
target          = {"lat":None, "lng":None, "alt":None}
fly             = True
flight_debug    = True
# Pixhawk Device Information
PIXHAWK = {
    "baud": 115200,
    "vid": ["26ac"], # The Vendor ID of the Pixhawk Flight Controller
    "pid": ["0011"], # The Product ID of the Pixhawk Flight Contorller
    "port": None,
    "session": None
}

# XBEE Device Information
XBEE = {
    "vid":      ["0403", "10C4"],
    "pid":      ["6015", "EA60"],
    "port":     None,
    "addr":     None,
    "session":  None
}

def distanceTo(targetLocation):
    """ Monitors the drone's distances to the provided target location. If the
        drone is within 15% of the target, the function returns"""
    vehicle = PIXHAWK.get('session')
    print "DEBUG: targetLocation: %s" % targetLocation
    currentLocation = vehicle.location.global_frame
    targetDistance = get_distance(currentLocation, targetLocation)

    while vehicle.mode.name=="GUIDED":
        #Stop action if we are no longer in guided mode.
        print "DEBUG: mode: %s" % vehicle.mode.name
        currentLocation = vehicle.location.global_frame
        remainingDistance = get_distance(currentLocation, targetLocation)
        print "DEBUG: Distance to target: ", remainingDistance
        if remainingDistance<=targetDistance*0.15:
            #Just below target, in case of undershoot.
            print "DEBUG: Reached target"
            break;
        time.sleep(2)

def get_distance(coor1, coor2):
    """ Calculates the distance between coor1 and coor2  """
    pos1 = (coor1.lat, coor1.lon)
    pos2 = (coor2.lat, coor2.lon)
    return distance.distance(pos1, pos2).meters


def find_device(device):
    """ Searches system's open ports for the provided device. If found, returns
        true, else false. """
    ports = serial.tools.list_ports.comports()
    for port in ports:
       for i in range(len(device['vid'])):
            dev_vid = int(device.get('vid')[i], 16)
            dev_pid = int(device.get('pid')[i], 16)
            if port.vid == dev_vid and port.pid == dev_pid:
                device['port'] = port.device
                return True
    return False

def startPIXHAWK(device):
    """ Establishes a connection with the drone's PIXHAWK. If the connection is
        successful, it returns true, else false """
    try:
        port = device.get('port')
        baud = device.get('baud')
        device['session'] = connect(port, baud=baud, wait_ready=True)
        time.sleep(5)
        return True
    except:
        return False

def startXBEE(device):
    """ Establishes a connection wit the XBee device connected. If the
        connection is successful, it returns true, else false"""
    try:
        device['session'] = Comms.Comms(device.get('port'), data_only=True)
        addr = device.get('session').getLocalAddr()
        time.sleep(1)
        device['addr'] = binascii.hexlify(addr[0] + addr[1])
        return True
    except:
        if device.get('session') != None:
            device['session'].close()
        return False

def get_coordinates():
    """ Obtains the current latitude, longitude and altitude of the drone """
    ans = {}
    #TODO Verify if referencing one global_frame is better
    ans['lat'] = PIXHAWK['session'].location.global_frame.lat
    ans['lng'] = PIXHAWK['session'].location.global_frame.lon
    ans['alt'] = PIXHAWK['session'].location.global_frame.alt
    return ans

def get_next_state():
    """ Checks if messages exists, if so, then is reads them in """
    m = hashlib.md5()
    data = {"code": PREV_STATE}
    msg = {}
    if not XBEE.get('session').isMailboxEmpty():
        msg = XBEE.get('session').readMessage()
        if msg == None:
            return data
        msg = msg.get('rx')
        data = json.loads(msg)
    return data

def send_message(dest=None, data=None):
    """ Sends provided data to the proivded destination via XBee """
    base    = bases.get(dest)
    drone   = drones.get(dest)
    if dest == glob_id:
        print "sending to %s at %s" % (dest, Comms.Comms.BROADCAST)
        XBEE.get('session').sendData(Comms.Comms.BROADCAST, data, None, dest)
    elif bases.get(dest) != None:
        print "sending to %s at %s" % (dest, repr(base.get('addr')))
        XBEE.get('session').sendData(base.get('addr'), data, None, dest)
    elif drones.get(dest) != None:
        print "sending to %s at %s" % (dest, repr(drone.get('addr')))
        XBEE.get('session').sendData(drone.get('addr'), data, None, dest)
    else:
        print "Failed to send"

def print_info(data):
    """ Prints each key and value of the provided dictionary """
    print "\t\tReceived..."
    for key in data:
        print "\t\t\t%s\t\t%s" %(key, repr(data.get(key)))

#
#   State Machtine
#

def ask_for_confirmation(baseID):
    """ Sends a base a message to check if they will pick it up and reply """
    m = {
            "code": SEND_CONFIRM,
            "seq": '1',
            "id": dev_id,
            "addr": XBEE.get('addr')
        }
    send_message(baseID, json.dumps(m))
    #TODO   Need way to check if 1, send_confirmation has been sent and 2. if a
    #       there hasn't been any reply. This would result in aborting the the
    #       mission

def ask_for_direction(baseID, nextBaseID):
    """ Sends a base a message asking for directions to the target base or
        next base """
    m = {
            "code": SEND_DIRECT,
            "base": nextBaseID,
            "id": dev_id
        }
    send_message(baseID, json.dumps(m))

def direct(data):
    global target
    print "\t\tBefore"
    print "\t\t\ttarget: %s" % repr(target)
    print_info(data)
    if fly:
        vehicle = PIXHAWK['session']
    target["waymarks"] = data.get('waymarks')
    target["alt"] = data.get('alt')
    print target.get("waymarks")
    print target.get("alt")
    if fly:
        #Remove any previous waypoints
        cmds = vehicle.commands
        #cmds.clear()
        #cmds.upload()

        for point in target['waymarks'][:-1]:
            cmd = Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT,
                    mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,0, 0, 0, 0, 0, 0,
                    point.get('lat'), point.get('lng'), target['alt'])
            #TODO: is this the correct format for waymarks?
            cmds.add(cmd)
        cmds.upload()
        vehicle.mode = VehicleMode("GUIDED")
        waypoint = target.get('waymarks')[-2]
        target = LocationGlobal(waypoint.get('lat'), waypoint.get('lng'))
        distanceTo(target)
    print "\t\tAfter"
    print "\t\t\ttarget: %s" % repr(target)

def release(baseID):
    """   """
    m = {'code': RELEASE_MSG, 'id': dev_id, 'addr':XBEE.get('addr')}
    send_message(baseID, json.dumps(m))

def send_msg(data, baseID, nextBaseID):
    print_info(data)
    m = {'code': FORWARD,'id':dev_id, 'base': baseID, "msg": data.get('msg')}
    send_message(nextBaseID, json.dumps(m))

def move_to_base(data):
    global target
    print_info(data)
    vehicle = PIXHAWK['session']
    if fly:
        cmds = vehicle.commands
        #cmds.clear()
        #cmds.upload()

        # Upload the final waypoint
        trgt = target["waymarks"][-1]
        cmd = Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        0, 0, 0, 0, 0, 0,
        trgt.get('lat'), trgt.get('lng'), target['alt'])
        cmds.add(cmd)
        cmds.upload()
        PIXHAWK['session'].mode = VehicleMode("GUIDED")
        # code to translate coordinates into mechanical movements for the pixhawk
        # drone moves to the base
        distanceTo(LocationGlobal(lat=trgt.get('lat'), lon=trgt.get('lng')))

def abort(data):
    print_info(data)
    #Clear the current flight plan
    #TODO Should trace steps back to the central base
    if fly:
        cmds = PIXHAWK['session'].commands
        #cmds.clear()
        #cmds.upload()

        trgt = target['waymarks'][0]
        cmd = Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        0, 0, 0, 0, 0, 0,
        trgt.get('lat'), trgt.get('lng'), target['alt'])
        cmds.add(cmd)
        cmds.upload()
        land()

def reply_status(baseID, nextBaseID):
    coor = get_coordinates()
    m = {'code': CHECK_REQUEST, 'id': dev_id, 'base':nextBaseID, 'lat':coor.get('lat'), 'lng': coor.get('lng')}
    send_message(baseID, json.dumps(m))


def confirm_flight_plan(data):
    global flight_plan
    global flight_stop
    global bases
    print_info(data)
    print "\t\tBefore"
    print "\t\t\tflight_plan: %s" % repr(flight_plan)
    print "\t\t\tflight_stop: %s" % repr(flight_stop)
    print "\t\t\tbases:       %s" % repr(bases)
    flight_stop = 1
    flight_plan = data.get('flight_plan')
    addrs = data.get('addrs')
    for i, base in enumerate(flight_plan):
        bases[base] = {"addr": binascii.unhexlify(addrs[i])}
    print "\t\tAfter"
    print "\t\t\tflight_plan: %s" % repr(flight_plan)
    print "\t\t\tflight_stop: %s" % repr(flight_stop)
    print "\t\t\tbases:       %s" % repr(bases)
    if flight_plan != None:
        m = {'code': START_TAKE_OFF, 'id': dev_id, 'base': flight_plan[flight_stop]}
        send_message(data.get('id'), json.dumps(m))

def arm_and_takeoff(targetAlt):
    vehicle = PIXHAWK['session']
    print vehicle
    #Do not continue until vehicle is ready to accept takeoff and requests
    while not vehicle.is_armable:
        time.sleep(3)

    #Clear any previous commands/missions before takeoff
    if flight_debug: print "Clearing previous commands"
    cmds = vehicle.commands
    #cmds.download()
    #cmds.wait_ready()
    vehicle.commands.clear()
    vehicle.commands.upload()


    #Arm the Vehicle
    if flight_debug: print "Arming motors"
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True
    while not vehicle.armed:
        time.sleep(3)

    #Takeoff
    if flight_debug: print "Taking off! target alt = " + str(targetAlt)
    vehicle.simple_takeoff(targetAlt)

    #Return from function once target altitude is about to be reached
    while True:
        print "Altitude: " + str(vehicle.location.global_relative_frame.alt)
        if vehicle.location.global_relative_frame.alt >= targetAlt *0.95:
            break
        time.sleep(1)
    if flight_debug: print "Target Altitude reached"
    vehicle.mode = VehicleMode("LOITER")
    return

def take_off(data):
    print_info(data)
    target["alt"] = 6 #data.get('alt')
    if fly:
        print "starting arm and take off"
        arm_and_takeoff(target["alt"])
    print "done with take off"

#NOTE: this function is called ONCE THE DRONE HAS REACHED IT'S LANDING LOCATION
def land():
    if fly:
        vehicle = PIXHAWK['session']
        vehicle.mode = VehicleMode("LAND")
        while vehicle.armed:
            time.sleep(1)

    #NOTE: there is nothing here to ensure that the drone has completed it's landing

def idle():
    pass

# Get ID Name
try:
    with open("id.pub") as fn:
        dev_id = fn.read()
except:
    exit("id.pub was not found")

# Get Global ID
try:
    with open("global.pub") as fn:
        glob_id = fn.read()
except:
    exit("global.pub was not found")
# Find PIXHAWK
if fly:
    if find_device(PIXHAWK):
        if not startPIXHAWK(PIXHAWK):
            exit("PIXHAWK Failed to Connect")
    else:
        exit("PIXHAWK not Found")


# Find XBEE
if find_device(XBEE):
    if not startXBEE(XBEE):
        exit("XBEE Failed to Connect")
else:
    exit("XBEE not Found")

# Send Xbee info to Central base
m = {"addr":XBEE.get('addr'), "dev":dev_id}
sp.call(["curl", "-f", "-s", "10.0.1.72:5000/xbee_info", "-X", "POST", "-d", json.dumps(m)], shell=False)


#TODO Uncomment once ready to fly
#if find_device(PIXHAWK):
#    if not startPIXHAWK(PIXHAWK):
#        exit("Pixhawk Failed to Connect")
#else:
#    XBEE.get('session').close()
#    exit("PIXHAWK not Found")

try:
    while run:
        data  = get_next_state()
        code  = data.get('code')

        if len(flight_plan) == 0 and not code == CONFIRM_FP:
            code = IDLE

        if code == IDLE:
            print "IDLE"
            PREV_STATE = IDLE
            idle()
        elif code == CONFIRM_FP:
            print "CONFIRM_FP"
            PREV_STATE = IDLE
            confirm_flight_plan(data)
        elif code == TAKE_OFF:
            print "TAKE_OFF"
            PREV_STATE = TAKE_OFF
            take_off(data)
            PREV_STATE = ASK_DIRECT
        elif code == CONFIRM:
            print "CONFIRM"
            PREV_STATE = IDLE
            ask_for_confirmation(flight_plan[flight_stop])
        elif code == ASK_DIRECT:
            print "ASK_DIRECT"
            PREV_STATE = IDLE
            ask_for_direction(flight_plan[flight_stop-1], flight_plan[flight_stop])
        elif code == DIRECT:
            print "DIRECT"
            PREV_STATE = IDLE
            direct(data)
            PREV_STATE = CONFIRM
        elif code == RELEASE:
            print "RELEASE"
            #TODO Try to Release
            PREV_STATE = IDLE
            release(flight_plan[flight_stop-1])
        elif code == SEND:
            print "SEND"
            PREV_STATE = IDLE
            send_msg(data, flight_plan[flight_stop-1], flight_plan[flight_stop])
        elif code == RELEASE_ACC:
            print "RELEASE_ACC"
            PREV_STATE = IDLE
            flight_stop += 1
            if len(flight_plan) <= flight_stop:
                PREV_STATE = LAND
            else:
                PREV_STATE = ASK_DIRECT
        elif code == MOVE:
            print "MOVE"
            PREV_STATE = IDLE
            move_to_base(data)
            PREV_STATE = RELEASE
        elif code == ABORT:
            print "ABORT"
            PREV_STATE = ABORT
            abort(data)
            flight_stop -= 1
        elif code == REPLY_STATUS:
            print "REPLY_STATUS"
            PREV_STATE = IDLE
            reply_status(dev_id, flight_plan[flight_stop])
        elif code == LAND:
            print 'LAND'
            PREV_STATE = IDLE
            land()
        else:
            print 'error: add code to throw an exception'
        time.sleep(1)
except(KeyboardInterrupt):
    XBEE.get('session').close()
    exit()
