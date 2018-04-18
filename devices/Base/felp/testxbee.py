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
PING            = 'g'

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

def get_state_from_enc_pub():
    global digest
    m = hashlib.md5()
    data = {"code": IDLE}
    # read a file called enc.pub
    if not XBEE.get('session').isMailboxEmpty():
        print "You have mail!"
        da = XBEE.get('session').readMessage().get('rx')
        print da
        print binascii.unhexlify(da)
        udata = binascii.unhexlify(da)
        with open(denc_file_name, 'wb') as fn:
            fn.write(udata)
    #time.sleep(5)
    # instead -> grab data from queue and decode
    if os.path.isfile(denc_file_name):
        with open(denc_file_name) as f:
            m.update(f.read())
            if digest != m.digest():
                digest = m.digest()
                # Try dev_id
                print "tyring id..."
                os.system("./decrypt %s < param/a3.param" % (dev_id))
                try:
                    with open(dec_file_name) as ff:
                        data = json.load(ff)
                except:
                    # Try glob_id
                    print "trying global id..."
                    os.system("./decrypt %s < param/a3.param" % (glob_id))
                    try:
                        with open(dec_file_name) as ff:
                            data = json.load(ff)
                    except:
                        print "pass"
                        pass
                        #exit("dec.pub failed to decrypt")
                print data
    return data


def broadcast_enc_pub(dest=None, broadcast=False, data=None):
    print "Broadcasting..."
    #with open(enc_file_name) as fn:
    #    data = fn.read()
    #hdata = binascii.hexlify(data)
    print data
    if broadcast:
        #XBEE.get('session').broadcastData("{'code': 'z'}")
        XBEE.get('session').broadcastData(data)
    elif base.get(dest) != None:
        print dest
        dest_addr = binascii.unhexlify(XBEE.get('addr'))
        XBEE.get('session').sendData(dest_addr, hdata)
    else: 
        XBEE.get('session').sendData(binascii.unhexlify(dest), hdata)
        #exit("Failed to send")

def idle():
    global run

def send_ping():
    global ping
    ping = False
    coor = {"lat": 12, "lng":34}
    m = {"code": "luis is here", 
            "id": dev_id,
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
    m = {"code": "daasdfasdfnk"}
    h = sp.check_output("./encrypt '%s' %s  < param/a3.param" % (json.dumps(m), glob_id), shell=True)
    print h
    broadcast_enc_pub(broadcast=True, data=h)
    #broadcast_enc_pub("0013a2004175bc91")

if find_device(XBEE):
    if not startXBEE(XBEE):
        exit("XBEE Failed to Connect")
else:
    exit("Xbee not found")

# On bootup, send Ping
send_ping()

print "/***** Starting Machine"
try:
    while run:
        data = get_state_from_enc_pub()
        code = data.get('code')
        debug = data.get('debug', False)
        
        if code == IDLE:
            print "\tIDLE"
            idle()
        elif code == PING:
            print "\tPING"
            send_ping()
        else:
            print "pass"
            pass
        time.sleep(1)
except (KeyboardInterrupt):
    XBEE.get('session').close()
    exit("closed")
