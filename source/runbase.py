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
import random
import string
import json
import time
import gps
import serial.tools.list_ports
import subprocess as sp

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

# Drone Codes
CONFRIM         = 'l'
DIRECT          = 'm'
ASK_DIRECT      = 'n'
RELEASE         = 'o'
SEND            = 'p'
MOVE            = 'q'
ABORT           = 'r'
# Global Variables
enc_file_name   = 'enc.pub'
dec_file_name   = 'dec.pub'
digest          = None
dev_id          = None
glob_id         = None
data            = {'code': IDLE}
mapa            = {}
base            = {}
flight_plan     = ["jvp2@princeton.edu"]
msgs            = {}
debug           = False
run             = True

# GPS Device Information
GPS = {
    "vid": "067B",
    "pid": "2303",
    "port": None,
    "session": None
}

# Get ID Name
try:
    with open("id.pub") as fn:
        dev_id = fn.read()
except:
    print "id.pub was not found"
    exit()

# Get Global Id
try:
    with open("global.pub") as fn:
        glob_id = fn.read()
except:
    print "global.pub was not found"
    exit()

def find_device(device):
    """ Searches system's open ports for the provided device.
        If found, returns true, else false."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == int(device['vid'], 16) and port.pid == int(device['pid'], 16):
            device['port'] = port.device
            return True
    return False

def db(STATE):
    global run
    if debug:
        print STATE
        run = False

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

def broadcast_enc_pub():
    #TODO
    pass

def idle():
    global run
    db(IDLE)

def send_connection_confirmation(data):
    m = {'code': ASK_DIRECT, 'data': 'OK'}
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), data.get('id')))
    db(SEND_CONFIRM)
    broadcast_enc_pub()

def send_directions(data):
    b = base.get(data.get('base'))
    if b == None:
        # Handle Situation when base provided is not in recognized by the base
        m = {
                'code': ABORT
            }
        pass
    else :
        m = {
                'code': DIRECT, 
                'long': base.get(data.get('base')).get('long'),  
                'lat' : base.get(data.get('base')).get('lat'),  
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
            'msg': data.get("msg")
        }
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), data.get('base')))
    db(FORWARD)
    broadcast_enc_pub()

def send_release_acceptance(data):
    m = {'code': MOVE, 'msg':'OK'}
    if data.get('msg') != msgs.get(data.get('id')):
        m['msg'] = 'FAILED'
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), data.get('id')))
    db(RELEASE_ACC)
    broadcast_enc_pub()


def get_state_from_enc_pub():
    global digest
    m = hashlib.md5()
    data = {"code": IDLE}
    if os.path.isfile(enc_file_name):
        with open(enc_file_name) as f:
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
                        print "dec.pub failed to decrypt"
                        exit() 
    return data

def get_coordinates():
    data = {'lat': None, 'lng': None}
    if session != None:
        report = GPS['session'].next()
        if report.get('class') == 'TPV':
            if hasattr(report, 'lat') and hasattr(report, 'lon'):
                data['lat'] = report.lat
                data['lng'] = report.lon
    return data

def send_ping():
    m = {'code': REPLY_PING, 'id': dev_id}
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), glob_id))
    db(PING)
    broadcast_enc_pub()

def send_reply_ping():
    coor = get_coordinates()
    m = {'code': UPDATE, 'id': dev_id, "lat": coor.get('lat'), "lng": coor.get('lng')}
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), glob_id))
    db(REPLY_PING)
    broadcast_enc_pub()

def update_map(data):
    mapa[data.get("id")] = {"lat": data.get("lat"), "lng": data.get("lng")}
    db(UPDATE)

def send_global_ping():
    m = {'code': PROPOGATE, 'id': dev_id, "data":{}, "q": [], "t": [dev_id]}
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), glob_id))
    db(GLOBAL_PING)
    broadcast_enc_pub()
   
def send_propogate(data):
    ID = data.get('id') 
    d = data.get('data') 
    q = data.get('q') 
    t = data.get('t') 
   
    for key in mapa.keys():
        if key not in q and key not in t and data.get(key) == None:
            q.append(key)
    coor = get_coordinates() 
    if d.get(dev_id) == None:
        d[dev_id] = {"lat": coor.get('lat'), "lng": coor.get('lng')} 

    m = {'code': PROPOGATE, 'id': dev_id, "data":d, "q": q}
    if mapa.get(q[0]) == None:
        i = t.pop()
        m['t'] = t
        os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), i))
    else:
        t.append(dev_id)
        m['q'] = q[1:]
        m['t'] = t
        os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), q[0]))
    db(PROPOGATE)
    broadcast_enc_pub()

# Find Devices
if find_device(GPS):
    if not startGPS(GPS):
        print GPS
        print "GPS Connection Failed"
        exit()
else:
    print "GPS not found"
    exit()

while run:
    data = get_state_from_enc_pub()
    code = data.get('code')
    debug = data.get('debug', False)
   
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
        send_reply_ping()
    elif code == UPDATE:
        update_map(data)
    elif code == GLOBAL_PING:
        send_global_ping()
    elif code == PROPOGATE:
        send_propogate(data)
    else:
        print 'Code Not Found'
