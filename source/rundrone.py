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
ABORT           = 'r'
TAKE_OFF        = 's'
CONFIRM_FP      = 't'
REPLY_STATUS    = 'w'

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
PREV_STATE      = CONFIRM
run             = True
debug           = False
dev_id          = None
glob_id         = None

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

def find_device(device):
    """ Searches system's open ports for the provided device.
        If found, returns true, else false """
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if port.vid == int(device['vid'], 16) and port.pid == int (device['pid'], 16):
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

def get_coordinates():
    #TODO
    pass

def reply_status(baseID, nextBaseID):
    coor = get_coordinates()
    m = {'code': CHECK_REQUEST, 'id': dev_id, 'base':nextBaseID, 'lat':coor.get('lat'), 'lng': coor.get('lng')}
    os.system("./encrypt '%s' %s < param/a3.param" % (json.dumps(m), baseID))
    db(REPLY_STATUS)
    broadcast_enc_pub()



def broadcast_enc_pub():
    #TODO
    pass

def broadcast_to_base(dev_id, baseID):
    m = {'code': SEND_CONFIRM, 'seq':'1', 'id': dev_id}
    os.system("./encrypt '%s' %s < param/a3.param" % (json.dumps(m), baseID))
    db(CONFIRM)
    broadcast_enc_pub()

def ask_for_direction(baseID, nextBaseID):
    # request base for direction to next base
    m = {'code': SEND_DIRECT, 'base': nextBaseID, 'id': baseID}
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

def release(dev_id, baseID):
    m = {'code': RELEASE_MSG, 'id': dev_id}
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

def abort(data):
    #TODO figure how to about a mission (as in move back to home base)
    db(ABORT)
    pass

def confirm_flight_plan(data):
    global flight_plan
    global flight_stop
    flight_stop = 0
    flight_plan = data.get('flight_plan')
    if flight_plan != None:
        m = {'code': CONFIRM_FP, 'id': dev_id, 'base': flight_plan[flight_stop]}
        os.system("./encrypt '%s' %s < param/a3.param" % (json.dumps(m), dev_id))
        db(CONFIRM_FP)
        broadcast_enc_pub()
    pass

def take_off(data):
    lat = data.get('lat')
    lng = data.get('lng')
    #TODO Add Take Off Code here
    #TODO Consider calling move_to_base from here
    db(TAKE_OFF)

def idle():
    db(IDLE)

def get_state_from_enc_pub():
    global digest
    m = hashlib.md5()
    data = {"code": PREV_STATE}
    if os.path.isfile(enc_file_name):
        with open(enc_file_name) as f:
            m.update(f.read())
            if digest != m.digest():
                digest = m.digest()
                os.system('./decrypt %s < param/a3.param' % (dev_id))
                try:
                    with open(dec_file_name) as ff:
                        data = json.load(ff)
                except:
                    os.system('./decrypt %s < param/a3.param' % (glob_id))
                    try:
                        with open(dec_file_name) as ff:
                            data = json.load(ff)
                    except:
                        exit("dec.pub failed to decrypt")
    return data

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
