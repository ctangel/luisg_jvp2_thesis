from xbee import ZigBee
import time, serial, os

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
#":".join("{:02x}".format(ord(c)) for c in dest) #NOTE: this is a simple way to print hex strings, where dest is the binary hex string

def callback_xb01(data):
    print "*** IN CALLBACK ***"
    print data.get('id')
    s = data.get('parameter')
    print ":".join("{:02x}".format(ord(c)) for c in s)

xb01_ser = serial.Serial(XB01, baudrate=BAUDRATE)
xb01 = ZigBee(xb01_ser, callback=callback_xb01)

def completeExit():
    xb01.halt()
    xb01_ser.close()
    exit()

try:
    while True:
        time.sleep(2)
        xb01.send('at', command='SL')
except KeyboardInterrupt:
    completeExit()
