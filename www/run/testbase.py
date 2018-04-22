'''
    Test File for runbase.py
'''
import subprocess as sp
import json
import unittest
import os
import time

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
START_TAKE_OFF  = 'u'

# Drone Codes
CONFIRM         = 'l'
DIRECT          = 'm'
ASK_DIRECT      = 'n'
RELEASE         = 'o'
SEND            = 'p'
MOVE            = 'q'
ABORT           = 'r'
TAKE_OFF        = 's'
CONFIRM_FP      = 't'

# Global Variables
dec_exe = ".."
enc_exe = ".."
dec_fn  = "dec.pub"
enc_fn  = "enc.pub"
deb_fn  = "deb.pub"
dev_id  = None
fn_num  = 0

with open("id.pub") as fn:
    dev_id = fn.read()

# Tests for IDLE State
def test_state(m):
    sp.call("./encrypt '%s' %s < param/a3.param" % (json.dumps(m), dev_id), shell=True)
    time.sleep(2)
    while not os.path.exists(deb_fn):
        pass
    with open(deb_fn) as fn:
        stdout = fn.read()
    return stdout

def silent_rm(fn):
    try:
        os.remove(fn)
    except:
        pass

class TestIDLEState(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.child = sp.Popen("python runbase.py", shell=True)
        time.sleep(15)


    @classmethod
    def tearDownClass(self):
        output = sp.check_output("pgrep -a python", shell=True)
        pid = None
        for i in output.split("\n"):
            if "runbase.py" in i:
                pid = i.split(" ")[0]
        if pid != None:
            sp.Popen("sudo kill %s" % (pid), shell=True)

    def setUp(self):
        pass
        #silent_rm(dec_fn)
        #silent_rm(enc_fn)
        silent_rm(deb_fn)

    def test_idle_start(self):
        m = {"code": IDLE, "debug": True}
        stdout = test_state(m)
        self.assertTrue(IDLE == stdout.strip())

    def test_send_confirm_start(self):
        m = {"code": SEND_CONFIRM, "id": dev_id, "debug": True}
        stdout = test_state(m)
        self.assertTrue(SEND_CONFIRM == stdout.strip())
 
    def test_send_direct_start(self):
        m = {"code": SEND_DIRECT, "id": dev_id, "debug": True}
        stdout = test_state(m)
        self.assertTrue(SEND_DIRECT == stdout.strip())

    def test_release_msg_start(self):
        m = {"code": RELEASE_MSG, "id": dev_id, "debug": True}
        stdout = test_state(m)
        self.assertTrue(RELEASE_MSG == stdout.strip())

    def test_foward_start(self):
        m = {"code": FORWARD, "base": dev_id, "msg": "asdf", "debug": True}
        stdout = test_state(m)
        self.assertTrue(FORWARD == stdout.strip())
    
    def test_release_acc_start(self):
        m = {"code": RELEASE_ACC, "id": dev_id, "msg": "asdf", "debug": True}
        stdout = test_state(m)
        self.assertTrue(RELEASE_ACC == stdout.strip())

    def test_ping_start(self):
        m = {"code": PING, "id": dev_id, "debug": True}
        stdout = test_state(m)
        self.assertTrue(PING == stdout.strip())

    def test_reply_ping_start(self):
        m = {"code": REPLY_PING, "id": dev_id, "debug": True}
        stdout = test_state(m)
        self.assertTrue(REPLY_PING == stdout.strip())

    def test_update_start(self):
        m = {"code": UPDATE, "id": dev_id, "lng": 09.00, "lat": 12.34, "debug": True}
        stdout = test_state(m)
        self.assertTrue(UPDATE == stdout.strip())

    def test_global_ping_start(self):
        m = {"code": GLOBAL_PING, "debug": True}
        stdout = test_state(m)
        self.assertTrue(GLOBAL_PING == stdout.strip())

    #def test_propogate_start(self):
    #    m = {"code": PROPOGATE, "id": dev_id, "data":{}, "q":[dev_id], "t":[dev_id, dev_id], "debug": True}
    #    stdout = test_state(m)
    #    self.assertTrue(PROPOGATE == stdout.strip())

"""
class TestSENDCONFIRMState(unittest.TestCase):
    def test_send_confirm_start(self):
        m = {"code": SEND_CONFIRM, "id": dev_id, "debug": True}
        stdout = test_state(m)
        self.assertTrue(SEND_CONFIRM == stdout.strip())
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
"""
if __name__ == '__main__':
    unittest.main()
