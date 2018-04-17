from xbee import ZigBee
import Queue
import serial, threading, time

class Comms():

    RESERVED_SERIAL  = '\xFF\xFE' #Necessary byte string for data transmissions
    BROADCAST        = '\x00\x00\x00\x00\x00\x00\xff\xff' #The broadcast frequency
    SERIAL_NUM_HIGH  = '\x00\x13\xA2\x00' #same for all devices

    """
        Comms class works for ZigBee devices. Given a USB Serial path and baudrate,
        will establish a serial channel with the USB ZigBee device. Will then
        create a ZigBee module for network communication. You can pass a 'callback'
        function that will be triggered for receipt of messages. The class provides
        a default queuedCallback routine for storage of messages. If default callback
        function is used, specify if this should be a 'rx' only device, meaning
        only data messages will be stored.

        If construction failes, return False.
    """
    def __init__(self, path, baud=9600, callback=None, data_only=False):
        self.path = path
        self.baud = baud
        if callback is None:
            self.callback = self.__queuedCallback
        else:
            self.callback = callback

        try:
            self.ser = serial.Serial(path, baudrate=baud)
        except:
            print "serial failed"
            exit()

        try:
            self.xb = ZigBee(self.ser, callback=self.callback)
        except(e):
            print "xb initialization failed"
            print e
            self.ser.close()
            exit()

        self.queue = Queue.Queue()
        self.queueAT = Queue.Queue() #Mailbox specifically for AT Responses
        self.data_only = data_only


        #TODO: type checking/null checking
        #TODO: try/except for Serial and ZigBee

    """
        releases all resources used by Comms class instantiation.
    """
    def close(self):
        self.xb.halt()
        self.ser.close()

    """
        If this Xbee stores only 'rx' messages, return True. Otherwise, False
    """
    def isDataOnly(self):
        return self.data_only

    """
        Will change if the mailbox is data only or not. returns the new value
        of self.data_only
    """
    def switchDataOnly(self):
        self.data_only = not self.data_only
        return self.data_only

    """
        A simple callback function that will store received frames until ready to be
        processed. If the received frame is an 'at_response', will blocks
    """
    def __queuedCallback(self, data):
        if data['id'] is 'at_response':
            self.queueAT.put(data, block=False)
            return
        if self.data_only:
            if data['id'] != 'rx':
                return
        self.queue.put(data, block=False)

    """
        If the mailbox is empty, return true. Otherwise, return false
    """

    def isMailboxEmpty(self):
        return self.queue.empty()

    """
        Returns the number of messages in the mailbox.
    """
    def messageCount(self):
        return self.queue.qsize()

    """
        Sends a 'tx' command. Sends 'data' to the address specified by 'dest'.
    """
    def sendData(self, dest, data):
        self.xb.send('tx', dest_addr_long=dest, dest=self.RESERVED_SERIAL, data=data)
        time.sleep(0.15) #wait 15ms to ensure message can be sent out
        #TODO: type checking/null checking

    """
        Broadcast 'data' across the entire network, all nodes.
    """
    def broadcastData(self, data):
        self.xb.send('tx', dest_addr_long=self.BROADCAST, dest=self.RESERVED_SERIAL, data=data)
        time.sleep(0.1)
        #TODO: type checking/null checking

    """
        Will read the first message in the mailbox. Returns a dictionary where the
        key is the data id, and the value is the data associated with that data,
        if any. Currently only supports data id's of type 'rx' or 'rx_explicit'.
        If no messages exist, or message type is unsupported, returns False.
    """
    def readMessage(self):
        if self.isMailboxEmpty():
            return False
        msg = self.queue.get_nowait()
        if msg['id'] is 'rx':
            return {'rx': msg['rf_data']}
        elif msg['id'] is 'at_response':
            return {'at_response': msg.get('parameter')}

    """
        Will return a 2 item list of the 64-bit address. First item is the
        high end serial address. Second item is the low end serial address.
    """
    def getLocalAddr(self):
        self.xb.send('at', command='SH')
        time.sleep(0.1)
        self.xb.send('at', command='SL')
        time.sleep(0.1)

        sh = self.queueAT.get_nowait()['parameter']
        sl = self.queueAT.get_nowait()['parameter']
        print [sh, sl]
        return [sh, sl]
        #":".join("{:02x}".format(ord(c)) for c in s)
