'''
    Test File for rundrone.py
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
    #child = sp.Popen("python rundrone.py", shell=True, stdout=sp.PIPE, stdin=sp.PIPE, stderr=sp.STDOUT)
    #print child.communicate()
    child = sp.Popen("python rundrone.py", shell=True, stdout=sp.PIPE, stdin=sp.PIPE, stderr=sp.STDOUT)
    return child.communicate()[0]

class TestCONFIRMState(unittest.TestCase):
    def test_confirm_start(self):
        m = {"code": CONFIRM, "debug": True}
        stdout = test_state(m)
        self.assertTrue(CONFIRM == stdout.strip())

class TestDIRECTState(unittest.TestCase):
    def test_direct_start(self):
        m = {"code": DIRECT, "id": dev_id, "lng":0.09, "lat": 12.1, "debug": True}
        stdout = test_state(m)
        self.assertTrue(DIRECT == stdout.strip())

class TestASKDIRECTState(unittest.TestCase):
    def test_ask_direct_start(self):
        m = {"code": ASK_DIRECT, "id": dev_id, "debug": True}
        stdout = test_state(m)
        self.assertTrue(ASK_DIRECT == stdout.strip())

class TestRELEASEState(unittest.TestCase):
    def test_release_start(self):
        m = {"code": RELEASE, "id": dev_id, "debug": True}
        stdout = test_state(m)
        self.assertTrue(RELEASE == stdout.strip())

class TestSENDState(unittest.TestCase):
    def test_send_start(self):
        m = {"code": SEND, "base": dev_id, "msg": "askb", "debug": True}
        stdout = test_state(m)
        self.assertTrue(SEND == stdout.strip())

class TestMOVEState(unittest.TestCase):
    def test_move_start(self):
        m = {"code": MOVE, "id": dev_id, "lng":0.09, "lat": 12.1, "debug": True}
        stdout = test_state(m)
        self.assertTrue(MOVE == stdout.strip())

if __name__ == '__main__':
    unittest.main()
