#! /usr/bin/python
'''
 * run.py
 *
 * Runs on a device (drone or base) and continuously scans for messages send
 * decryptes them.
 *
 * Author: Luis Gonzalez-Yante
 *
'''
import hashlib
import os
import random
import json

# CODES
CONFIRM = '00'
DIRECT  = '01'
RELEASE = '10'
PING    = '11'

enc_file_name = 'enc.pub'
dec_file_name = 'dec.pub'
digest = None
message = ' '
email = 'fnewaj@princeton.edu'
data = {'code': '00'}

#print 'START'
while True:
    #print 'while true'
    m = hashlib.md5()
 
    if os.path.isfile(enc_file_name):
        #print 'enc.pub exists'
        with open(enc_file_name) as f:
            #print 'open enc.pub'
            contents = f.read()
            m.update(contents)
            if digest != m.digest():
                digest = m.digest()
                # decrypt
                os.system('./decrypt < param/a3.param')
                with open(dec_file_name) as ff:
                    #cc = ff.read()
                    #print cc
                    #cc = "\'%s\'" % contents
                    data2 = json.load(ff);
                    #data2 = json.loads("\'" + contents + "\'");
                    print data2
                    code = data2['code']
                    if code == CONFIRM:
                        pass
                    elif code == DIRECT:
                        pass
                    elif code == RELEASE:
                        pass
                    elif code == PING:
                        pass
                    else:
                        print 'error: add code to throw an exception'

                    # send reply
            r = random.random()
            data['value'] = r
            #if r > 0.9:
            #else:
            message = json.dumps(data)
            os.system('./encrypt \''+message+ '\' ' + email+'< param/a3.param')
