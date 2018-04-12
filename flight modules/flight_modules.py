from dronekit import connect, VehicleMode, LocationGlobalRelative, LocationGlobal
from pymavlink import mavutil
import time, argparse, sys
sys.path.append('../serial_tests'); import getPixhawkPort as getPort

#Find the Vehcle
path = getPort.find_device(getPort.pixhawk)

#TODO: what does this do? TODO: where did you get this code from James, god damnnit!
parser = argparse.ArgumentParser()
parser.add_argument('--connect', default=path)
args = parser.parse_args()
#exit()

#Connect to the Vehicle
print 'Connecting to vehicle on %s' %args.connect
vehicle = connect(args.connect, baud=getPort.pixhawk['baud'], wait_ready=True)

#Download the vehicle waypoints and commapnds
cmds = vehicle.commands
cmds.clear()
cmds.upload()


#location is of the class dronekit.LocationGlobal(lat,lon,alt=None)
def goto_GPS(location):
    #not necessary b/c  simple_goto() will set the vehicle mode to GUIDED
    #vehicle.mode = VehicleMode("GUIDED")
    simple_goto(location)


def get_distance(location1, location2):


def main:

    lat = gotLat() #get target latitude
    lon = gotLon() #get target longitude
    alt = gotAlt() #get target Altitude

    newLoc = LocationGlobal(lat, lon, alt)
