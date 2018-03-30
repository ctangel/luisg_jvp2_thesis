from flask import Flask, render_template, request, url_for, jsonify
import os
application = Flask(__name__)

@application.route("/")
def hello():
  return render_template("index.html", my_string="Wheeeee!", undeviceList=os.listdir('/Volumes'),  deviceList=os.listdir('../devices/Base'))

@application.route("/register", methods=["POST"])
def register():
  input_json = request.form
  #deviceVolume = input_json['deviceVolume']
  deviceName = input_json['deviceName']
  deviceType = input_json['deviceType']
  deviceUser = input_json['deviceUser']
  deviceIP = input_json['deviceIP']
  devicePass = input_json['devicePass']
  devicePath = '../devices/' + deviceType    

  if deviceName in os.listdir("../devices/Drone"):
    return '400'
  if deviceName in os.listdir("../devices/Base"):
    return '400'
    
  # Create Folder in /devices/{deviceType}/{deviceName}
  os.system("mkdir %s/%s" % (devicePath, deviceName))
  os.system("mkdir %s/%s/param" % (devicePath, deviceName))
  os.system("cp ../system/*.pub %s/%s" % (devicePath, deviceName))
  os.system("cp ../system/param/a3.param %s/%s/param/a3.param" % (devicePath, deviceName))
  os.system("./../exec/extract %s  < ../system/param/a3.param" % deviceName)
  #os.system("./../source/extract.c %s  < ../system/param/a3.param" % deviceName)
  os.system("mv ../www/*.pub %s/%s" % (devicePath, deviceName))
  #os.system("cp ../exec/ibc* %s/%s" % (devicePath, deviceName))
  os.system("cp ../source/ibc* %s/%s" % (devicePath, deviceName))
  #os.system("cp ../exec/encrypt %s/%s" % (devicePath, deviceName))
  os.system("cp ../source/encrypt.c %s/%s" % (devicePath, deviceName))
  #os.system("cp ../exec/decrypt %s/%s" % (devicePath, deviceName))
  os.system("cp ../source/decrypt.c %s/%s" % (devicePath, deviceName))
  os.system("cp ../source/compile.py %s/%s" % (devicePath, deviceName))
  if deviceType == 'Base':
    os.system("cp ../source/runbase.py %s/%s" % (devicePath, deviceName))
    os.system("cp ../source/testbase.py %s/%s" % (devicePath, deviceName))
  else:
    os.system("cp ../source/rundrone.py %s/%s" % (devicePath, deviceName))
    os.system("cp ../source/testdrone.py %s/%s" % (devicePath, deviceName))
  #os.system("cp -r %s/%s /Volumes/'%s'" % (devicePath, deviceName, deviceVolume))
  
  # try to send code to pi via scp
  # sshpass -p thesis123 scp -r ../devices/Base/{deviceName} pi%10.0.1.128:/home/pi
  os.system("sshpass -p %s scp -r %s/%s/. %s@%s:/home/%s/run" % (devicePass, devicePath, deviceName, deviceUser, deviceIP, deviceUser))

  return '200'#

@application.route("/master_reset", methods=["POST"])
def master_reset():
  os.system("./../exec/setup < ../system/param/a3.param")

  # generate global key
  gkey = os.urandom(36).encode('hex')
  os.system("./../exec/extract " + gkey + " < ../system/param/a3.param")
  os.system("mv ../www/*.pub ../system")
  os.system("mv ../system/id.pub global.pub")
  os.system("mv ../system/sqid.pub gqid.pub")
  return '200'
if __name__ == "__main__":
  application.run(host='0.0.0.0')
