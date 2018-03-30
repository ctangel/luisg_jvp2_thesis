'''
    Test File for runbase.py
'''
import subprocess as sp
import json
import unittest
import os

# Base Codes
IDLE            = 'a'
SEND_CONFIRM    = 'b'
SEND_DIRECT     = 'c'
RELEASE_MSG     = 'd'
FORWARD         = 'e'
RELEASE_ACC     = 'f'
PING            = 'g'
REPLY_PING      = 'h'
UPDATE          = 'i'
GLOBAL_PING     = 'j'
PROPOGATE       = 'k'

# Drone Codes
CONFIRM         = 'l'
DIRECT          = 'm'
ASK_DIRECT      = 'n'
RELEASE         = 'o'
SEND            = 'p'
MOVE            = 'q'

# Global Variables
dec_exe = ".."
enc_exe = ".."
dec_fn  = "dec.pub"
enc_fn  = "enc.pub"
dev_id  = None

with open("id.pub") as fn:
    dev_id = fn.read()

# Tests for IDLE State
def test_state(m):
    sp.call("./encrypt '%s' %s < param/a3.param" % (json.dumps(m), dev_id), shell=True)
    #child = sp.Popen("python runbase.py", shell=True, stdout=sp.PIPE, stdin=sp.PIPE, stderr=sp.STDOUT)
    #print child.communicate()
    child = sp.Popen("python runbase.py", shell=True, stdout=sp.PIPE, stdin=sp.PIPE, stderr=sp.STDOUT)
    return child.communicate()[0]

class TestIDLEState(unittest.TestCase):
    def test_idle_start(self):
        m = {"code": IDLE, "debug": True}
        stdout = test_state(m)
        self.assertTrue(IDLE == stdout.strip())

class TestSENDCONFIRMState(unittest.TestCase):
    def test_send_confirm_start(self):
        m = {"code": SEND_CONFIRM, "id": dev_id, "debug": True}
        stdout = test_state(m)
        self.assertTrue(SEND_CONFIRM == stdout.strip())
'''
    def test_send_confirm_reply(self):
        print "confirm reply"
        m = {"code": SEND_CONFIRM, "id": dev_id, "debug": True}
        sp.call("./encrypt '%s' %s < param/a3.param" % (json.dumps(m), dev_id), shell=True)
        sp.Popen("python runbase.py", shell=True, stdout=sp.PIPE, stdin=sp.PIPE, stderr=sp.STDOUT)
        os.system("./decrypt < param/a3.param")
        r = {"code": ASK_DIRECT, "data": "OK"}
        with open(dec_fn) as fn:
            data = json.load(fn)
            print data
            print r
            self.assertTrue(r == data)
'''

class TestSENDDIRECTState(unittest.TestCase):
    def test_send_direct_start(self):
        m = {"code": SEND_DIRECT, "id": dev_id, "debug": True}
        stdout = test_state(m)
        self.assertTrue(SEND_DIRECT == stdout.strip())

class TestRELEASEMSGState(unittest.TestCase):
    def test_release_msg_start(self):
        m = {"code": RELEASE_MSG, "id": dev_id, "debug": True}
        stdout = test_state(m)
        self.assertTrue(RELEASE_MSG == stdout.strip())

class TestFORWARDState(unittest.TestCase):
    def test_foward_start(self):
        m = {"code": FORWARD, "base": dev_id, "msg": "asdf", "debug": True}
        stdout = test_state(m)
        self.assertTrue(FORWARD == stdout.strip())

class TestRELEASEACCState(unittest.TestCase):
    def test_release_acc_start(self):
        m = {"code": RELEASE_ACC, "id": dev_id, "msg": "asdf", "debug": True}
        stdout = test_state(m)
        self.assertTrue(RELEASE_ACC == stdout.strip())

class TestPINGState(unittest.TestCase):
    def test_ping_start(self):
        m = {"code": PING, "id": dev_id, "debug": True}
        stdout = test_state(m)
        self.assertTrue(PING == stdout.strip())

class TestREPLYPINGState(unittest.TestCase):
    def test_reply_ping_start(self):
        m = {"code": REPLY_PING, "id": dev_id, "debug": True}
        stdout = test_state(m)
        self.assertTrue(REPLY_PING == stdout.strip())

class TestUPDATEState(unittest.TestCase):
    def test_update_start(self):
        m = {"code": UPDATE, "id": dev_id, "lng": 09.00, "lat": 12.34, "debug": True}
        stdout = test_state(m)
        self.assertTrue(UPDATE == stdout.strip())

class TestGLOBALPINGState(unittest.TestCase):
    def test_global_ping_start(self):
        m = {"code": GLOBAL_PING, "debug": True}
        stdout = test_state(m)
        self.assertTrue(GLOBAL_PING == stdout.strip())

class TestPROPOGATEState(unittest.TestCase):
    def test_propogate_start(self):
        m = {"code": PROPOGATE, "id": dev_id, "data":{}, "q":[dev_id], "t":[dev_id], "debug": True}
        stdout = test_state(m)
        self.assertTrue(PROPOGATE == stdout.strip())

if __name__ == '__main__':
    unittest.main()
