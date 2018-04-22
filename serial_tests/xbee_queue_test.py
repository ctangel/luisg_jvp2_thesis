from xbee import ZigBee
import time, serial, Queue, os, logging
from apscheduler.scheduler import Scheduler

BAUDRATE = 9600

#FIXME: you'll need to update these when you run multiple sessions
#because the USB serial paths will change
#Serial paths
XB01 = '/dev/cu.usbserial-DN041WOY' #XB01
XB22 = '/dev/cu.usbserial-DN02Z3LS' #XB22
XB52 = '/dev/cu.usbserial-DN02Z6QG' #XB52

#Route Addressing
SERIAL_NUM_HIGH = '\x00\x13\xA2\x00' #same for all devices
SERIAL_XB52_LOW = '\x41\x75\xBC\x91'
SERIAL_XB22_LOW = '\x41\x75\xBC\x88'
SERIAL_XB01_LOW = '\x41\x67\x21\xA9'
BROADCAST        = '\x00\x00\x00\x00\x00\x00\xff\xff' #The broadcast frequency
RESERVED_SERIAL  = '\xFF\xFE'
i = 0
#":".join("{:02x}".format(ord(c)) for c in dest) #NOTE: this is a simple way to print hex strings, where dest is the binary hex string

frames = Queue.Queue()
logging.basicConfig()

#This is for recevied data
def callback_xb01(data):
    frames.put(data, block=False)

def callback_xb22(data):
    print '*** IN 22 CALLBACK ***'
    print data.get('rf_data')
    print '**********************'

def callback_xb52(data):
        print '*** IN 52 CALLBACK ***'
        print data.get('rf_data')
        print '**********************'

def completeExit():
    xb01.halt(), xb22.halt()
    xb01_ser.close(), xb22_ser.close()
    exit()

def handleFrame(data):
    print data['id'],
    if data['id'] == 'rx':

        print "NEW DATA: " + data['rf_data']
    elif data['id'] == 'tx_status':
        print "DELIVER STATUS: " + data['deliver_status'].encode('hex')
    else:
        print 'Unimplemented frame type'

#this is XB22 -> XB01'
def sendQueryPacket():
    content = "sending i at: " + str(i)
    dest = SERIAL_NUM_HIGH + SERIAL_XB01_LOW
    xb22.send('tx', dest_addr_long=dest, dest=RESERVED_SERIAL, data='Got this?\r')

xb01_ser = serial.Serial(XB01, baudrate=BAUDRATE)
xb01 = ZigBee(xb01_ser, callback=callback_xb01)
xb22_ser = serial.Serial(XB22, baudrate=BAUDRATE)
xb22 = ZigBee(xb22_ser)

#XB22 will send a data frame to XB01 every second
sendScheduler = Scheduler()
sendScheduler.start()
sendScheduler.add_interval_job(sendQueryPacket, seconds=1)

#The PC Xbee will only receive
cycle = 0
while True:
    try:
        print "Queue size: " + str(frames.qsize())
        time.sleep(3)
        if frames.qsize() > 0:
            print "cycle is: " + str(cycle)
            cycle += 1
            handleFrame(frames.get_nowait())

    except KeyboardInterrupt:
        completeExit()
