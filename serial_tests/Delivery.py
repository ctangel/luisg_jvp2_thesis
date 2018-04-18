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
        elif length > limit:
            if length % self.chunk_limit == 0:
                num_chunks = (length/self.chunk_limit)
            else:
                num_chunks = (length/self.chunk_limit) + 1
            for i in range(num_chunks):
                lo = self.chunk_limit * i
                hi = self.chunk_limit + lo
                chunks.apend(msg[lo:hi])
        else:
            print "Error"
        return chunks

    """
        Given a list of messages 'msgs', encrypte the messages. Returns a list
        of encrypted messages to send out
    """
    def encrypt(self, data, devID):
        pass

    def batchEncrypt(self, data, devID):
        lst = []
        for msg in data:
            lst.append(self.encrypt(msg, devID))
        return lst

    """
        Given a whole message 'data', will prepare the message for delivery and send
        via the given 'comm' to the destination 'dest'
    """
    def package(self, dest, data):
        assert(data != None and dest != None and len(data) <= self.MAX_MSG_SIZE)

        #Destination is new. Add dicitonary file for this destination
        if self.destinations.get(dest) == None:
            self.destinations[dest] = {}

        chunks = __breakup(data)
        max = len(chunks)

        #Add a new message identifier to the dictionary file, marking as a "sender"
        for msgID in REFLIST:
            if msgID not in self.destinations[dest]:
                self.destinations[dest][msgID] = 'SENDER'
                break
            return False

        #prepare messages by prefixing and encrypting
        msgs = []
        for i, msg in enumerate(chunks):
            msgs.append("%s%s%d%s" % (msgID, REFLIST[i], REFLIST[max], msg))
        return batchEncrypt(msgs)

    def unpackage(self, data, source):
        assert(data is not None and source is not None)
        dec_msg = self.decrypt(data)
        id = dec_msg[0] #Message Identifier
        max =dec_msg[2] #Number of partial messages for completed message

        try:
            #Means that this is the first message received with this identifier.
            #Make a new MessageBuilder
            if self.destinations.get(source) == None:
                self.destinations[source] = {}

            #For this source, get the message identifier. If no identifier exists,
            #Create a new diciotnary file with the Message Builder
            if self.destinations[source].get(id) == None:
                self.destinations[source][id] = MessageBuilder.MessageBuilder(max)


            if self.destinations[source][id].addMessage(msg[1:]):
                complete_msg = __compileMessage(self.destinations[source][id].getMsgs())
                del self.destinations[source][id]
                return (id, complete_msg) #TODO: recipient now needs to send a confimration
                                    #that all messages have been received
        except:
            print "you royally messed up..."
            return None

    def __compileMessage(self, msgs):
        return ''.join([y[2:] for y in sorted(msgs, key = lambda x: REFLIST.index(x[0]))])
            #Sort messages by REFLIST, and then remove the message prefix from
            #each message. Then combines all the messages and returns the completed
            #message

    def decrypt(self, data, devID):
        pass

    def batchDecrypt(self, data, devID):
        lst = []
        for msg in data:
            lst.append(self.decrypt(msg))
