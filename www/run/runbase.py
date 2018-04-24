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
import serial.tools.list_ports
import subprocess as sp
import Comms
from gps3 import gps3 as gps

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
LAND            = 'z'

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
base_alt        = 1
dev_coor        = None
disableGPS      = True

# GPS Device Information
GPS = {
    "vid": ["067B","10C4"],
    "pid": ["2303","EA60"],
    "port": None,
    "session": `None`
}

# XBEE Device Information
XBEE = {
    "vid":      ["0403", "10C4"],
    "pid":      ["6015", "EA60"],
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

def get_distance(coor1, coor2):
    pos1 = (coor1.get('lat'), coor1.get('lng'))
    pos2 = (coor2.get('lat'), coor2.get('lng'))
    return distance.distance(pos1, pos2).kilometers


def get_coordinates():
    data = {'lat': None, 'lng': None, 'alt':None}
    if not disableGPS:
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
    else:
        data = {'lat': 40.7357, 'lng': -74.1724, 'alt':3}
    return data

def trigger_request():
    global request
    threading.Timer(100, trigger_request)
    request = True

def trigger_ping():
    global ping
    #threading.Timer(10, trigger_ping)
    ping = True

def startGPS(device):
    """ Sets up and establishes a connection with the provided gps device.
        If connection is successful, it returns true, else false"""
    # Checking if GPS is Connected to Socket
    if disableGPS:
        return True
    try:
        os.system("/usr/local/sbin/gpsd %s" % (device['port']))
        os.system("/usr/sbin/gpsd %s" % (device['port']))
        device['session'] = gps.GPSDSocket()
        device['session'].connect()
        device['session'].watch()
    except:
        # GPS Failed to Connect to Socket
        return False

    while True:
        time.sleep(1)
        report = device['session'].next()
        if report != None:
            report = json.loads(report)
            if report.get('class') == "TPV":
                break
    return True

def startXBEE(device):
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

def get_state_from_enc_pub():
    """ Checks if messages exists, if so, then is reads them in """
    global digest
    m = hashlib.md5()
    data = {"code": IDLE}
    msg = {}
    print "/// *** %d" % XBEE.get('session').messageCount()
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
    print "\t\tSending...:"
    jdata = json.loads(data)
    for key in jdata:
        print "\t\t\t%s\t\t%s" % (key, repr(jdata.get(key)))
    if dest == glob_id:
        print "\t\tsending to %s at %s" % (dest, repr(Comms.Comms.BROADCAST))
        XBEE.get('session').sendData(Comms.Comms.BROADCAST, data, None, dest)
    elif bases.get(dest) != None:
        print "\t\tsending to %s at %s" % (dest, repr(bases.get(dest).get('addr')))
        XBEE.get('session').sendData(bases.get(dest).get('addr'), data, None, dest)
    elif drones.get(dest) != None:
        print "\t\tsending to %s at %s" % (dest, repr(drones.get(dest).get('addr')))
        XBEE.get('session').sendData(drones.get(dest).get('addr'), data, None, dest)
    else:
        print "\t\t/*** Failed to send"
        #exit("Failed to send")

def print_info(data):
    print "\t\tReceived..."
    for key in data:
        print "\t\t\t%s\t\t%s" %(key, repr(data.get(key)))

#
#   State Methods
#

def idle():
    global run
    db(IDLE)

def send_connection_confirmation(data):
    global drones
    print_info(data)
    print "\t\tBefore"
    print "\t\t\tdrone: %s" % repr(drones)
    m = {'code': ASK_DIRECT, 'id': dev_id, 'data': 'OK'}
    if data.get('id') not in drones:
        drones[data.get('id')] = {"addr": binascii.unhexlify(data.get('addr'))}
    print "\t\tAfter"
    print "\t\t\tdrones: %s" % repr(drones)
    db(SEND_CONFIRM)
    broadcast_enc_pub(data.get('id'), json.dumps(m))

def send_directions(data):
    global bases
    print_info(data)
    print "\t\tBefore"
    print "\t\t\tbases: %s" % repr(bases)
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
        waymarks = []
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
    print "\t\tAfter"
    print "\t\t\tbases: %s" % repr(bases)
    db(SEND_DIRECT)
    broadcast_enc_pub(data.get('id'), json.dumps(m))

def send_release_msg(data):
    global msgs
    global drones
    print_info(data)
    print "\t\tBefore"
    print "\t\t\tmsgs:   %s" % repr(msgs)
    print "\t\t\tdrones: %s" % repr(drones)
    m = {'code': SEND, 'msg': 'asdef', "id": dev_id}
    drones[data.get('id')] = {'addr':binascii.unhexlify(data.get('addr'))}
    chars = string.ascii_uppercase + string.digits
    m['msg'] = ''.join(random.choice(chars) for _ in range(12))
    msgs[data.get('id')] = m.get('msg')
    print "\t\tAfter"
    print "\t\t\tmsgs:   %s" % repr(msgs)
    print "\t\t\tdrones: %s" % repr(drones)
    db(RELEASE_MSG)
    broadcast_enc_pub(data.get('id'), json.dumps(m))

def forward_release_msg(data):
    print_info(data)
    print "\t\tBefore"
    print "\t\t\tmsgs:   %s" % repr(msgs)
    print "\t\t\tdrones: %s" % repr(drones)
    m = {
            'code': RELEASE_ACC,
            'msg': data.get("msg"),
            'id': data.get('id'),
            'base': dev_id
        }
    db(FORWARD)
    print "\t\tAfter"
    print "\t\t\tmsgs:   %s" % repr(msgs)
    print "\t\t\tdrones: %s" % repr(drones)
    broadcast_enc_pub(data.get('base'), json.dumps(m))

def send_release_acceptance(data):
    global drones
    global bases
    print_info(data)
    print "\t\tBefore"
    print "\t\t\tbases:  %s" % repr(bases)
    print "\t\t\tdrones: %s" % repr(drones)
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
    print "\t\tAfter"
    print "\t\t\tbases:  %s" % repr(bases)
    print "\t\t\tdrones: %s" % repr(drones)

def send_ping():
    global ping
    global bases
    ping = False
    print "\t\tBefore"
    print "\t\t\tbases: %s" % repr(bases)
    m = {"code": REPLY_PING,
            "id": dev_id,
            "addr":XBEE.get('addr'),
            "route":1,
            "lat":dev_coor.get('lat'),
            "lng":dev_coor.get('lng'),
            "alt":dev_coor.get('alt')}
    bases_copy = dict(bases)
    for b in bases_copy:
        if bases[b].get("check") == None:
            bases[b]['check'] = 2
        else:
            if bases[b].get("check") == 0:
                del bases[b]
            else:
                bases[b]['check'] = bases[b]['check'] - 1
    print "\t\tAfter"
    print "\t\t\tbases: %s" % repr(bases)
    broadcast_enc_pub(glob_id, json.dumps(m))

def send_reply_ping(data):
    print bases
    print_info(data)
    print "\t\tBefore"
    print "\t\t\tbases: %s" % repr(bases)
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
    m = {
            'code': UPDATE,
            'id': dev_id,
            "addr":XBEE.get('addr'),
            "lat": dev_coor.get('lat'),
            "lng": dev_coor.get('lng'),
            "alt": dev_coor.get('alt'),
            "route":2
        }
    print "\t\tAfter"
    print "\t\t\tbases: %s" % repr(bases)
    broadcast_enc_pub(data.get('id'), json.dumps(m))
    #TODO   Bases is cleared when a system goes down. Hence, when it reboots and sends a ping, the others won't reply with their information.
    #       we need to have the others send a reply.
    #       This could lead to cycle of send_replies. May need a new state that updates but does not reply
    db(REPLY_PING)

def update_map(data):
    global bases
    print_info(data)
    print "\t\tBefore"
    print "\t\t\tbases: %s" % repr(bases)
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
    if bases.get(data.get('id')).get('check') != None:
        bases[data.get('id')]['check'] = 2
    db(UPDATE)
    print "\t\tAfter"
    print "\t\t\tbases: %s" % repr(bases)

def send_global_ping():
    m = {'code': PROPOGATE, 'og':dev_id, 'id': dev_id, "data":{}, "q": [], "t": []}
    db(GLOBAL_PING)
    broadcast_enc_pub(glob_id, json.dumps(m))

def send_propogate(data):
    print_info(data)
    ID = data.get('id')
    d = data.get('data')    # data
    q = data.get('q')       # queue of bases to visit
    t = data.get('t')       # trace of path taken
    for key in bases.keys():
        # add based to queue only if does not exist in queue, trace, and data
        if key not in q and key not in t and data.get(key) == None:
            q.append(key)
    if d.get(dev_id) == None:
        d[dev_id] = {"lat": dev_coor.get('lat'), "lng": dev_coor.get('lng'), "alt": dev_coor.get('alt'), "links":bases.keys()}

    if dev_id == data.get('og'):
        d[dev_id] = {"lat": dev_coor.get('lat'), "lng": dev_coor.get('lng'), "alt": dev_coor.get('alt'), "links":bases.keys()}
        data = []
        for key in d:
            d.get(key)["base"] = key
            data.append(d.get(key))
        #TODO Needs to check if 1. New data's bases exists in existing map. If so, the value need to be updated with the new ones. 
        if os.path.isfile('map.pub'):
           with open('map.pub') as fn:
            existing_map = json.load(fn)
            for m in existing_map:
                if m not in data:
                    data.append(m)
 
        with open('map.pub', 'w') as fn:
            fn.write(json.dumps(data))
        return

    m = {'code': PROPOGATE, 'og':data.get('og'), 'id': dev_id, "data":d, "q": q, "t":t}
    #TODO Pending more tests, this closed out programs
    if len(t) != 0:
        if len(q) == 0:
            # if queue is empty, go back in trace
            i = t.pop()
            m['t'] = t
            recipient = i
        elif bases.get(q[0]) == None:
            # if queue item 1 exists in bases, go back in trace
            i = t.pop()
            m['t'] = t
            recipient = i
        else:
            t.append(dev_id)
            m['q'] = q[1:]
            m['t'] = t
            recipient = q[0]

    db(PROPOGATE)
    #TODO Could fail, may need glob_id instead of recipient
    #broadcast_enc_pub(recipient, json.dumps(m))
    broadcast_enc_pub(glob_id, json.dumps(m))

def start_take_off(data):
    print_info(data)
    if data.get('base') == None:
        #TODO Send Abort, the base the drone asked for exist
        return
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
    print_info(data)
    print "\t\tBefore"
    print "\t\t\tdrones: %s" % repr(drones)
    m = {
            'code': CONFIRM_FP,
            'flight_plan': data.get('flight_plan'),
            'addrs': data.get('addrs'),
            'drone': data.get('drone'),
            'id': dev_id
        }
    drones[data.get('drone')] = {"addr": binascii.unhexlify(data.get('addr'))}
    db(SEND_FP)
    print "\t\tAfter"
    print "\t\t\tdrones: %s" % repr(drones)
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
    print_info(data)
    coor1 = (dev_coor.get('lat'), dev_coor.get('lng'))
    coor2 = (data.get('lat'), data.get('lng'))
    if not distance.distance(coor1, coor2).miles > 0:
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

print "/*** Starting Base"
print "\tdev_id  \t%s" % dev_id
print "\tglob_id \t%s" % glob_id

# Find GPS
if disableGPS or find_device(GPS):
    if not startGPS(GPS):
        exit("GPS Failed to Connect")
else:
    exit("GPS not found")

if GPS.get('session') == None:
    print '\tGPS not found'
else:
    print "\tGPS found at %s" % GPS.get('port')

# Find XBEE
if find_device(XBEE):
    if not startXBEE(XBEE):
        exit("XBEE Failed to Connect")
else:
    exit("XBEE not Found")

if XBEE.get('session') == None:
    print '\tXBEE not found'
else:
    print "\tXBEE found at %s" % XBEE.get('port')
    print "\t\taddr: %s" % repr(XBEE.get('addr'))

# Send Xbee info to Central base
m = {"addr":XBEE.get('addr'), "dev":dev_id}
sp.call(["curl", "-f", "-s", "10.0.1.72:5000/xbee_info", "-X", "POST", "-d", json.dumps(m)], shell=False)

dev_coor = get_coordinates()
print "\tStarting Position"
print "\t\tlatitude:  %f" % dev_coor.get('lat')
print "\t\tlongitude: %f" % dev_coor.get('lng')
print "\t\taltitude:  %f" % dev_coor.get('alt')


print "\tStarting triggers"
# Start Triggers
#TODO Turn back one
#trigger_request()
trigger_ping()

#print "\tSending Startup Ping"
# On bootup, send Ping
#send_ping()
timer = 0
print "\n/*** Starting Machine"
try:
    while run:
        data = get_state_from_enc_pub()
        code = data.get('code')
        debug = data.get('debug', False)

        # Every Once in a while, check in with all drones currentlying moving
        if request:
            request_status()

        # Once in while, check try to update base map
        if ping or (timer % 10000) == 0:
            print "\tPING"
            timer = 0
            send_ping()

        # Send Flight Plan if available
        if os.path.isfile("flight_plan.pub"):
            with open("flight_plan.pub") as fn:
                fp_data = json.load(fn)
            print "\tSEND_FP"
            send_flight_plan(fp_data)
            os.remove("flight_plan.pub")

        # Send Global Ping if available
        if os.path.isfile("update.pub"):
            with open("update.pub") as fn:
                fp_data = json.load(fn)
            print "\tGLOBAL_PING"
            send_global_ping()
            os.remove("update.pub")

        if code == IDLE:
            #print "\tIDLE"
            idle()
        elif code == SEND_CONFIRM:
            print "\n\tSEND_CONFIRM"
            send_connection_confirmation(data)
        elif code == SEND_DIRECT:
            print "\n\tSEND_DIRECT"
            send_directions(data)
        elif code == RELEASE_MSG:
            print "\n\tRELEASE_MSG"
            send_release_msg(data)
        elif code == FORWARD:
            print "\n\tFORWARD"
            forward_release_msg(data)
        elif code == RELEASE_ACC:
            print "\n\tRELEASE_ACC"
            send_release_acceptance(data)
        elif code == PING:
            print "\n\tPING"
            send_ping()
        elif code == REPLY_PING:
            print "\n\tREPLY_PING"
            send_reply_ping(data)
        elif code == UPDATE:
            print "\n\tUPDATE"
            update_map(data)
        elif code == GLOBAL_PING:
            print "\n\tGLOBAL_PING"
            send_global_ping()
        elif code == PROPOGATE:
            print "\n\tPROPOGATE"
            send_propogate(data)
        elif code == START_TAKE_OFF:
            print "\n\tSTART_TAKE_OFF"
            start_take_off(data)
        elif code == SEND_FP:
            print "\n\tSEND_FP"
            send_flight_plan(data)
        elif code == CHECK_STATUS:
            print "\n\tCHECK_STATUS"
            check_status(data)
        else:
            pass
        time.sleep(1)
        timer += 1
except(KeyboardInterrupt):
    XBEE.get('session').close()
    exit()
