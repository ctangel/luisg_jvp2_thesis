from xbee import ZigBee
import time, serial, Queue

#Get the 'PC' Xbee device
BAUD_RATE = 9600

XB01 = '/dev/cu.usbserial-DN041WOY' #XB01
XB22 = '/dev/cu.usbserial-DN02Z3LS' #XB22
XB52 = '/dev/cu.usbserial-DN02Z6QG' #XB52

SERIAL_NUM_HIGH = '\x00\x13\xA2\x00' #same for all devices
SERIAL_NUM_LOW   = '\x41\x75\xBC\x88' #for the PC
RASPI_NUM_LOW    = '\x41\x67\x21\xA9' #for the Raspberry Pi
BROADCAST        = '\x00\x00\x00\x00\x00\x00\xff\xff'
RESERVED_SERIAL  = '\xFF\xFE'
dest = SERIAL_NUM_HIGH + RASPI_NUM_LOW
#":".join("{:02x}".format(ord(c)) for c in dest) #NOTE: this is a simple way to print hex strings, where dest is the binary hex string

def callback_function(data):
    print 'packet received'
    print data.get('rf_data')
    print '**********'

#type the receive code here which is the callback_function!
xbee_serial = serial.Serial(PORT, baudrate=BAUD_RATE)
xb = ZigBee(xbee_serial, callback=callback_function)

try:
    while True:
        pass
except KeyboardInterrupt:
    xb.halt()
    xbee_serial.close()
    exit()
