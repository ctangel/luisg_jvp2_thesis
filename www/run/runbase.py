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
#import geopy
import binascii
import time
#import gps
import serial.tools.list_ports
import subprocess as sp
import Comms

# CODES
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

# Drone Codes
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

# Global Variables
db_file_name    = 'deb.pub'
digest          = None
dev_id          = None
glob_id         = None
data            = {'code': IDLE}
bases           = {}
drones          = {}
msgs            = {}
debug           = False
run             = True
request         = False
ping            = False
base_alt        = 5
dev_coor        = None

# GPS Device Information
GPS = {
    "vid": ["067B","10C4"],
    "pid": ["2303","EA60"],
    "port": None,
    "session": `None`
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

def db(STATE):
    """ Used in debuging, will print state machine's current state """
    global run
    if debug:
        with open(db_file_name, 'w') as fn:
            fn.write(STATE)
        #run = False

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

def get_distance(coor1, coo2):
    return geopy.distance.distance(coor1, coor2).kilometers


def get_coordinates():
    data = {'lat': None, 'lng': None}
    #TODO Remove, used in tested
    return {"lat": 40.3470190911147, "lng":-74.66142010205618}
    if GPS.get('session') != None:
        report = GPS['session'].next()
        if report.get('class') == 'TPV':
            if hasattr(report, 'lat') and hasattr(report, 'lon'):
                data['lat'] = report.lat
                data['lng'] = report.lon
                data['alt'] = report.alt
    return data


def trigger_request():
    global request
    threading.Timer(100, trigger_request)
    request = True

def trigger_ping():
    global ping
    threading.Timer(100, trigger_ping)
    ping = True

def startGPS(device):
    """ Sets up and establishes a connection with the provided gps device.
        If connection is successful, it returns true, else false"""
    # Checking if GPS is Connected to Socket
    try:
        child = sp.Popen("pgrep -a gpsd", shell=True, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
        output, err = child.communicate()
        if device['port'] not in output and output != '':
            # Killing Existing GPS Socket Connection
            os.system("sudo killall -q gpsd")

        if device['port'] not in output:
            # Connecting GPS to Socket
            os.system("gpsd %s" % (device['port']))
    except:
        # GPS Failed to Connect to Socket
        return False

    # Checking if gps session is valid
    while True:
        time.sleep(1)
        try:
            device['session'] = gps.gps("localhost", "2947")
            break
        except:
            sp.check_call("sudo killall -q gpsd", shell=True)
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
        device['addr'] = binascii.hexlify(addr[0] + addr[1])
        return True
    except:
        device['session'].close()
        return False

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
        print "sendingi to %s" % dest 
        print drones.get(dest).get('addr')
        XBEE.get('session').sendData(drones.get(dest).get('addr'), data, None, dest)
    else:
        print "Failed to send"
        #exit("Failed to send")

#
#   State Methods
#

def idle():
    global run
    db(IDLE)

def send_connection_confirmation(data):
    global drones
    m = {'code': ASK_DIRECT, 'id': dev_id, 'data': 'OK'}
    if data.get('id') not in drones:
        drones[data.get('id')] = {"addr": binascii.unhexlify(data.get('addr'))}
    db(SEND_CONFIRM)
    broadcast_enc_pub(data.get('id'), json.dumps(m))

def send_directions(data):
    global bases
    b = bases.get(data.get('base'))
    if b == None:
        #TODO Handle Situation when base provided is not in recognized by the base
        m = {'code': ABORT, "id": dev_id}
    else:
        # Find open path
        path = None
        for p in b.get("paths"):
            if b.get("paths").get(p) == None:
                path = p
        if path == None:
            #TODO   Do not exit, properly handle case when all paths are take
            #       Consider having the drone hover in place or land and wait
            #       until a path frees up
            exit("All Paths are taken")

        # Generate Path
        b["paths"][p] = data.get('id')
        origin = {"lat":dev_coor.get('lat'), "lng":dev_coor.get('lng')}
        target = {"lat":b.get('lat'), "lng":b.get('lng')}
        brng = get_bearing(origin, target)
        d = 0.001
        if p == "1":
            left = (brng - 90) % 360
            waymarks.append(get_new_coor(origin, left, d))
            dist = get_distance(waymarks[0], target)
            third = dist / 3.0
            remainder = dist - third
            waymarks.append(get_new_coor(waymarks[0], 0, third))
            waymarks.append(get_new_coor(waymarks[1], 0, remainder))
        elif p == "2":
            dist = get_distance(origin, target)
            third = dist / 3.0
            remainder = dist - third
            waymarks.append(get_new_coor(origin, 0, third))
            waymarks.append(get_new_coor(waymarks[0], 0, remainder))
        else:
            right = (brng + 90) % 360
            waymarks.append(get_new_coor(origin, right, d))
            dist = get_distance(waymarks[0], target)
            third = dist / 3.0
            remainder = dist - third
            waymarks.append(get_new_coor(waymarks[0], 0, third))
            waymarks.append(get_new_coor(waymarks[1], 0, remainder))
        # Send info
        m = {
                'code': DIRECT,
                'waymarks': waymarks,
                'id': dev_id,
                'lng': bases.get(data.get('base')).get('lng'), #FIXME: get rid of old way
                'lat': bases.get(data.get('base')).get('lat'), #FIXME: get rid of old way
                'alt': dev_coor.get('alt') + (bases[data.get('base')].get('out') * base_alt)
            }
    db(SEND_DIRECT)
    broadcast_enc_pub(data.get('id'), json.dumps(m))

def send_release_msg(data):
    global msgs
    m = {'code': SEND, 'msg': 'asdef', "id": dev_id}
    chars = string.ascii_uppercase + string.digits
    m['msg'] = ''.join(random.choice(chars) for _ in range(12))
    msgs[data.get('id')] = m.get('msg')
    db(RELEASE_MSG)
    broadcast_enc_pub(data.get('id'), json.dumps(m))

def forward_release_msg(data):
    m = {
            'code': RELEASE_ACC,
            'msg': data.get("msg"),
            'id': data.get('id'),
            'base': dev_id
        }
    db(FOWARD)
    broadcast_enc_pub(data.get('base'), json.dumps(m))

def send_release_acceptance(data):
    global drones
    global bases
    m = {'code': MOVE}
    if data.get('msg') != msgs.get(data.get('id')):
        m['msg'] = 'FAILED'
    for p in bases[data.get('base')].get('paths'):
        if bases[data.get('base')].get('paths').get(p) == data.get('id'):
            bases[data.get('base')]['paths'][p] = None
    db(RELEASE_ACC)
    broadcast_enc_pub(data.get('id'), json.dumps(m))
    if data.get('id') in drones:
        del drones[data.get('id')]

def send_ping():
    global ping
    ping = False
    print "\tprepping message..."
    m = {"code": REPLY_PING,
            "id": dev_id,
            "addr":XBEE.get('addr'),
            "route":1,
            "lat":dev_coor.get('lat'),
            "lng":dev_coor.get('lng'),
            "alt":dev_coor.get('alt')}
    print "\tchecking base records..."
    for b in bases:
        if bases[b].get("check") == None:
            bases[b]['check'] = 2
        else:
            if bases[b].get("check") == 0:
                del bases[b]
            else:
                bases[b]['check'] = bases[b]['check'] - 1
    print "\tbroadcasting..."
    broadcast_enc_pub(glob_id, json.dumps(m))

def send_reply_ping(data):
    print "\tsaving information..."
    print bases
    if bases.get(data.get('id')) == None:
        # add to the base with out route 1 and in route 2
        bases[data.get('id')] = {
                "lat":data.get('lat'),
                "lng":data.get('lng'),
                "alt":data.get('alt'),
                "addr":binascii.unhexlify(data.get('addr')),
                "in":1,
                "out":2,
                "paths": {
                        "1": None,
                        "2": None,
                        "3": None
                    }
            }
        print "\tpreppring message..."
        m = {
                'code': UPDATE,
                'id': dev_id,
                "addr":XBEE.get('addr'),
                "lat": dev_coor.get('lat'),
                "lng": dev_coor.get('lng'),
                "alt": dev_coor.get('alt'),
                "route":2
            }
        print bases
        print "\tsending to %s..." % data.get('id')
        broadcast_enc_pub(data.get('id'), json.dumps(m))
    #TODO   Bases is cleared when a system goes down. Hence, when it reboots and sends a ping, the others won't reply with their information. 
    #       we need to have the others send a reply. 
    #       This could lead to cycle of send_replies. May need a new state that updates but does not reply
    db(REPLY_PING)

def update_map(data):
    global bases
    print "\tupdating map..."
    print bases
    if bases.get(data.get('id')) == None:
        # add to the base with out route 1 and in route 2
        bases[data.get('id')] = {
                "lat":data.get('lat'),
                "lng":data.get('lng'),
                "alt":data.get('alt'),
                "addr":binascii.unhexlify(data.get('addr')),
                "in":2,
                "out":1,
                "paths": {
                        "1": None,
                        "2": None,
                        "3": None
                    }
            }
    # reset
    print "updated"
    if bases.get(data.get('id')).get('check') != None:
        bases[data.get('id')]['check'] = 2
    print bases
    db(UPDATE)

def send_global_ping():
    m = {'code': PROPOGATE, 'og':dev_id, 'id': dev_id, "data":{}, "q": [], "t": []}
    db(GLOBAL_PING)
    broadcast_enc_pub(glob_id, json.dumps(m))

def send_propogate(data):
    ID = data.get('id')
    d = data.get('data')    # data
    q = data.get('q')       # queue of bases to visit
    t = data.get('t')       # trace of path taken
    print "\tpropogating..."
    print d
    print q
    print t
    print "\tcycling through keys..."
    for key in bases.keys():
        print "\t%s..." % key
        # add based to queue only if does not exist in queue, trace, and data
        if key not in q and key not in t and data.get(key) == None:
            q.append(key)
    print "\tchecking if dev_id exist...."
    if d.get(dev_id) == None:
        print "\tit didn't"
        d[dev_id] = {"lat": dev_coor.get('lat'), "lng": dev_coor.get('lng'), "alt": dev_coor.get('alt'), "links":bases.keys()}
    
    if dev_id == data.get('og'):
        print "\tBack at OG!"
        d[dev_id] = {"lat": dev_coor.get('lat'), "lng": dev_coor.get('lng'), "alt": dev_coor.get('alt'), "links":bases.keys()}
        print d
        data = []
        for key in d:
            d.get(key)["base"] = key
            data.append(d.get(key))
        with open('map.pub', 'w') as fn:
            fn.write(json.dumps(data))
        return
 
    print "\tprepping message..."
    m = {'code': PROPOGATE, 'og':data.get('og'), 'id': dev_id, "data":d, "q": q, "t":t}
    #TODO Pending more tests, this closed out programs
    if len(q) == 0:
        # if queue is empty, go back in trace
        i = t.pop()
        m['t'] = t
        recipient = i
    elif bases.get(q[0]) == None:
        # if queue item 1 exists in bases, go back in trace
        print "\toption 1..."
        i = t.pop()
        m['t'] = t
        recipient = i
    else:
        print "\toption2..."
        t.append(dev_id)
        m['q'] = q[1:]
        m['t'] = t
        recipient = q[0]

    db(PROPOGATE)
    print "\tpropogating to %s" % recipient
    print m
    #TODO Could fail, may need glob_id instead of recipient
    #broadcast_enc_pub(recipient, json.dumps(m))
    broadcast_enc_pub(glob_id, json.dumps(m))

def start_take_off(data):
    m = {
            'code': TAKE_OFF,
            'lat': bases.get(data.get('base')).get('lat'),
            "lng": bases.get(data.get('base')).get('lat'),
            "alt": dev_coor.get('alt') + (bases[data.get('base')].get('out') * base_alt),
            'id': dev_id
        }
    #TODO add drone to internal memory
    #TODO could benefit from send_direct code for horizontal laning
    db(START_TAKE_OFF)
    broadcast_enc_pub(data.get('id'), json.dumps(m))

def send_flight_plan(data):
    global drones
    print "sending flight plan"
    print data
    m = {
            'code': CONFIRM_FP,
            'flight_plan': data.get('flight_plan'),
            'addrs': data.get('addrs'),
            'drone': data.get('drone'),
            'id': dev_id
        }
    print m
    drones[data.get('drone')] = {"addr": binascii.unhexlify(data.get('addr'))}
    db(SEND_FP)
    broadcast_enc_pub(data.get('drone'), json.dumps(m))

def request_status():
    global request
    for drone in drones:
        m = {
            'code': REPLY_STATUS,
            'id': dev_id
            }
        broadcast_enc_pub(drone, json.dumps(m))
    request = False

def check_status(data):
   coor1 = (dev_coor.get('lat'), dev_coor.get('lng'))
   coor2 = (data.get('lat'), data.get('lng'))
   if not geopy.distance.distance(coor1, coor2).miles > 0:
       send_directon(data)
       pass

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

# Find GPS
#if find_device(GPS):
#    if not startGPS(GPS):
#        exit("GPS Failed to Connect")
#else:
#    exit("GPS not found")

# Find XBEE
if find_device(XBEE):
    if not startXBEE(XBEE):
        exit("XBEE Failed to Connect")
else:
    exit("XBEE not Found")

# Send Xbee info to Central base
m = {"addr":XBEE.get('addr'), "dev":dev_id}
sp.call(["curl", "-f", "-s", "10.0.1.72:5000/xbee_info", "-X", "POST", "-d", json.dumps(m)], shell=False)

dev_coor = get_coordinates()
print dev_coor
# Start Triggers
#TODO Turn back one
#trigger_request()
#trigger_ping()

# On bootup, send Ping
send_ping()
print "dank"
try:
    while run:
        data = get_state_from_enc_pub()
        code = data.get('code')
        debug = data.get('debug', False)

        # Every Once in a while, check in with all drones currentlying moving
        if request:
            request_status()

        # Once in while, check try to update base map
        if ping:
            send_ping()

        # Send Flight Plan if available
        if os.path.isfile("flight_plan.pub"):
            with open("flight_plan.pub") as fn:
                fp_data = json.load(fn)
            send_flight_plan(fp_data)
            os.remove("flight_plan.pub")

        # Send Global Ping if available
        if os.path.isfile("update.pub"):
            print "update.pub found!"
            with open("update.pub") as fn:
                fp_data = json.load(fn)
            print "GLOBAL_PING"
            send_global_ping()
            os.remove("update.pub")


        if code == IDLE:
            print "IDLE"
            idle()
        elif code == SEND_CONFIRM:
            print "SEND_CONFIRM"
            send_connection_confirmation(data)
        elif code == SEND_DIRECT:
            print "SEND_DIRECT"
            send_directions(data)
        elif code == RELEASE_MSG:
            print "RELEASE_MSG"
            send_release_msg(data)
        elif code == FORWARD:
            print "FORWARD"
            forward_release_msg(data)
        elif code == RELEASE_ACC:
            print "RELEASE_ACC"
            send_release_acceptance(data)
        elif code == PING:
            print "PING"
            send_ping()
        elif code == REPLY_PING:
            print "REPLY_PING"
            send_reply_ping(data)
        elif code == UPDATE:
            print "UPDATE"
            update_map(data)
        elif code == GLOBAL_PING:
            print "GLOBAL_PING"
            send_global_ping()
        elif code == PROPOGATE:
            print "PROPOGATE"
            send_propogate(data)
        elif code == START_TAKE_OFF:
            print "STATE_TAKE_OFF"
            start_take_off(data)
        elif code == SEND_FP:
            print "SEND_FP"
            send_flight_plan(data)
        elif code == CHECK_STATUS:
            print "CHECK_STATUS"
            check_status(data)
        else:
            pass
        time.sleep(1)
except(KeyboardInterrupt):
    XBEE.get('session').close()
    exit()
