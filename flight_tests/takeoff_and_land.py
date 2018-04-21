from dronekit import connect, VehicleMode, LocationGlobalRelative
from pymavlink import mavutil
import time, argparse, sys
sys.path.append('../serial_tests'); import getPixhawkPort as getPort

#Find the Vehcle
path = getPort.find_device(getPort.pixhawk)

parser = argparse.ArgumentParser()
parser.add_argument('--connect', default=path)
args = parser.parse_args()
exit()

#Connect to the Vehicle
print 'Connecting to vehicle on %s' %args.connect
vehicle = connect(args.connect, baud=getPort.pixhawk['baud'], wait_ready=True)

#Function to arm and then takeoff to a user specified altitude
def arm_and_takeoff(aTargetAltitude):
    print 'Basic pre-arm checks'

    #Don't let the user try to arm until autopilot is wait_ready
    while not vehicle.is_armable:
        print 'Waiting for vehicle to initialise...'
        time.sleep(3)

    print 'Arming motors'

    #Copter should arm in GUIDED mode
    vehicle.mode    = vehicleMode("GUIDED")
    vehicle.armed   = True

    while not vehicle.armed:
        print "Waiting for arming..."
        time.sleep(3)

    print 'Taking off!'
    vehicle.simple_takeoff(aTargetAltitude) #Take off to target altitude

    #Check that the vehicle has reached takeoff aTargetAltitude
    while True:
        print "Altitude: " + vehicle.location.global_relative_frame.alt
        #Break and return from function just below target altitude
        if vehicle.location.global_relative_frame.alt >= aTargetAltitude*0.95:
            print "Reached target altitude"
            break
            time.sleep(1)

#Initialize the takeoff sequence to 20m
arm_and_takeoff(20)

print("Take off complete")

#Hover for 10 seconds
time.sleep(10)

print("Now let's land")
vehicle_mode = VehicleMode("LAND")

#Close Vehicle Object
vehicle.close()
