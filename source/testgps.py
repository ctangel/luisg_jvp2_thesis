import gps
import os
import time

# Setup GPS Serial Port Connection
#os.system("sudo su")
os.system("systemctl stop gpsd.socket")
os.system("systemctl disable gpsd.socket")
os.system("gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock")
time.sleep(5)

# Listen on port 2947 (gpsd) of localhost
session = gps.gps("localhost", "2947")
session.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
reset_timer = 0 
while True:
    try:
    	report = session.next()
		# Wait for a 'TPV' report and display the current time
		# To see all report data, uncomment the line below
		# print report
        #print report
        if report['class'] == 'TPV':
            if hasattr(report, 'lat') and hasattr(report, 'lon'):
                print "%f %f" % (report.lat, report.lon)
            if hasattr(report, 'mode'):
                if report.mode == 1:
                    print "rest_timer: %d" % (reset_timer)
                    reset_timer += 1
                if reset_timer > 40:
                    #os.system("killall gpsd")
                    #os.system("gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock")
                    #time.sleep(10)
                    #session = gps.gps("localhost", "2947")
                    #session.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)
                    reset_timer = 0
    except KeyError:
		pass
    except KeyboardInterrupt:
		quit()
    except StopIteration:
		session = None
		print "GPSD has terminated"
