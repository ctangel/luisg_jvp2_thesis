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
import hashlib, os, threading, random
import string, json, math, binascii
import time, serial.tools.list_ports, subprocess as sp
import Comms
from geopy import distance
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
digest          = None
dev_id          = None
glob_id         = None
data            = {'code': IDLE}
bases           = {}
drones          = {}
msgs            = {}
run             = True
request         = False
ping            = False
base_alt        = 1
dev_coor        = None
disableGPS      = True
debug           = True

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
          dev_vid = int(device['vid'][i], 16)
          dev_pid = int(device['pid'][i], 16)
          if port.vid == dev_vid and port.pid == dev_pid:
              device['port'] = port.device
              return True
    return False

def get_bearing(origin, target):
    """ Returns the bearing (0 - 360 deg) the path between the two supplied GPS
        cooridates will take the drone towards """
    lat1    = math.radians(origin.get('lat'))
    lng1    = math.radians(origin.get('lng'))
    lat2    = math.radians(target.get('lat'))
    lng2    = math.radians(target.get('lng'))
    y       = math.sin(lng2-lng1) * math.cos(lat2)
    xleft   = math.cos(lat1) * math.sin(lat2)
    xright  = math.sin(lat1) * math.cos(lat2) * math.cos(lng2-lng1)
    x       = xleft - xright
    brng    = math.degrees(math.atan2(y, x));
    deg     = 360 - ((brng + 360) % 360);
    return  (brng + 360) % 360

def get_new_coor(coor, brng, d):
    """ Returns the new coordinates of a location d kilometers in brng bearing
        from coordinates (lat, lng1) """
    lat1        = math.radians(coor.get('lat'))
    lng1        = math.radians(coor.get('lng'))
    R           = 6371.0
    lat2left    = math.sin(lat1) * math.cos(d/R)
    lat2right   = math.cos(lat1) * math.sin(d/R) * math.cos(math.radians(brng))
    lat2        = math.asin(lat2left + lat2right)
    lng2left    = math.sin(math.radians(brng)) * math.sin(d/R) * math.cos(lat1)
    lng2right   = math.cos(d/R) - (math.sin(lat1) * math.sin(lat2))
    lng2        = lng1 + math.atan2(lng2left, lng2right)
    return      {"lat":math.degrees(lat2), "lng":math.degrees(lng2)}

def get_distance(coor1, coor2):
    """ Returns the distance between coor1 and coor2 in kilometers """
    pos1 = (coor1.get('lat'), coor1.get('lng'))
    pos2 = (coor2.get('lat'), coor2.get('lng'))
    return distance.distance(pos1, pos2).kilometers


def get_coordinates():
    """ Return a dictionary with latitude, longitude, and altitude obtained
        from the GPS  """
    data = {'lat': 40.7357, 'lng': -74.1724, 'alt':3} # Dummy Data
    if not disableGPS and GPS.get('session') != None:
        while True:
            time.sleep(1)
            report = GPS['session'].next()
            print report
            if report != None:
                report = json.loads(report)
                if report.get('class') == "TPV":
                    if report.get('lat') != None and report.get('lon') != None:
                        # Update Dummy Data with real GPS coordinates
                        data['lat'] = report.get('lat')
                        data['lng'] = report.get('lon')
                        data['alt'] = report.get('alt')
                        break
    return data

#TODO   Using Threading to launch a trigger does not appear to work.
#       Consider removing these functions
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
    if disableGPS:
        return True
    try:
        os.system("/usr/local/sbin/gpsd %s" % (device['port']))
        os.system("/usr/sbin/gpsd %s" % (device['port']))
        device['session'] = gps.GPSDSocket()
        device['session'].connect()
        device['session'].watch()
    except:
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
    """ Sets up and establishes a connection with the provided xbee device.
        If connection is successful, it returns true, else false """
    try:
        device['session']   = Comms.Comms(device.get('port'), data_only=True)
        addr                = device.get('session').getLocalAddr()
        time.sleep(1)
        device['addr']      = binascii.hexlify(addr[0] + addr[1])
        return True
    except:
        if device.get('session') != None:
            device['session'].close()
        return False

def get_next_state():
    """ Checks if messages exists, if so, then is reads them in
        and returns it """
    data    = {"code": IDLE}
    msg     = {}
    print "/// *** %d" % XBEE.get('session').messageCount()
    if not XBEE.get('session').isMailboxEmpty():
        msg     = XBEE.get('session').readMessage()
        if msg == None:
            return data
        msg     = msg.get('rx')
        data    = json.loads(msg)
    return data

def log(data):
    if debug:
        print data

def print_info(data):
    """ Prints each key and value of the provided dictionary """
    print "\t\tReceived..."
    for key in data:
        print "\t\t\t%s\t\t%s" %(key, repr(data.get(key)))

def send_message(dest=None, data=None):
    """ Sends provided data to the provided destination via Xbee """
    print "\t\tSending...:"
    base    = bases.get(dest)
    drone   = drones.get(dest)
    print_info(json.loads(data))
    if dest == glob_id:
        print "\t\tsending to %s at %s" % (dest, repr(Comms.Comms.BROADCAST))
        XBEE.get('session').sendData(Comms.Comms.BROADCAST, data, None, dest)
    elif base != None:
        print "\t\tsending to %s at %s" % (dest, repr(base.get('addr')))
        XBEE.get('session').sendData(base.get('addr'), data, None, dest)
    elif drone != None:
        print "\t\tsending to %s at %s" % (dest, repr(drone.get('addr')))
        XBEE.get('session').sendData(drone.get('addr'), data, None, dest)
    else:
        print "\t\t/*** Failed to send"


#
#   State Methods
#

def idle():
    """ Idle state. Does nothing"""
    pass

def send_connection_confirmation(data):
    """ Replies a drone's request confirmation request """
    global drones
    print_info(data)
    log("\t\tBefore")
    log("\t\t\tdrone: %s" % repr(drones))
    m = {'code': MOVE, 'id': dev_id, 'data': 'OK'}
    if data.get('id') not in drones:
        drones[data.get('id')] = {"addr": binascii.unhexlify(data.get('addr'))}
    log("\t\tAfter")
    log("\t\t\tdrones: %s" % repr(drones))
    send_message(data.get('id'), json.dumps(m))

def send_directions(data):
    """ Replies a drone's request for directions to a provided destination
        If the provided destination does not exist, then the drone will be
        forced to abort. if the provided destination does exist, but all
        paths are occupied, it will be asked to hover until a path opens up
    """
    global bases
    print_info(data)
    log("\t\tBefore")
    log("\t\t\tbases: %s" % repr(bases))
    b = bases.get(data.get('base'))
    if b == None:
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
        waymarks = [origin]
        brng = get_bearing(origin, target)
        d = 0.006 # distance left/right of base
        offset = 0.002 # distance before reaching base
        if path == "1":
            left = (brng - 90) % 360
            waymarks.append(get_new_coor(origin, left, d))
            dist = get_distance(waymarks[0], target)
            third = dist / 3.0
            remainder = dist - third - offset
            waymarks.append(get_new_coor(waymarks[0], brng, third))
            waymarks.append(get_new_coor(waymarks[1], brng, remainder))
        elif path == "2":
            dist = get_distance(origin, target)
            third = dist / 3.0
            remainder = dist - third - offset
            waymarks.append(get_new_coor(origin, brng, third))
            waymarks.append(get_new_coor(waymarks[0],brng, remainder))
        else:
            right = (brng + 90) % 360
            waymarks.append(get_new_coor(origin, right, d))
            dist = get_distance(waymarks[0], target)
            third = dist / 3.0
            remainder = dist - third - offset
            waymarks.append(get_new_coor(waymarks[0], brng, third))
            waymarks.append(get_new_coor(waymarks[1], brng, remainder))
        # Send info
        m = {
                'code': DIRECT,
                'waymarks': waymarks,
                'id': dev_id,
                'alt': dev_coor.get('alt') + (b.get('out') * base_alt)
            }

    print "/*** trace"
    for point in waymarks:
        print "%s, %s" % (repr(point.get('lat')), repr(point.get('lng')))

    log("\t\tAfter")
    log("\t\t\tbases: %s" % repr(bases))
    send_message(data.get('id'), json.dumps(m))

def send_release_msg(data):
    """ Replies to a drone's request to be released by generating a random
        message """
    global msgs
    global drones
    print_info(data)
    log("\t\tBefore")
    log("\t\t\tmsgs:   %s" % repr(msgs))
    log("\t\t\tdrones: %s" % repr(drones))
    m = {'code': SEND, 'msg': 'asdef', "id": dev_id}
    drones[data.get('id')] = {'addr':binascii.unhexlify(data.get('addr'))}
    chars = string.ascii_uppercase + string.digits
    m['msg'] = ''.join(random.choice(chars) for _ in range(12))
    msgs[data.get('id')] = m.get('msg')
    log("\t\tAfter")
    log("\t\t\tmsgs:   %s" % repr(msgs))
    log("\t\t\tdrones: %s" % repr(drones))
    send_message(data.get('id'), json.dumps(m))

def forward_release_msg(data):
    """ Responds to the drone's request to forward the release message provided
        to the provded base """
    print_info(data)
    log("\t\tBefore")
    log("\t\t\tmsgs:   %s" % repr(msgs))
    log("\t\t\tdrones: %s" % repr(drones))
    m = {
            'code': RELEASE_ACC,
            'msg': data.get("msg"),
            'id': data.get('id'),
            'base': dev_id
        }
    log("\t\tAfter")
    log("\t\t\tmsgs:   %s" % repr(msgs))
    log("\t\t\tdrones: %s" % repr(drones))
    send_message(data.get('base'), json.dumps(m))

def send_release_acceptance(data):
    """ Responds to the base's forward request by accepting or rejecting the
        message. If accepted, the base replies to provided  drone and released
        control. If rejected, the base will be forced to abort. """
    global drones
    global bases
    print_info(data)
    log("\t\tBefore")
    log("\t\t\tbases:  %s" % repr(bases))
    log("\t\t\tdrones: %s" % repr(drones))
    m = {'code': RELEASE_ACC}
    if data.get('msg') != msgs.get(data.get('id')):
        #NOTE Base should have the drone reattempt the release process
        m['code'] = ABORT
    #NOTE   Unlocking paths is bad here. This should happen after the drone
    #       reaches its target.
    for p in bases[data.get('base')].get('paths'):
        if bases[data.get('base')].get('paths').get(p) == data.get('id'):
            bases[data.get('base')]['paths'][p] = None
    send_message(data.get('id'), json.dumps(m))
    if data.get('id') in drones:
       del drones[data.get('id')]
    log("\t\tAfter")
    log("\t\t\tbases:  %s" % repr(bases))
    log("\t\t\tdrones: %s" % repr(drones))

def send_ping():
    """ Broadcasts a message with information needed communicate and locate.
        This information includes id, xbee address, latitude, longitude, and
        altidude """
    global ping
    global bases
    ping = False
    log("\t\tBefore")
    log("\t\t\tbases: %s" % repr(bases))
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
    log("\t\tAfter")
    log("\t\t\tbases: %s" % repr(bases))
    send_message(glob_id, json.dumps(m))

def send_reply_ping(data):
    """ Replies to a ping, by sending personal information needed to
        communicate and locate. Add provided information into memeory """
    print_info(data)
    log("\t\tBefore")
    log("\t\t\tbases: %s" % repr(bases))
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
    log("\t\tAfter")
    log("\t\t\tbases: %s" % repr(bases))
    send_message(data.get('id'), json.dumps(m))
    #TODO   Bases is cleared when a system goes down. Hence, when it reboots
    #       and sends a ping, the others won't reply with their information. we
    #       need to have the others send a reply. This could lead to cycle of
    #       send_replies. May need a new state that updates but does not reply

def update_map(data):
    """ Responds to a ping reply, by adding the provided information into
        memory """
    global bases
    print_info(data)
    log("\t\tBefore")
    log("\t\t\tbases: %s" % repr(bases))
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
    log("\t\tAfter")
    log("\t\t\tbases: %s" % repr(bases))

def send_global_ping():
    """ Broadcasts a message with empty data fields where other bases will
        add data to """
    m = {
            "code": PROPOGATE,
            "og": dev_id,
            "id": dev_id,
            "data":{},
            "q": [],
            "t": [dev_id]
        }
    #NOTE Assumes Central Base does not join two seperate networks
    if len(bases) > 0:
        for key in bases:
            send_message(key, json.dumps(m))
            break

def send_propogate(data):
    """ Replies to a global ping and request to propagate by adding peroson
        communication and location information to the data and bases for the
        ping to be propagated to """
    print_info(data)
    ID = data.get('id')
    d = data.get('data')    # data
    q = data.get('q')       # queue of bases to visit
    t = data.get('t')       # trace of path taken
    for key in bases.keys():
        # add based to queue only if does not exist in queue, trace, and data
        if key not in q and key not in t and d.get(key) == None:
            q.append(key)
    if d.get(dev_id) == None:
        d[dev_id] = {
                "lat": dev_coor.get('lat'),
                "lng": dev_coor.get('lng'),
                "alt": dev_coor.get('alt'),
                "links":bases.keys()
                }

    if dev_id == data.get('og'):
        d[dev_id] = {
                "lat": dev_coor.get('lat'),
                "lng": dev_coor.get('lng'),
                "alt": dev_coor.get('alt'),
                "links":bases.keys()
                }
        data = []
        for key in d:
            d.get(key)["base"] = key
            data.append(d.get(key))
        if os.path.isfile('map.pub'):
            os.remove("map.pub")
        with open('map.pub', 'w') as fn:
            fn.write(json.dumps(data))
        return

    m = {
            "code": PROPOGATE,
            "og": data.get('og'),
            "id": dev_id,
            "data":d,
            "q": q,
            "t":t
        }

    if len(q) > 0:
        if bases.get(q[0]) != None:
            t.append(dev_id)
            m['q'] = q[1:]
            m['t'] = t
            recipient = q[0]
            send_message(recipient, json.dumps(m))
            return
    recipient = t.pop()
    m['t'] = t
    send_message(recipient, json.dumps(m))
    #send_message(glob_id, json.dumps(m))

def start_take_off(data):
    """ Sends drone an altitude to take off too """
    print_info(data)
    base = bases.get(data.get('base'))
    m = {
            'code': TAKE_OFF,
            'lat': base.get('lat'),
            "lng": base.get('lng'),
            "alt": dev_coor.get('alt') + (base.get('out') * base_alt),
            'id': dev_id
        }
    if data.get('id') not in drones:
        drones[data.get('id')] = {"addr": binascii.unhexlify(data.get('addr'))}
    send_message(data.get('id'), json.dumps(m))

def send_flight_plan(data):
    """ Sends a flight plan to the provided drone  """
    global drones
    print_info(data)
    log("\t\tBefore")
    log("\t\t\tdrones: %s" % repr(drones))
    m = {
            'code': CONFIRM_FP,
            'flight_plan': data.get('flight_plan'),
            'addrs': data.get('addrs'),
            'drone': data.get('drone'),
            'id': dev_id
        }
    drones[data.get('drone')] = {"addr": binascii.unhexlify(data.get('addr'))}
    log("\t\tAfter")
    log("\t\t\tdrones: %s" % repr(drones))
    send_message(data.get('drone'), json.dumps(m))

#NOTE This two may be unneeded seeing that a drone can't reply mid flight
def request_status():
    """ Sends a request to the drone to provide location mid flight """
    global request
    for drone in drones:
        m = {
            'code': REPLY_STATUS,
            'id': dev_id
            }
        send_message(drone, json.dumps(m))
    request = False

def check_status(data):
    """ Given provided latitude and longitude of a drone, will resend directions
        if the drone has not taken off """
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

log("/*** Starting Base")
log("\tdev_id  \t%s" % dev_id)
log("\tglob_id \t%s" % glob_id)

# Find GPS
if disableGPS or find_device(GPS):
    if not startGPS(GPS):
        exit("GPS Failed to Connect")
else:
    exit("GPS not found")

if GPS.get('session') == None:
    exit('GPS not found')
else:
    log("\tGPS found at %s" % GPS.get('port'))

# Find XBEE
if find_device(XBEE):
    if not startXBEE(XBEE):
        exit("XBEE Failed to Connect")
else:
    exit("XBEE not Found")

if XBEE.get('session') == None:

    exit('\tXBEE not found')
else:
    log("\tXBEE found at %s" % XBEE.get('port'))
    log("\t\taddr: %s" % repr(XBEE.get('addr')))

# Send Xbee info to Central base
m = {"addr":XBEE.get('addr'), "dev":dev_id}
sp.Popen(["curl", "-f", "-s", "10.0.1.72:5000/xbee_info", "-X", "POST", "-d", json.dumps(m)], shell=False)

dev_coor = get_coordinates()
log("\tStarting Position")
log("\t\tlatitude:  %f" % dev_coor.get('lat'))
log("\t\tlongitude: %f" % dev_coor.get('lng'))
log("\t\taltitude:  %f" % dev_coor.get('alt'))


log("\tStarting triggers")
# Start Triggers
#TODO Turn back on
#trigger_request()
trigger_ping()

#print "\tSending Startup Ping"
# On bootup, send Ping
#send_ping()
timer = 0
print "\n/*** Starting Machine"
try:
    while run:
        data = get_next_state()
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
