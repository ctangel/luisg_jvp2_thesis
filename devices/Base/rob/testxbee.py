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
import binascii
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
    "vid":      ["067B","10C4"],
    "pid":      ["2303","EA60"],
    "port":     None,
    "session":  None
}

# XBEE Device Information
XBEE = {
    "vid":      ["0403"],
    "pid":      ["6015"],
    "port":     None,
    "addr":      None,
    "session":  None
}


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
print dev_id
print glob_id
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

def startXBEE(device):
    try:
        device['session'] = Comms.Comms(device.get('port'), data_only=True)
        addr = device.get('session').getLocalAddr()
        time.sleep(1)
        device['addr'] = binascii.hexlify(addr[0] + addr[1])
        print device
        return True
    except:
        device['session'].close()
        return False

def broadcast_enc_pub(dest=None, broadcast=False):
    print "Broadcasting..."
    with open(enc_file_name) as fn:
        data = fn.read()
    hdata = binascii.hexlify(data)
    if broadcast:
        print "global"
        print data
        #XBEE.get('session').broadcastData("{'code': 'z'}")
        print binascii.hexlify(data)
        XBEE.get('session').broadcastData(hdata)
    elif base.get(dest) != None:
        print dest
        dest_addr = binascii.unhexlify(XBEE.get('addr'))
        XBEE.get('session').sendData(dest_addr, hdata)
    else:
        exit("Failed to send")

def idle():
    global run
    db(IDLE)

def send_ping():
    global ping
    print "Sending Ping..."
    ping = False
    coor = {"lat": 12, "lng":34}
    m = {'code': REPLY_PING, 'id': dev_id,
            "addr":XBEE.get('addr'),
            "route":1,
            "lat":coor.get('lat'),
            "lng":coor.get('lng'),
            "alt":coor.get('alt')}
    for b in base:
        if base[b].get("check") == None:
            base[b]['check'] = 2
        else:
            if base[b].get("check") == 0:
                del base[b]
            else:
                base[b]['check'] = base[b]['check'] - 1
    print "encrypting message..."
    sp.call("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), glob_id), shell=True)
    db(PING)
    broadcast_enc_pub(broadcast=True)

def send_reply_ping(data):
    print "Sending Ping Reply..."
    coor = get_coordinates()
    if base.get(data.get('id')) == None:
        # add to the base with out route 1 and in route 2
        base[data.get('id')] = {
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
        m = {'code': UPDATE, 'id': dev_id, "addr":XBEE.get('addr'), "lat": coor.get('lat'), "lng": coor.get('lng'), "alt":coor.get('alt'), "route":2}
    os.system("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), data.get('id')))
    db(REPLY_PING)
    broadcast_enc_pub(base.get(data.get('id')).get('addr'))

def update_map(data):
    if base.get(data.get('id')) == None:
        # add to the base with out route 1 and in route 2
        base[data.get('id')] = {
                "lat":data.get('lat'),
                "lng":data.get('lng'),
                "alt":data.get('alt'),
                "addr":binascii.unhexlify(data.get('sddr')),
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
    db(UPDATE)

if find_device(XBEE):
    if not startXBEE(XBEE):
        exit("XBEE Failed to Connect")
else:
    exit("Xbee not found")

# On bootup, send Ping
send_ping()

def get_state_from_enc_pub():
    global digest
    m = hashlib.md5()
    data = {"code": IDLE}
    # read a file called enc.pub
    if not XBEE.get('session').isMailboxEmpty():
        print "You have mail!"
        data = XBEE.get('session').readMessage()
        print data
        print binascii.unhexlify(data)
        udata = binascii.unhexlify(data)
        with open(denc_file_name, 'wb') as fn:
            fn.write(udata)

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
                print data
    return data


try:
    while run:
        data = get_state_from_enc_pub()
        code = data.get('code')
        debug = data.get('debug', False)

        # set timer to fire send_ping()
        if code == IDLE:
            idle()
        elif code == PING:
            send_ping()
        elif code == REPLY_PING:
            send_reply_ping(data)
        elif code == UPDATE:
            update_map(data)
        else:
            pass
            #print 'Code Not Found'
except (KeyboardInterrupt):
    XBEE.get('session').close()
    exit("closed")
