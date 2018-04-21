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
from dronekit import connect, VehicleMode, LocationGlobal
from pymavlink import mavutil
import argparse, sys


#TODO: This thing needs to land....
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
data            = {'code': CONFIRM}
flight_plan     = []
flight_stop     = 1
bases           = {}
drones          = {}
PREV_STATE      = CONFIRM
run             = True
debug           = False
dev_id          = None
glob_id         = None
target          = {"lat":None, "lng":None, "alt":None}
fly             = False

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
    "vid":      ["0403"],
    "pid":      ["6015"],
    "port":     None,
    "addr":     None,
    "session":  None
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


# Drone has its own GPS so we will have to give it a specialized code
# The rest will be using the GPS Ultimate module

def db(STATE):
    global run
    if debug:
        print STATE
        run = False

def startPIXHAWK(device):
    try:
        device['session'] = connect(device['port'], baud=device['baud'], wait_ready=True)
        sleep(5)
    except:
        return False

def startXBEE(device):
    try:
        device['session'] = Comms.Comms(device.get('port'), data_only=True)
        addr = device.get('session').getLocalAddr()
        time.sleep(1)
        device['addr'] = binascii.hexlify(addr[0] + addr[1])
        return True
    except:
        device['session'].close()
        return False

def get_coordinates():
    ans = {}
    ans['lat'] = PIXHAWK['session'].location.global_frame.lat
    ans['lng'] = PIXHAWK['session'].location.global_frame.lon
    ans['alt'] = PIXHAWK['session'].location.global_frame.alt
    return ans

def get_state_from_enc_pub():
    """ Checks if messages exists, if so, then is reads them in """
    global digest
    m = hashlib.md5()
    data = {"code": IDLE}
    msg = {}
    if not XBEE.get('session').isMailboxEmpty():
        msg = XBEE.get('session').readMessage()
        if msg == None:
            return data
        msg = msg.get('rx')
        m.update(msg)
        if digest != m.digest():
            digest = m.digest()
            try:
                data = json.loads(msg)
            except:
                print "\t\tpass"
                pass
    return data

def broadcast_enc_pub(dest=None, data=None):
    print bases
    print drones
    if dest == glob_id:
        XBEE.get('session').sendData(Comms.Comms.BROADCAST, data, None, dest)
    elif bases.get(dest) != None:
        XBEE.get('session').sendData(bases.get(dest).get('addr'), data, None, dest)
    elif drones.get(dest) != None:
        print "sending to %s at %s" % (dest, repr(drones.get(dest).get('addr')))
        XBEE.get('session').sendData(drones.get(dest).get('addr'), data, None, dest)
    else:
        print "Failed to send"
        #exit("Failed to send")

def print_info(data):
    print "\t\tReceived..."
    for key in data:
        print "\t\t\t%s\t\t%s" %(key, repr(data.get(key)))
 

#
#   State Machtine
#

def broadcast_to_base(baseID):
    m = {'code': SEND_CONFIRM, 'seq':'1', 'id': dev_id, "addr":XBEE.get('addr')}
    db(CONFIRM)
    broadcast_enc_pub(baseID, json.dumps(m))

def ask_for_direction(baseID, nextBaseID):
    # request base for direction to next base
    m = {'code': SEND_DIRECT, 'base': nextBaseID, 'id': dev_id}
    db(ASK_DIRECT)
    broadcast_enc_pub(baseID, json.dumps(m))

def direct(data):
    #checkout send_directions() in runbase.py
    global target
    print "\t\tBefore"
    print "\t\t\ttarget: %s" % repr(target)    
    print_info(data)
    if fly:
        viehicle = PIXHAWK['session']
    target["waymarks"] = data.get('waymarks')
    target["alt"] = data.get('alt') #NOTE: Altitude will never change with waymarks
    db(DIRECT)
    # code to translate coordinates into mechanical movements for the pixhawk
    # ideally the drone moves to the halfway mark to prepare for release()
    if fly:
        #Remove any previous waypoints
        cmds = vehicle.commands
        cmds.clr()
        cmds.upload()

        for point in target['waymarks'][:-1]:
            cmd = Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
            0, 0, 0, 0, 0, 0,
            point.get('lat'), point.get('lon'), target['alt'])
            #TODO: is this the correct format for waymarks?
            cmds.add(cmd)
        cmds.upload()
        vehicle.mode = VehicleMode("GUIDED")
    print "\t\tAfter"
    print "\t\t\ttarget: %s" % repr(target)    
    
    """
            msg = vehicle.message_factory.set_position_target_global_int_encode(
            0,       # time_boot_ms (not used)
            0, 0,    # target system, target component
            mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT, # frame
            0b0000111111111000, # type_mask (only speeds enabled)
            aLocation.lat*1e7, # lat_int - X Position in WGS84 frame in 1e7 * meters
            aLocation.lon*1e7, # lon_int - Y Position in WGS84 frame in 1e7 * meters
            aLocation.alt, # alt - Altitude in meters in AMSL altitude, not WGS84 if absolute or relative, above terrain if GLOBAL_TERRAIN_ALT_INT
            0, # X velocity in NED frame in m/s
            0, # Y velocity in NED frame in m/s
            0, # Z velocity in NED frame in m/s
            0, 0, 0, # afx, afy, afz acceleration (not supported yet, ignored in GCS_Mavlink)
            0, 0)    # yaw, yaw_rate (not supported yet, ignored in GCS_Mavlink)
            # send command to vehicle
            vehicle.send_mavlink(msg)
    """
    """
        waymark = [{"lat":b.get('lat'), "lng": b.get('lng')}]
    """

def release(baseID):
    m = {'code': RELEASE_MSG, 'id': dev_id, 'addr':XBEE.get('addr')}
    db(RELEASE)
    broadcast_enc_pub(baseID, json.dumps(m))

def send_msg(data, baseID, nextBaseID):
    print_info(data)
    m = {'code': FORWARD,'id':dev_id, 'base': baseID, "msg": data.get('msg')}
    db(SEND)
    broadcast_enc_pub(nextBaseID, json.dumps(m))

def move_to_base(data):
    print_info(data)
    # Upload the final waypoint
    trgt = target["waymarks"][-1]
    db(MOVE)
    if fly:
        cmd = Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        0, 0, 0, 0, 0, 0,
        trgt.get('lat'), trgt.get('lon'), target['alt'])
        cmds.add(cmd)
        cmds.upload()
        PIXHAWK['session'].mode = VehicleMode("GUIDED")
        # code to translate coordinates into mechanical movements for the pixhawk
        # drone moves to the base

def abort(data):
    print_info(data)
    #Clear the current flight plan
    if fly:
        cmds = PIXHAWK['session'].commands
        cmds.clr()
        cmds.upload()

        trgt = target['waymarks'][0]
        cmd = Command(0,0,0, mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT, mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
        0, 0, 0, 0, 0, 0,
        trgt.get('lat'), trgt.get('lon'), target['alt'])
        cmds.add(cmd)
        cmds.upload()
        PIXHAWK['session'].mode = VehicleMode("GUIDED")
        db(ABORT)

def reply_status(baseID, nextBaseID):
    coor = get_coordinates()
    m = {'code': CHECK_REQUEST, 'id': dev_id, 'base':nextBaseID, 'lat':coor.get('lat'), 'lng': coor.get('lng')}
    db(REPLY_STATUS)
    broadcast_enc_pub(baseID, json.dumps(m))


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
        db(CONFIRM_FP)
        broadcast_enc_pub(data.get('id'), json.dumps(m))

def arm_and_takeoff(targetAlt):
    vehicle = PIXHAWK['session']

    #Do not continue until vehicle is ready to accept takeoff and requests
    while not vehicle.is_armable:
        time.sleep(3)

    #Clear any previous commands/missions before takeoff
    cmds = vehicle.commands
    cmds.download()
    cmds.wait_ready()
    vehicle.commands.clr()
    vehicle.commands.upload()


    #Arm the Vehicle
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True
    while not vehicle.armed:
        time.sleep(3)

    #Takeoff
    vehicle.simple_takeoff(targetAlt)

    #Return from function once target altitude is about to be reached
    while True:
        if vehicle.location.global_frame.alt >= targetAlt *0.95:
            break
        sleep(1)

    return

def take_off(data):
    print_info(data)
    target["alt"] = data.get('alt')
    if fly:
        arm_and_takeoff(target["alt"])
    db(TAKE_OFF)

#NOTE: this function is called ONCE THE DRONE HAS REACHED IT'S LANDING LOCATION
def land():
    if fly:
        PIXHAWK['session'].mode = VehicleMode("LAND")
    #NOTE: there is nothing here to ensure that the drone has completed it's landing

def idle():
    db(IDLE)

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
        data  = get_state_from_enc_pub()
        code  = data.get('code')
        debug = data.get('debug', False)

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
            PREV_STATE = MOVE
        elif code == CONFIRM:
            print "CONFIRM"
            PREV_STATE = CONFIRM
            broadcast_to_base(dev_id, flight_plan[flight_stop])
        elif code == ASK_DIRECT:
            print "ASK_DIRECT"
            PREV_STATE = IDLE
            ask_for_direction(flight_plan[flight_stop-1], flight_plan[flight_stop])
        elif code == DIRECT:
            print "DIRECT"
            PREV_STATE = DIRECT
            direct(data)
            PREV_STATE = RELEASE
        elif code == RELEASE:
            print "RELEASE"
            PREV_STATE = IDLE
            release(flight_plan[flight_stop-1])
        elif code == SEND:
            print "SEND"
            PREV_STATE = IDLE
            send_msg(data, flight_plan[flight_stop-1], flight_plan[flight_stop])
        elif code == MOVE:
            print "MOVE"
            PREV_STATE = MOVE
            move_to_base(data)
            flight_stop += 1
            if len(flight_plan) <= flight_stop:
                PREV_STATE = LAND
            else:
                PREV_STATE = CONFIRM
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
