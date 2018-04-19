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
import binascii
import time
import gps
import serial.tools.list_ports
import Comms


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
flight_stop     = 0;
bases           = {}
PREV_STATE      = CONFIRM
run             = True
debug           = False
dev_id          = None
glob_id         = None
target          = {"lat":None, "lng":None, "alt":None}

# GPS Device Information
GPS = {
    "vid": ["067B","10C4"],
    "pid": ["2303","EA60"],
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

def startGPS(device):
    """ Sets up and establishes a connection with the provided gps device.
        if connection is successfull, it returns true, else false """
    # Checking if GPS is Connected to a Socket
    try:
        child = sp.Popen("pgrep -s gpsd", shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
        output, err = child.communicate()
        if device['port'] not in output and output != '':
            # Kills Existing GPS Socket Connection
            os.system("sudo killall -q gpsd")
        if device['port'] not in output:
            # Connect GPS to a Socket
            os.system("gpsd %s" % (device['port']))
    except:
        # GPS Failed to Connect to a socket
        return False

    # Check if GPS session is valid
    while True:
        time.sleep(1)
        try:
            device['session'] = gps.gps('localhost', '2947')
            break
        except:
            sp.check_all("sudo killall -q gpsd", shell=True)
            os.system("gpsd %s" % (device['port']))
    device['session'].stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
    report = device['session'].next()

    # Locking onto GPS
    while report.get('mode') != 3:
        time.sleep(1)
        report = device['session'].next()
    return True

def startXBEE(device):
    try:
        device['session'] = Comms.Comms(device.get('port'), data_only=True)
        addr = device.get('session').getLocalAddr()
        time.sleep(1)
        device['addr'] = addr[0] + addr[1]
        return True
    except:
        device['session'].close()
        return False


def get_coordinates():
    #TODO
    pass

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
    if dest == glob_id:
        #TODO Add glob_id as input to broadcastData
        XBEE.get('session').broadcastData(data)
    elif bases.get(dest) != None:
        XBEE.get('session').sendData(bases.get(dest).get('addr'), data, None, dest)
    elif drones.get(dest) != None:
        XBEE.get('session').sendData(drones.get(dest).get('addr'), data, None, dest)
    else:
        print "Failed to send"
        #exit("Failed to send")


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
    broadcast_enc_pub(baseID, json.dump(m))

def direct(data):
    global target
    target["waymarks"] = data.get('waymarks')
    target["lng"] = data.get('lng')
    target["lat"] = data.get('lat')
    target["alt"] = data.get('alt')
    db(DIRECT)
    # code to translate coordinates into mechanical movements for the pixhawk
    # ideally the drone moves to the halfway mark to prepare for release()
    #TODO

def release(baseID):
    m = {'code': RELEASE_MSG, 'id': dev_id}
    db(RELEASE)
    broadcast_enc_pub(baseID, json.dumps(m))

def send_msg(data, baseID, nextBaseID):
    m = {'code': FORWARD,'id':dev_id, 'base': baseID, "msg": data.get('msg')}
    db(SEND)
    broadcast_enc_pub(newBaseID, json.dumps(m))

def move_to_base(data):
    # Use Target
    target["waymarks"]
    db(MOVE)
    # code to translate coordinates into mechanical movements for the pixhawk
    # drone moves to the base
    #TODO

def abort(data):
    #TODO figure how to about a mission (as in move back to home base)
    db(ABORT)
    pass

def reply_status(baseID, nextBaseID):
    coor = get_coordinates()
    m = {'code': CHECK_REQUEST, 'id': dev_id, 'base':nextBaseID, 'lat':coor.get('lat'), 'lng': coor.get('lng')}
    db(REPLY_STATUS)
    broadcast_enc_pub(baseID, json.dumps(m))


def confirm_flight_plan(data):
    global flight_plan
    global flight_stop
    global flight_plan
    global bases
    flight_stop = 0
    flight_plan = data.get('flight_plan')
    addrs = data.get('addrs')
    for i, base in eneruate(flight_plan):
        bases[base] = {"addr": addrs[i]}

    if flight_plan != None:
        m = {'code': CONFIRM_FP, 'id': dev_id, 'base': flight_plan[flight_stop]}
        db(CONFIRM_FP)
        broadcast_enc_pub(data.get('id'), json.dumps(m))

def take_off(data):
    target["lat"] = data.get('lat')
    target["lng"] = data.get('lng')
    target["alt"] = data.get('alt')
    #TODO Add Take Off Code here
    #TODO Consider calling move_to_base from here
    db(TAKE_OFF)

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

# Send Xbee info to Central base
m = {"addr":XBEE.get('addr'), "dev":dev_id}
sp.call(["curl", "-f", "-s", "localhost:5000/xbee_info", "-X", "POST", "-d", json.dumps(m)], shell=False)

# Find XBEE
if find_device(XBEE):
    if not startXBEE(XBEE):
        exit("XBEE Failed to Connect")
else:
    exit("XBEE not Found")

try:
    while run:
        data  = get_state_from_enc_pub()
        code  = data.get('code')
        debug = data.get('debug', False)

        if len(flight_plan) == 0 and not code == SEND_FP:
            code = IDLE

        if code == IDLE:
            PREV_STATE = IDLE
            idle()
        elif code == CONFIRM_FP:
            PREV_STATE = CONFIRM_FP
            confirm_flight_plan(data)
        elif code == TAKE_OFF:
            PREV_STATE = TAKE_OFF
            take_off()
            PREV_STATE = MOVE
        elif code == CONFIRM:
            PREV_STATE = CONFIRM
            broadcast_to_base(dev_id, flight_plan[flight_stop])
        elif code == ASK_DIRECT:
            PREV_STATE = ASK_DIRECT
            ask_for_direction(flight_plan[flight_stop], flight_plan[flight_stop+1])
        elif code == DIRECT:
            PREV_STATE = DIRECT
            direct(data)
            PREV_STATE = RELEASE
        elif code == RELEASE:
            PREV_STATE = RELEASE
            release(dev_id, flight_plan[flight_stop])
        elif code == SEND:
            PREV_STATE = SEND
            send_msg(data, flight_plan[flight_stop], flight_plan[flight_stop+1])
        elif code == MOVE:
            PREV_STATE = MOVE
            move_to_base(data)
            flight_stop += 1
            PREV_STATE = CONFIRM
        elif code == ABORT:
            PREV_STATE = ABORT
            abort(data)
            flight_stop -= 1
        elif code == REPLY_STATUS:
            PREV_STATE = IDLE
            reply_status(dev_id, flight_plan[flight_stop])
        else:
            print 'error: add code to throw an exception'
except(KeyboardInterrupt):
    XBEE.get('session').close()
    exit()
