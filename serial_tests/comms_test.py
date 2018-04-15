from Comms import Comms
import threading, time, serial.tools.list_ports

XBEE = {
    "vid": ["0403"],
    "pid": ["6015"],
    "port": None,
    "session": None
}


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

BAUDRATE = 9600

XB01 = '/dev/cu.usbserial-DN041WOY' #XB01
XB22 = '/dev/cu.usbserial-DN02Z3LS' #XB22
SERIAL_XB01_LOW = '\x41\x67\x21\xA9'
SERIAL_XB22_LOW = '\x41\x75\xBC\x88'
SERIAL_NUM_HIGH = '\x00\x13\xA2\x00' #same for all devices
print "dab"
try:
    #if find_device(XBEE):
    #    print XBEE.get('port')
    #    xb   = Comms(XBEE.get('port'), data_only=True)
    xb   = Comms(XB01, data_only=True)
        #xb   = Comms("/dev/ttyUSB0", data_only=True)
    #if find_device(XBEE):
    xb22 = Comms(XB22, data_only=True)
except:
    print "failed..."
    exit()

print "Data only? " + str(xb.isDataOnly())
print "switching..."
xb.switchDataOnly()
print "Data only? " + str(xb.isDataOnly())
print "Mailbox empty? " + str(xb.isMailboxEmpty())
print "message count: " + str(xb.messageCount())

data1 = "hey there! 1"
data2 = "hey there! 2"
data3 = "broadcasting"
dest = SERIAL_NUM_HIGH + SERIAL_XB01_LOW #XB22 -> XB01
xb22.sendData(dest=dest, data = data1)
xb22.sendData(dest=dest, data = data2)
print "XB22 sent two messages..."
print "Mailbox empty? " + str(xb.isMailboxEmpty())
print "Message count: " + str(xb.messageCount())
print xb.readMessage()
print xb.readMessage()
xb22.broadcastData(data3)
print str(xb.messageCount())
print xb.readMessage()
print str(xb.readMessage())

xb.getLocalAddr()

xb.close()
xb22.close()
del xb
exit()
