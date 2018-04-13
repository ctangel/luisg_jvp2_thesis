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
    pass

def callback_xb22(data):
    print '*** IN 22 CALLBACK ***'
    print data.get('rf_data')
    print '**********************'

def callback_xb52(data):
        print '*** IN 52 CALLBACK ***'
        print data.get('rf_data')
        print '**********************'

def completeExit():
    xb01.halt(), xb22.halt(), xb52.halt()
    xb01_ser.close(), xb22_ser.close(), xb52_ser.close()
    exit()

xb01_ser = serial.Serial(XB01, baudrate=BAUDRATE)
xb01 = ZigBee(xb01_ser, callback=callback_xb01)
xb22_ser = serial.Serial(XB22, baudrate=BAUDRATE)
xb22 = ZigBee(xb22_ser, callback=callback_xb22)
xb52_ser = serial.Serial(XB52, baudrate=BAUDRATE)
xb52 = ZigBee(xb52_ser, callback=callback_xb52)

#Using binary files provided in ../files
try:
    fIn = open('./files/sample1.pub', 'r')
    contents = fIn.read()
    statinfo = os.stat('./files/sample3.pub')
    print statinfo.st_size
    print contents
except:
    print 'Error occured'
    completeExit()


try:
    while True:
        time.sleep(3)
        #xb01 send message to xb2
        dest = SERIAL_NUM_HIGH + SERIAL_XB22_LOW
        xb01.send('tx', dest_addr_long=dest, dest=RESERVED_SERIAL, data=contents + '\r')
        print 'message to xb22 sent'
        time.sleep(3)
        #xb01 send message to xb52
        dest = SERIAL_NUM_HIGH + SERIAL_XB52_LOW
        xb01.send('tx', dest_addr_long=dest, dest=RESERVED_SERIAL, data='HEY 52 FROM 01!\r')
        print 'message to xb52 sent'
except KeyboardInterrupt:
    completeExit()
