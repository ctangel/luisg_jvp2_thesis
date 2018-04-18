import os, json, random

# Generate Random Test String
msg = os.urandom(456).encode("hex")
msg = '{"code":"REPLY_PING", "alt": 89, "lat": 12.1234, "lng": 34.0543", "addr": "AE89FF3BBA", "id": "central", "data": "this is where we will add other information but I am just adding this to make this look larger"}'
print "Test String:\t%s" % msg

def parse(msg):
    limit = 100
    length = len(msg)
    chunks = []
    print "String Length:\t%s" % length
    if length <= limit:
        print "Chunked Num:\t1"
        print "Output:\t\t%s" % msg
        chunks.append(msg)
    elif length > limit:
        if length % 100 == 0:
            num_chunks = length / 100
        else:
            num_chunks = (length / 100) + 1
        print "Chunked Num:\t%d" % num_chunks
        for i in range(num_chunks):
            low = 100 * i
            hi  = 100 + low
            print "Chunk %d:\t%s" % (i+1, msg[low:hi])
            chunks.append(msg[low:hi])
    else:
        print "Error"
    return chunks

chunks = parse(msg)

# Sender tells Receiver that you will be sending X messages
m = {"code": "PING", "chunks": len(chunks)}
print "\nSending.... %s" % json.dumps(m)

# Receiver will wait until it received them all
print "\nMessage received... waiting for %d messages" % len(chunks)

# Sender send each message
print "\nSending...."
msgs = []
for i, chunk in enumerate(chunks):
    print "-> %04x%s" % (i, chunk) #number of chunck stored in first 2 bytes
    msgs.append("%04x%s" % (i, chunk))

# Receiver constructs full message
random.shuffle(msgs)
ordered_msgs = [0] * len(msgs)
for m in msgs:
    num = m[:4]
    ordered_msgs[int(num)] = m[4:]

full_msg = ''
for m in ordered_msgs:
    full_msg = full_msg + m

if full_msg == msg:
    print '\nMatch!'
else:
    print "\nNo Match"
