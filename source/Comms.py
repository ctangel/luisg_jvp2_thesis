from xbee import ZigBee
import Queue
import serial, threading, time, string, binascii, subprocess as sp, os, json
class MessageBuilder():
    def __init__(self, num):
        self.msgs = []
        self.num = num

    def getMsgs(self):
        return self.msgs

    def getNum(self):
        return self.num

    #Returns true if the last message added completed the expected number of
    #received messages. Otherwise, returns false
    def addMessage(self, msg):
        self.msgs.append(msg)
        return len(self.msgs) == self.num

class Delivery():

    REFLIST = list(string.printable[:94])
    MAX_CHUNK_SIZE = 67 #73 - 2*3, where 73 is the max size of a data stream. 3 for the
    #placeholder bytes needed for keeping track of messages
    MAX_MSG_SIZE = len(REFLIST) * MAX_CHUNK_SIZE

    """
        Delivery class is meant to prepare messages for transmission and unpackage
        recovered messages.
    """
    def __init__(self, chunk_limit=None):

        #Maximum size that an individual data frame can be. Throw error if larger
        #than MAX chunk Size
        if chunk_limit == None or chunk_limit > self.MAX_CHUNK_SIZE:
            self.chunk_limit = self.MAX_CHUNK_SIZE
        else:
            self.chunk_limit = chunk_limit
        self.destinations = {} #This is intended to be a doubly nested dictionary
        #where the top level represents the destinations, and the secondary level
        #is for the message identifiers for the destinations
        #recipients have MessageBuilder objects. Senders are denoted as "SENDER"

    """
        Given a data message 'msg', will breakup the message into the sizeable
        chunks necessary for delivery on the XBEE device. Inteded as a helper function
        for Delivery.send()
    """
    def __breakup(self, data):
        chunks = []
        length = len(data)
        if length <= self.chunk_limit:
            chunks.append(data)
        elif length > self.chunk_limit:
            if length % self.chunk_limit == 0:
                num_chunks = (length/self.chunk_limit)
            else:
                num_chunks = (length/self.chunk_limit) + 1
            for i in range(num_chunks):
                lo = self.chunk_limit * i
                hi = self.chunk_limit + lo
                chunks.append(data[lo:hi])
        else:
            print "Error"
        return chunks

    """
        Given a list of messages 'msgs', encrypte the messages. Returns a list
        of encrypted messages to send out
    """
    def encrypt(self, data, devID):
        enc_data = sp.check_output("./encrypt '%s' %s < param/a3.param" % (data, devID), shell=True)
        return enc_data

    def batchEncrypt(self, data, devID):
        lst = []
        for msg in data:
            lst.append(self.encrypt(msg, devID))
        return lst

    def decrypt(self, data, devID):
        dec_data = sp.check_output("./decrypt %s %s < param/a3.param" % (devID, data), shell=True)
        return dec_data

    def batchDecrypt(self, data, devID):
        lst = []
        for msg in data:
            lst.append(self.decrypt(msg, devID))

    """
        Given a whole message 'data', will prepare the message for delivery and send
        via the given 'comm' to the destination 'dest'
    """
    def package(self, dest, data, devID):
        assert(data != None and dest != None and len(data) <= self.MAX_MSG_SIZE) 
        #Destination is new. Add dicitonary file for this destination
        print self.destinations
        if self.destinations.get(dest) == None:
            self.destinations[dest] = {}

        chunks = self.__breakup(data)
        max = len(chunks)

        #Add a new message identifier to the dictionary file, marking as a "sender"
        for msgID in self.REFLIST:
            if msgID not in self.destinations[dest]:
                self.destinations[dest][msgID] = 'SENDER'
                break
            #return False
        #TODO   Currently, the same message cannot be send to a destination twice
        #       This present attempts at resending a dropped message
        #prepare messages by prefixing and encrypting
        msgs = []
        for i, msg in enumerate(chunks):
            msgs.append("%s%s%s%s" % (msgID, self.REFLIST[i], self.REFLIST[max], msg))
        if dest == '\x00\x00\x00\x00\x00\x00\xff\xff':
                    del self.destinations[dest]
        return self.batchEncrypt(msgs, devID)

    def unpackage(self, data, source, devID):
        assert(data is not None and source is not None)
        dec_msg = self.decrypt(data, devID)
        print "\t\t\t%s" % dec_msg
        try:
            d = dec_msg.decode('ascii')
            dd = repr(dec_msg).decode('ascii')
        except:
            return (None, None)
        try:
            w = json.loads(dec_msg)
            if w.get('code') == 'y':
                del self.destinations[source][w.get("msgID")]
            return (w.get('msgID'), None)
        except:
            #NOTE Failurer here. exception is thrown and (None, None) is thrown even though message was properly decrypted
            #try:
            if True:
                i = dec_msg[0] #Message Identifier
                m = int(dec_msg[2]) #Number of partial messages for completed message
                #Means that this is the first message received with this identifier.
                #Make a new MessageBuilder
                print "\t\t\t++> source: %s" % source
                print "\t\t\t++> %s" % repr(self.destinations)
                if self.destinations.get(source) == None:
                    self.destinations[source] = {}
                
                print "\t\t\t++> %s" % repr(self.destinations)
                #For this source, get the message identifier. If no identifier exists,
                #Create a new diciotnary file with the Message Builder
                #NOTE this can return either a Message Builder or a 'SENDER' string
                if self.destinations[source].get(i) == None:
                    self.destinations[source][i] = MessageBuilder(m)
                if self.destinations[source].get(i) == "SENDER":
                    #Overwrite SENDER STATUS
                    self.destinations[source][i] = MessageBuilder(m)
                print "\t\t\t++> %s" % repr(self.destinations)
                if self.destinations[source][i].addMessage(dec_msg[1:]):
                    complete_msg = self.__compileMessage(self.destinations[source][i].getMsgs())
                    del self.destinations[source][i]
                    return (i, complete_msg) #TODO: recipient now needs to send a confimration
            try:
                return (i, None)
            except:
                return (None, None)

    def __compileMessage(self, msgs):
        return ''.join([y[2:] for y in sorted(msgs, key = lambda x: self.REFLIST.index(x[0]))])
            #Sort messages by REFLIST, and then remove the message prefix from
            #each message. Then combines all the messages and returns the completed
            #message

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
        self.delivery = Delivery(chunk_limit=25)
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

        except:
            print "xb initialization failed"
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
        print "\t\t\t-> %s" % repr(data)
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
    def sendData(self, dest, data, ack, devID):
        if ack: #This should be encrypted. Luis promised it will be
            self.xb.send('tx', dest_addr_long=dest, dest=self.RESERVED_SERIAL, data=data)
            time.sleep(0.15) #wait 15ms to ensure message can be sent out
            #TODO: type checking/null checking
        else:
            msgs = self.delivery.package(dest, data, devID)
            if not msgs:
                print "failed to send"
                return
            if os.path.isfile("global.pub"):
                with open("global.pub") as fn:
                    global_id = fn.read()
            if global_id == devID:
                for msg in msgs:
                    self.xb.send('tx', dest_addr_long=dest, dest=self.RESERVED_SERIAL, data=msg, frame_id="A")
                    time.sleep(0.15)
            else:
                 for msg in msgs:
                    self.xb.send('tx', dest_addr_long=dest, dest=self.RESERVED_SERIAL, data=msg, frame_id="B")
                    time.sleep(0.15)
            
    """
        Broadcast 'data' across the entire network, all nodes.
    """
    def broadcastData(self, dest, data):
        for msg in self.delivery.package(dest, data, dest):
            self.xb.send('tx', dest_addr_long=self.BROADCAST, dest=self.RESERVED_SERIAL, data=msg)
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
            return None
        # Read in Device ID and Global ID from file
        if os.path.isfile("id.pub"):
            with open("id.pub") as fn:
                dev_id = fn.read()
        if os.path.isfile("global.pub"):
            with open("global.pub") as fn:
                global_id = fn.read()
        is_global = False
        msg = self.queue.get_nowait()
        """
        if msg['id'] is 'rx':
            print "checking source %s" % msg.get('source_addr_long')
            #TODO Handle both dev_id and glob_id
            msgID, data = self.delivery.unpackage(msg['rf_data'], msg['source_addr_long'], dev_id)
            if msgID is None and data is None:
                is_global = True
                msgID, data = self.delivery.unpackage(msg['rf_data'], msg['source_addr_long'], global_id)
            #FIXME  Code above trys to decrypt with dev_id, if it fails, then it attemps to decrypt with global_id
            #       Could cause problems when mutliple messages are being sent over the network
            if data != None:
                try:
                    senderID = json.loads(data).get('id')
                except:
                    return None
                dest = msg['source_addr_long'] #FIXME: possibly in wrong format (but correct parameter)
                m = {"code": "y", "msgID": msgID} #FIXME: get a global variable / not hardcoded
                msg = self.delivery.encrypt(json.dumps(m), senderID)
                if not is_global:
                    self.sendData(dest=dest, data=msg, ack=True, devID=senderID)
                return {'rx': data}
            else:
                #del self.destinations[source][i]
                pass
            return None
            """
        if msg['id'] is 'rx':
            option = binascii.hexlify(msg.get('options'))
            is_global = False
            if option == "c2":
                # global
                print "\t\t\tGLOBAL"
                msgID, data = self.delivery.unpackage(msg['rf_data'], msg['source_addr_long'], global_id)
                is_global = True
            else:
                # dev_id
                print "\t\t\tDEV_ID"
                msgID, data = self.delivery.unpackage(msg['rf_data'], msg['source_addr_long'], dev_id)
            if data == None and msgID == None:
                print "\t\t\tNot for me" 
                #return None
            if data != None:
                print "\t\t\tHave data!"
                try:
                    senderID = json.loads(data).get('id')
                except:
                    print "\t\t\tNot decrypted properly"
                    return None
                dest = msg['source_addr_long'] #FIXME: possibly in wrong format (but correct parameter)
                m = {"code": "y", "msgID": msgID} #FIXME: get a global variable / not hardcoded
                msg = self.delivery.encrypt(json.dumps(m), senderID)
                if not is_global:
                    self.sendData(dest=dest, data=msg, ack=True, devID=senderID)
                return {'rx': data}
            else:
                print "\t\t\tPass, no data"
                pass
            return None
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
        return [sh, sl]
        #":".join("{:02x}".format(ord(c)) for c in s)
