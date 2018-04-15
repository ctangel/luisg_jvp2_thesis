#! /usr/bin/python
'''
 * testxbee.py
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
import geopy
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

# Global Variables
enc_file_name   = 'enc.pub'
denc_file_name  = 'denc.pub'
dec_file_name   = 'dec.pub'
db_file_name    = 'deb.pub'
digest          = None
dev_id          = None
glob_id         = None
data            = {'code': IDLE}
base            = {}
drones          = []
msgs            = {}
debug           = False
run             = True
request         = False
ping            = False
base_alt        = 5
dev_alt         = None
dev_lat         = None
dev_lng         = None

# GPS Device Information
GPS = {
    "vid": ["067B","10C4"],
    "pid": ["2303","EA60"],
    "port": None,
    "session": None
}

# XBEE Device Information
XBEE = {
    "vid": ["0403"],
    "pid": ["6015"],
    "port": None,
    "low": None,
    "high":'\x00\x13\xA2\x00',
    "session": None
}


# Get ID Name
#try:
#    with open("id.pub") as fn:
#        dev_id = fn.read()
#except:
#    exit("id.pub was not found")

# Get Global Id
#try:
#    with open("global.pub") as fn:
#        glob_id = fn.read()
#except:
#    exit("global.pub was not found")

def find_device(device):
    """ Searches system's open ports for the provided device.
        If found, returns true, else false."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
      for i in range(len(device['vid'])):
          if port.vid == int(device['vid'][i], 16) and port.pid == int(device['pid'][i], 16):
              device['port'] = str(port.device)
              return True
    return False

def db(STATE):
    """ Used in debuging, will print state machine's current state """
    global run
    if debug:
        with open(db_file_name, 'w') as fn:
            fn.write(STATE)
        #run = False

def get_bearing(lat1, lng1, lat2, lng2):
    """ Returns the bearing (0 - 360 deg) the path between the two supplied GPS cooridates will
        take the drone towards """
    lat1 = math.radians(lat1)
    lng1 = math.radians(lng1)
    lat2 = math.radians(lat2)
    lng2 = math.radians(lng2)
    y = math.sin(lng2-lng1) * math.cos(lat2);
    x = (math.cos(lat1) * math.sin(lat2)) - (math.sin(lat1) * math.cos(lat2) * math.cos(lng2-lng1));
    brng = math.degrees(math.atan2(y, x));
    deg = 360 - ((brng + 360) % 360);
    return ((brng + 360) % 360);

def get_new_coor(lat1, lng1, brng, d):
    """ Returns the new coordinates of a location d kilometers in brng bearing from coordinates
        (lat, lng1) """
    lat1 = math.radians(lat1)
    lng1 = math.radians(lng1)
    R = 6371.0
    lat2 = math.asin((math.sin(lat1)*math.cos(d/R)) + (math.cos(lat1)*math.sin(d/R)*math.cos(math.radians(brng)) ));
    lng2 = lng1 + math.atan2(math.sin(math.radians(brng))*math.sin(d/R)*math.cos(lat1), math.cos(d/R) - (math.sin(lat1)*math.sin(lat2)));
    return {"lat":math.degrees(lat2), "lng":math.degrees(lng2)}

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
    print "starting xbee"
    print "getting session"
    device['session'] = Comms.Comms(device.get('port'), data_only=True)
    print device
    #serial_num = device.get('session').getLocalAddr()
    try:
        time.sleep(1)
        print serial_num
        device['low'] = serial_num[0]
        return True
    except:
        device['session'].stop()
        return False

def idle():
    global run
    db(IDLE)

def send_connection_confirmation(data):
    global drones
    m = {'code': ASK_DIRECT, 'data': 'OK'}
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), data.get('id')))
    if data.get('id') not in drones:
        drones.append(data.get('id'))
    db(SEND_CONFIRM)
    broadcast_enc_pub()

def send_directions(data):
    global base
    b = base.get(data.get('base'))
    if b == None:
        # Handle Situation when base provided is not in recognized by the base
        m = {
                'code': ABORT
            }
        pass
    else:
        # Find open path
        path = None
        for p in b.get("paths"):
            if b.get("paths").get(p) == None:
                path = p
        if path == None:
            exit("All Paths are taken")

        # Generate Path
        b["paths"][p] = data.get('id')
        brng = get_bearing(dev_lat, dev_lng, b.get('lat'), b.get('lng'))
        d = 0.001
        if p == "1":
            left = (brng - 90) % 360
            waymark1 = get_new_coor(lat1, lng1, left, d)
            waymark2 = get_new_coor(b.get('lat'), b.get('lng'), left, d)
            waymarks = [waymark1, waymark2]
        elif p == "2":
            waymarks = [{"lat":b.get('lat'), "lng": b.get('lng')}]
        else:
            right = (brng + 90) % 360
            waymark1 = get_new_coor(lat1, lng1, right, d)
            waymark2 = get_new_coor(b.get('lat'), b.get('lng'), right, d)
            waymarks = [waymark1, waymark2]
        # Send info
        m = {
                'code': DIRECT,
                'waymarks': waymarks,
                'lng': base.get(data.get('base')).get('lng'),
                'lat': base.get(data.get('base')).get('lat'),
                "alt": dev_alt + (base[data.get('base')].get('out') * base_alt)
            }
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), data.get('id')))
    db(SEND_DIRECT)
    broadcast_enc_pub()

def send_release_msg(data):
    m = {
            'code': SEND,
            'msg': 'asdef'
        }
    chars = string.ascii_uppercase + string.digits
    m['msg'] = ''.join(random.choice(chars) for _ in range(12))
    msgs[data.get('id')] = m.get('msg')
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), data.get('id')))
    db(RELEASE_MSG)
    broadcast_enc_pub()

def forward_release_msg(data):
    m = {
            'code': RELEASE_ACC,
            'msg': data.get("msg"),
            'id': data.get('id'),
            'base': dev_id
        }
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), data.get('base')))
    db(FORWARD)
    broadcast_enc_pub()

def send_release_acceptance(data):
    global drones
    global base
    m = {'code': MOVE}
    if data.get('msg') != msgs.get(data.get('id')):
        m['msg'] = 'FAILED'
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), data.get('id')))
    if data.get('id') in drones:
        drones.remove(data.get('id'))
    for p in base[data.get('base')].get('paths'):
        if base[data.get('base')].get('paths').get(p) == data.get('id'):
            base[data.get('base')]['paths'][p] = None
    db(RELEASE_ACC)
    broadcast_enc_pub()

def get_coordinates():
    data = {'lat': None, 'lng': None}
    if GPS.get('session') != None:
        report = GPS['session'].next()
        if report.get('class') == 'TPV':
            if hasattr(report, 'lat') and hasattr(report, 'lon'):
                data['lat'] = report.lat
                data['lng'] = report.lon
                data['alt'] = report.alt
    return data

def send_ping():
    global ping
    ping = False
    coor = get_coordinates()
    m = {'code': REPLY_PING, 'id': dev_id, "low":XBEE.get('low'), "route":1, "lat":coor.get('lat'), "lng":coor.get('lng'), "alt":coor.get('alt')}
    for b in base:
        if base[b].get("check") == None:
            base[b]['check'] = 2
        else:
            if base[b].get("check") == 0:
                del base[b]
            else:
                base[b]['check'] = base[b]['check'] - 1
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), glob_id))
    db(PING)
    broadcast_enc_pub()

def send_reply_ping(data):
    coor = get_coordinates()
    if base.get(data.get('id')) == None:
        # add to the base with out route 1 and in route 2
        base[data.get('id')] = {
                "lat":data.get('lat'),
                "lng":data.get('lng'),
                "alt":data.get('alt'),
                "low":data.get('low'),
                "in":1,
                "out":2,
                "paths": {
                        "1": None,
                        "2": None,
                        "3": None
                    }
            }
        m = {'code': UPDATE, 'id': dev_id, "low":XBEE.get('low'), "lat": coor.get('lat'), "lng": coor.get('lng'), "alt":coor.get('alt'), "route":2}
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), data.get('id')))
    db(REPLY_PING)
    broadcast_enc_pub()

def update_map(data):
    coor = get_coordinates()
    if base.get(data.get('id')) == None:
        # add to the base with out route 1 and in route 2
        base[data.get('id')] = {
                "lat":data.get('lat'),
                "lng":data.get('lng'),
                "alt":data.get('alt'),
                "low":data.get('low'),
                "in":2,
                "out":1,
                "paths": {
                        "1": None,
                        "2": None,
                        "3": None
                    }
            }
    # reset
    if base.get(data.get('id')).get('check') != None:
        base[data.get('id')]['check'] = 2
        #base[data.get("id")]['lat'] = data.get("lat")
        #base[data.get("id")]['lng'] = data.get("lng")
        #base[data.get("id")]['alt'] = data.get("alt")
    db(UPDATE)

def send_global_ping():
    m = {'code': PROPOGATE, 'og':dev_id, 'id': dev_id, "data":{}, "q": [], "t": [dev_id]}
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), glob_id))
    db(GLOBAL_PING)
    broadcast_enc_pub()

def send_propogate(data):
    ID = data.get('id')
    d = data.get('data')
    q = data.get('q')
    t = data.get('t')

    for key in base.keys():
        if key not in q and key not in t and data.get(key) == None:
            q.append(key)
    coor = get_coordinates()
    if d.get(dev_id) == None:
        d[dev_id] = {"lat": coor.get('lat'), "lng": coor.get('lng'), "alt":coor.get('alt'), "links":base.keys()}

    m = {'code': PROPOGATE, 'og':data.get('og'), 'id': dev_id, "data":d, "q": q}
    if base.get(q[0]) == None:
        i = t.pop()
        m['t'] = t
        os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), i))
    else:
        t.append(dev_id)
        m['q'] = q[1:]
        m['t'] = t
        os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), q[0]))

    db(PROPOGATE)
    if not dev_id == data.get('og'):
        broadcast_enc_pub()
    else:
        d[dev_id] = {"lat": coor.get('lat'), "lng": coor.get('lng'), "alt":coor.get('alt'), "links":base.keys()}
        with open('map.pub', 'w') as fn:
            fn.write(json.dumps(d))
"""
    {
        "a": {"lat": 0, "lng": 0, "alt": 0, "links":[]},
        "b": {"lat": 0, "lng": 0, "alt": 0, "links":[]},
        "c": {"lat": 0, "lng": 0, "alt": 0, "links":[]}
    }
"""
def start_take_off(data):
    m = {
            'code': TAKE_OFF,
            'lat': base.get(data.get('base')).get('lat'),
            "lng": base.get(data.get('base')).get('lat'),
            "alt": dev_alt + (base[data.get('base')].get('out') * base_alt)
        }
    #TODO could benefit from send_direct code for horizontal laning
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), data.get('id')))
    db(START_TAKE_OFF)
    broadcast_enc_pub()

def send_flight_plan(data):
    m = {
            'code': CONFIRM_FP,
            'flight_plan': data.get('flight_plan')
        }
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), data.get('id')))
    db(SEND_FP)
    broadcast_enc_pub()

def trigger_request():
    global request
    threading.Timer(100, trigger_request)
    request = True

def trigger_ping():
    global ping
    threading.Timer(100, trigger_ping)
    ping = True


def request_status():
    global request
    for drone in drones:
        m = {
            'code': REPLY_STATUS,
            'id': dev_id
            }
        os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), drone))
        broadcast_enc_pub()
    request = False

def check_status(data):
   coors = get_coordinates()
   coor1 = (coors.get('lat'), coors.get('lng'))
   coor2 = (data.get('lat'), data.get('lng'))
   if not geopy.distance.distance(coor1, coor2).miles > 0:
       send_directon(data)
       pass

# Find Devices
#if find_device(GPS):
#    if not startGPS(GPS):
#        print GPS
#        exit("GPS Failed to Connect")
#else:
#    print "GPS not found"
#    exit()

print "finding xbee"
if find_device(XBEE):
    print "found, starting it up"
    print XBEE
    if not startXBEE(XBEE):
        print XBEE
        exit("XBEE Failed to Connect")
else:
    print "Xbee found"
    exit()

#TODO Trun back one
#trigger_request()
#trigger_ping()

# On bootup, send Ping
send_ping()


def broadcast_enc_pub(dest=None, broadcast=False):
    with open(enc_file_name) as fn:
        data = fn.read()
    if base.get(dest) != None:
        dest_addr = XBEE.get('high') + base.get('low')
        if not broadcast:
            XBEE.get('session').sendData(dest_addr, data)
        else:
             XBEE.get('session').broadcastData(data)
    else:
        exit("Failed to send")
def get_state_from_enc_pub():
    global digest
    m = hashlib.md5()
    data = {"code": IDLE}
    # read a file called enc.pub
    if not XBEE.get('session').isMailBoxEmpty():
        data = XBEE.get('session').readMessage()
        with open(denc_file_name, 'w') as fn:
            fn.write(data)

    # instead -> grab data from queue and decode
    if os.path.isfile(denc_file_name):
        with open(denc_file_name) as f:
            m.update(f.read())
            if digest != m.digest():
                digest = m.digest()
                # Try dev_id
                os.system("./decrypt %s < param/a3.param" % (dev_id))
                try:
                    with open(dec_file_name) as ff:
                        data = json.load(ff)
                except:
                    # Try glob_id
                    os.system("./decrypt %s < param/a3.param" % (glob_id))
                    try:
                        with open(dec_file_name) as ff:
                            data = json.load(ff)
                    except:
                        pass
                        #exit("dec.pub failed to decrypt")
    return data

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

    # set timer to fire send_ping()
    if code == IDLE:
        idle()
    elif code == SEND_CONFIRM:
        send_connection_confirmation(data)
    elif code == SEND_DIRECT:
        send_directions(data)
    elif code == RELEASE_MSG:
        send_release_msg(data)
    elif code == FORWARD:
        forward_release_msg(data)
    elif code == RELEASE_ACC:
        send_release_acceptance(data)
    elif code == PING:
        send_ping()
    elif code == REPLY_PING:
        send_reply_ping(data)
    elif code == UPDATE:
        update_map(data)
    elif code == GLOBAL_PING:
        send_global_ping()
    elif code == PROPOGATE:
        send_propogate(data)
    elif code == START_TAKE_OFF:
        start_take_off(data)
    elif code == SEND_FP:
        send_flight_plan(data)
    elif code == CHECK_STATUS:
        check_status(data)
    else:
        pass
        #print 'Code Not Found'
