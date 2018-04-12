from xbee import ZigBee
import time, serial, Queue

#Get the 'PC' Xbee device
BAUD_RATE = 9600
PORT = '/dev/cu.usbserial-DN02Z3LS'
SERIAL_NUM_HIGH = '\x00\x13\xA2\x00' #same for all devices
SERIAL_NUM_LOW  = '\x41\x67\x21\xA9' #for the Raspberry Pi
PC_SERIAL_LOW   = '\x41\x75\xBC\x88' #for the PC
BROADCAST = '\x00\x00\x00\x00\x00\x00\xff\xff'
RESERVED_SERIAL  = '\xFF\xFE'
dest = SERIAL_NUM_HIGH + PC_SERIAL_LOW
#":".join("{:02x}".format(ord(c)) for c in dest) #NOTE: this is a simple way to print hex strings, where dest is the binary hex string

"""
#callback function for when data is received
def callback_function(data):
    print 'packet received'

def errorCallback_function(data:):
    print 'error: no packet received'
"""

xbee_serial = serial.Serial(PORT, baudrate=BAUD_RATE)
#xb = ZigBee(xbee_serial,callback=callback_function,error_callBack_function=errorCallback_function)
xb = ZigBee(xbee_serial)

while True:
    try:
        time.sleep(1)
        xb.send('tx', dest_addr_long=dest, dest=RESERVED_SERIAL, data='HELLO_DATA\r')
        print 'message sent'
    except KeyboardInterrupt:
        xb.halt()
        xbee_serial.close()
        exit()
