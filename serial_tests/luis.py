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

BAUDRATE = 9600
SERIAL_XB01_LOW = '\x41\x67\x21\xA9'
SERIAL_XB22_LOW = '\x41\x75\xBC\x88'
SERIAL_NUM_HIGH = '\x00\x13\xA2\x00' #same for all devices

try:
    if find_device(XBEE):
        xb   = Comms(XBEE.get('port'), data_only=True)
except:
    exit("Xbee connection Failed")

self = xb.getLocalAddr()

print "\n/** Sending Messages"
addr = self[0] + self[1]
print addr
print repr(addr)
data3 = binascii.hexlify(self[0]) + binascii.hexlify(self[1])
xb.sendData(addr, '{"code":"PING", "addr": "%s"}' % data3)


print "\n/** Reading Messages"
target = None
try:
    while True:
        if not xb.isMailboxEmpty():
            d = xb.readMessage().get('rx')
            data = json.loads(d)
            print data
            if data.get('code') == "PING":
                target = binascii.unhexlify(data.get('addr'))
                print target
                xb.sendData(dest=target, data='{"code":"REPLY","addr":"%s"}' % data.get('addr'))
                print "dank"
            elif data.get('code') == "REPLY":
                break
except (KeyboardInterrupt):
    xb.close()
    exit()
    

