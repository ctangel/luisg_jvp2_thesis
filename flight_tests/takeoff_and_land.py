from dronekit import connect, VehicleMode, LocationGlobalRelative
from pymavlink import mavutil
import time, argparse, sys
sys.path.append('../serial_tests'); import getPixhawkPort as getPort

#Find the Vehcle
path = getPort.find_device(getPort.pixhawk)

<<<<<<< HEAD
#parser = argparse.ArgumentParser()
#parser.add_argument('--connect', default=path) #TODO: what does this do?
#args = parser.parse_args()
=======
parser = argparse.ArgumentParser()
parser.add_argument('--connect', default=path)
args = parser.parse_args()
exit()
>>>>>>> 4d6f30b5b5ec314507d34351bf4418b261cc2170

#Connect to the Vehicle
#print 'Connecting to vehicle on %s' %args.connect

alt = int(sys.argv[1])
hov = int(sys.argv[2])

print 'Connecting to vehicle on %s' %path
#vehicle = connect(args.connect, baud=getPort.pixhawk['baud'], wait_ready=True)
vehicle = connect(path, baud=getPort.pixhawk['baud'], wait_ready=True)
#TODO: put into a try and catch block; add support for failure to connect

#Function to arm and then takeoff to a user specified altitude
def arm_and_takeoff(aTargetAltitude):
    print 'Basic pre-arm checks'

    #Don't let the user try to arm until autopilot is wait_ready
#    while not vehicle.is_armable:
 #       print 'Waiting for vehicle to initialise...'
  #      time.sleep(3)

    print 'Arming motors'

    #Copter should arm in GUIDED mode
    vehicle.mode    = VehicleMode("GUIDED")
    vehicle.armed   = True

    
    while not vehicle.armed:
        print "Waiting for arming..."
        time.sleep(3)
    

#    while not vehicle.mode.name=='GUIDED' and not vehicle.armed and not api.exit:
 #       print 'Getting ready to take off, waiting for arming...'
#time.sleep(1)
 
    print 'Taking off!'
    vehicle.simple_takeoff(aTargetAltitude) #Take off to target altitude

    #Check that the vehicle has reached takeoff aTargetAltitude
    while True:
        print "Altitude: " + str(vehicle.location.global_relative_frame.alt)
        #Break and return from function just below target altitude
        if vehicle.location.global_relative_frame.alt >= aTargetAltitude*0.95:
            print "Reached target altitude"
            break
<<<<<<< HEAD
        time.sleep(1)
#Initialize the takeoff sequence to alt meters
arm_and_takeoff(alt)
=======
            time.sleep(1)

#Initialize the takeoff sequence to 20m
arm_and_takeoff(20)
>>>>>>> 4d6f30b5b5ec314507d34351bf4418b261cc2170

print("Take off complete")

#Hover for hov seconds
time.sleep(hov)

print("Now let's land")
vehicle_mode = VehicleMode("LAND")

#Close Vehicle Object
vehicle.close()
