class Comms:
    from xbee import ZigBee
    import Queue, serial

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
    def __init__(self, path, baud=9600, callback=self.queuedCallback, data_only=False):
        self.path = path
        self.baud = baud
        self.callback = callback
        self.ser = serial.Serial(path, baudrate=baud)
        self.xb = ZigBee(self.ser, callback=self.callback)
        self.queue = Queue.Queue()
        self.data_only = data_only

        #TODO: type checking/null checking
        #TODO: try/except for Serial and ZigBee

    """
        If this Xbee stores only 'rx' messages, return True. Otherwise, False
    """
    def isDataOnly(self):
        return self.data_only

    """
        A simple callback function that will store received frames until ready to be
        processed.
    """
    def queuedCallback(self, data):
        if self.data_only:
            if data['id'] != 'rx':
                return
        self.queue.put(data, block=False)

    """
        If the mailbox is empty, return true. Otherwise, return false
    """
    def isMailboxEmpty(self):

    """
        Returns the number of messages in the mailbox.
    """
    def messageCount(self):
        return self.queue.qsize()

    """
        Sends a 'tx' command. Sends 'data' to the address specified by 'dest'.
    """
    def sendData(self, dest, data):
        self.xb.send('tx', dest_addr_long=dest, dest=RESERVED_SERIAL, data=data)
        #TODO: type checking/null checking

    """
        Broadcast 'data' across the entire network, all nodes.
    """
    def broadcastData(self, data):
        self.xb.send('tx', dest_addr_long=BROADCAST, dest=RESERVED_SERIAL, data=data)
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
        if msg['id'] != 'rx':
            return False
        return {'rx': data['rf_data']}
