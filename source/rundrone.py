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

# CODES
CONFIRM         = 'l'
DIRECT          = 'm'
ASK_DIRECT      = 'n'
RELEASE         = 'o'
SEND            = 'p'
MOVE            = 'q'

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

enc_file_name   = 'enc.pub'
dec_file_name   = 'dec.pub'
digest          = None
message         = ' '
ID              = 'fnewaj@princeton.edu'
data            = {'code': CONFIRM}
flight_plan     = ["jvp2@princeton.edu", "h"]
flight_stop     = 0;
PREV_STATE      = CONFIRM
run             = True
debug           = False

# Read ID from id.pub and store in id var
# with open("id.pub", "r") as f:
#    ID = f.read()


def db(STATE):
    global run
    if debug:
        print STATE
        run = False

def broadcast_enc_pub():
    #TODO
    pass

def broadcast_to_base(ID, baseID):
    m = {'code': SEND_CONFIRM, 'seq':'1', 'id': ID}
    os.system("./encrypt '%s' %s < param/a3.param" % (json.dumps(m), baseID))
    db(CONFIRM)
    broadcast_enc_pub()

def ask_for_direction(baseID, nextBaseID):
    # request base for direction to next base
    m = {'code': SEND_DIRECT, 'base': nextBaseID}
    os.system("./encrypt '%s' %s < param/a3.param" % (json.dumps(m), baseID))
    db(ASK_DIRECT)
    broadcast_enc_pub()

def direct(data):     
    lng = data.get('lng')
    lat = data.get('lat')
    db(DIRECT)
    # code to translate coordinates into mechanical movements for the pixhawk
    # ideally the drone moves to the halfway mark to prepare for release()
    #TODO

def release(ID, baseID):
    m = {'code': RELEASE_MSG, 'id': ID}
    os.system("./encrypt '%s' %s < param/a3.param" % (json.dumps(m), baseID))
    db(RELEASE)
    broadcast_enc_pub()

def send_msg(data, baseID, nextBaseID):
    m = {'code': FORWARD, 'base': baseID, "msg": data.get('msg')}
    os.system("./encrypt '%s' %s < param/a3.param" % (json.dumps(m), nextBaseID))
    db(SEND)
    broadcast_enc_pub()

def move_to_base(data):
    lng = data.get('lng')
    lat = data.get('lat')
    db(MOVE)
    # code to translate coordinates into mechanical movements for the pixhawk
    # drone moves to the base
    #TODO

def get_state_from_enc_pub():
    global digest
    m = hashlib.md5()
    data = {"code": PREV_STATE}
    if os.path.isfile(enc_file_name):
        with open(enc_file_name) as f:
            m.update(f.read())
            if digest != m.digest():
                digest = m.digest()
                os.system('./decrypt < param/a3.param')
                with open(dec_file_name) as ff:
                    data = json.load(ff);
    return data

while run:
    #print "start"
    data  = get_state_from_enc_pub()
    code  = data.get('code')
    debug = data.get('debug', False)
    #print "mid"
    if code == CONFIRM:
        PREV_STATE = CONFIRM
        broadcast_to_base(ID, flight_plan[flight_stop])
    elif code == ASK_DIRECT:
        PREV_STATE = ASK_DIRECT
        ask_for_direction(flight_plan[flight_stop], flight_plan[flight_stop+1])
    elif code == DIRECT:
        PREV_STATE = DIRECT
        direct(data)
        PREV_STATE = RELEASE
    elif code == RELEASE: 
        PREV_STATE = RELEASE
        release(ID, flight_plan[flight_stop])
    elif code == SEND:
        PREV_STATE = SEND
        send_msg(data, flight_plan[flight_stop], flight_plan[flight_stop+1])
    elif code == MOVE:
        PREV_STATE = MOVE
        move_to_base(data)
        flight_stop += 1
    else:
        print 'error: add code to throw an exception'
