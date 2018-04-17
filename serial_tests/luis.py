from Comms import Comms
import threading, time, serial.tools.list_ports, json, binascii

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

def bytecode_to_hex(bytecode):
    s = ""
    #for byte in bytearray(str.encode(bytecode)):
    for byte in bytearray(bytecode):
        s = "%s-%s" %(s, "%02X" % (byte))
    return s

BAUDRATE = 9600

XB01 = '/dev/cu.usbserial-DN041WOY' #XB01
XB22 = '/dev/cu.usbserial-DN02Z3LS' #XB22
SERIAL_XB01_LOW = '\x41\x67\x21\xA9'
SERIAL_XB22_LOW = '\x41\x75\xBC\x88'
SERIAL_NUM_HIGH = '\x00\x13\xA2\x00' #same for all devices
print "OG"
print SERIAL_XB01_LOW
print repr(SERIAL_XB01_LOW)
print type(SERIAL_XB01_LOW)
print
try:
    if find_device(XBEE):
        xb   = Comms(XBEE.get('port'), data_only=True)
except:
    exit("Xbee connection Failed")

#print "Data only? " + str(xb.isDataOnly())
print "/** Prechecks"
self = xb.getLocalAddr()
print "\tMailbox empty? " + str(xb.isMailboxEmpty())
print "\tmessage count: " + str(xb.messageCount())

print "\n/** Sending Messages"
data1 = "hey there! 1, from xb01"
data2 = "hey there! 2, from xb01"
#data3 = bytecode_to_hex(self[0]) + bytecode_to_hex(self[1])
data3 = binascii.hexlify(self[0]) + binascii.hexlify(self[1])
dest = SERIAL_NUM_HIGH + SERIAL_XB22_LOW #XB22 -> XB01
#xb.sendData(dest=dest, data = data1)
#xb.sendData(dest=dest, data = data2)
xb.broadcastData('{"code":"PING", "addr": "%s"}' % data3)
print "\tXB01 sent two messages..."


print "\n/** Reading Messages"
target = None
try:
    while True:
        if not xb.isMailboxEmpty():
            d = xb.readMessage().get('rx')
            data = json.loads(d)
            if data.get('code') == "PING":
                target = binascii.unhexlify(data.get('addr'))
                data4 = binascii.hexlify(self[0]) + binascii.hexlify(self[1])
                target = target.replace("-", "\\x")
                xb.sendData(dest=target, data='{"code":"REPLY","addr":"%s"}' % data4)
            elif data.get('code') == "REPLY":
                reply = xb.readMessage()
                print reply
except (KeyboardInterrupt):
    xb.close()
    exit()
