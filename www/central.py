from flask import Flask, render_template, request, url_for, jsonify
import os, math
import subprocess as sp
import json
application = Flask(__name__)

# Helper Functions
def cal_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def generate_graph(raw_map):
    graph = {}
    mapa = {}
    for base in raw_map:
        mapa[base.get('base')] = base
    for s in mapa:
        graph[s] = {}
        s1 = mapa.get(s).get("lat")
        s2 = mapa.get(s).get("lng")
        for d in mapa.get(s).get('links'):
            d1 = mapa.get(s).get('lat')
            d2 = mapa.get(s).get('lng')
            dist = cal_distance(s1, s2, d1, d2)
            graph[s][d] = dist
    return graph

def dijkstra(graph,src,dest,visited=[],distances={},predecessors={}):
    """ calculates a shortest path tree routed in src
        obtained at http://www.gilles-bertrand.com/2014/03/dijkstra-algorithm-python-example-source-code-shortest-path.html
    """
    # a few sanity checks
    if src not in graph:
        raise TypeError('The root of the shortest path tree cannot be found')
    if dest not in graph:
        raise TypeError('The target of the shortest path cannot be found')
    # ending condition
    if src == dest:
        # We build the shortest path and display it
        path=[]
        pred=dest
        while pred != None:
            path.append(pred)
            pred=predecessors.get(pred,None)
        #print('shortest path: '+str(path[::-1])+" cost="+str(distances[dest]))
        return  list(reversed(path))
        #return list(reversed(path))
    else :
        # if it is the initial  run, initializes the cost
        if not visited:
            distances[src]=0
        # visit the neighbors
        for neighbor in graph[src] :
            if neighbor not in visited:
                new_distance = distances[src] + graph[src][neighbor]
                if new_distance < distances.get(neighbor,float('inf')):
                    distances[neighbor] = new_distance
                    predecessors[neighbor] = src
        # mark as visited
        visited.append(src)
        # now that all neighbors have been visited: recurse
        # select the non visited node with lowest distance 'x'
        # run Dijskstra with src='x'
        unvisited={}
        for k in graph:
            if k not in visited:
                unvisited[k] = distances.get(k,float('inf'))
        x=min(unvisited, key=unvisited.get)
        return dijkstra(graph,x,dest,visited,distances,predecessors)


@application.route("/")
def hello():
  # Check if runbase.py is running, if no, then run
  bases = []
  if os.path.isfile("run/map.pub"):
      with open("run/map.pub") as fn:
          bases = json.load(fn)
  #bases = [{"base": "A", "lat": 51.5, "lng": -0.09 },{"base": "B", "lat": 51.6, "lng": -0.09 }]
  return render_template("index.html", markers=json.dumps(bases), deviceList=[f for f in os.listdir('../devices/Base') if not f.startswith('.')], droneList=[f for f in os.listdir('../devices/Drone') if not f.startswith('.')])


@application.route("/register", methods=["POST"])
def register():
  input_json = request.form
  #deviceVolume = input_json['deviceVolume']
  deviceName = input_json['deviceName']
  deviceType = input_json['deviceType']
  deviceUser = input_json['deviceUser']
  deviceIP = input_json['deviceIP']
  devicePass = input_json['devicePass']
  if deviceName == "central":
      devicePath = './run'
  else:
    devicePath = '../devices/%s/%s' % (deviceType, deviceName)

  if deviceName in os.listdir("../devices/Drone"):
    return '400'
  if deviceName in os.listdir("../devices/Base"):
    return '400'

  # Create Folder in /devices/{deviceType}/{deviceName}
  os.system("mkdir %s" % (devicePath))
  os.system("mkdir %s/param" % (devicePath))
  os.system("cp ../system/*.pub %s" % (devicePath))
  os.system("cp ../system/param/a3.param %s/param/a3.param" % (devicePath))
  os.system("./../exec/extract %s  < ../system/param/a3.param" % deviceName)
  os.system("mv ../www/*.pub %s" % (devicePath))
  os.system("cp ../source/ibc* %s" % (devicePath))
  os.system("cp ../source/encrypt.c %s" % (devicePath))
  os.system("cp ../source/decrypt.c %s" % (devicePath))
  os.system("cp ../source/compile.py %s" % (devicePath))
  os.system("cp ../source/Comms.py %s" % (devicePath))
  os.system("cp ../source/testxbee.py %s" % (devicePath))
  if deviceType == 'Base':
    os.system("cp ../source/runbase.py %s" % (devicePath))
    os.system("cp ../source/testbase.py %s" % (devicePath))
  else:
    os.system("cp ../source/rundrone.py %s" % (devicePath))
    os.system("cp ../source/testdrone.py %s" % (devicePath))

  # try to send code to pi via scp
  # sshpass -p thesis123 scp -r ../devices/Base/{deviceName} pi%10.0.1.128:/home/pi
  if deviceName != "central":
    os.system("sshpass -p %s scp -r %s/. %s@%s:/home/%s/run" % (devicePass, devicePath, deviceUser, deviceIP, deviceUser))

  return '200'#

@application.route("/master_reset", methods=["POST"])
def master_reset():
  os.system("./../exec/setup < ../system/param/a3.param")

  # generate global key
  gkey = os.urandom(4).encode('hex')
  os.system("./../exec/extract " + gkey + " < ../system/param/a3.param")
  os.system("mv ../www/*.pub ../system")
  os.system("mv ../system/id.pub ../system/global.pub")
  os.system("mv ../system/sqid.pub ../system/gqid.pub")
  return '200'

@application.route("/send_fp", methods=["POST"])
def send_fp():
    input_json = request.form
    drone = input_json['drone']
    base = input_json['base']
    SEND_FP = 'v'
    bases = {}
    if os.path.isfile("run/map.pub"):
        with open("run/map.pub") as fn:
            bases = json.load(fn)
    graph = generate_graph(bases)
    flight_plan = dijkstra(graph, "central", base)
    with open("run/addr.pub") as fn:
        addr_data = json.load(fn)
    addrs = []
    for stop in flight_plan:
        addrs.append(addr_data.get(stop))
    # Get flight_plan from base
    print type(flight_plan)
    print flight_plan
    print addrs
    flight_plan.append('mathey')
    addrs.append('0013a2004175bc91')
    m = {
            "code": SEND_FP,
            "id": "central",
            "flight_plan": flight_plan,
            "addrs": addrs,
            "drone": drone,
            "addr": addr_data.get(drone)
        }
    try:
        with open("run/flight_plan.pub", 'w') as fn:
            fn.write(json.dumps(m))
        return '200'
    except:
        return '400'

@application.route("/update_network", methods=["POST"])
def update_network():
    GLOBAL_PING = 'j'
    with open('run/global.pub') as fn:
        glob_dev = fn.read()
    # Get flight_plan from base
    m = {"code": GLOBAL_PING}
    #TODO have this wait until it sees the map update
    try:
        with open("run/update.pub", 'w') as fn:
            fn.write(json.dumps(m))
        data = None
        if os.path.isfile("run/map.pub"):
            with open("run/map.pub") as fn:
                data = fn.read()
        #while True:
        #    if os.path.isfile('run/map.pub'):
        #        with open("run/map.pub") as fn:
        #            newdata = fn.read()
        #        if data != newdata:
        #            break
        #        #TODO test, will not return and load page until update is complete
        return '200'
    except:
        return '400'

@application.route("/xbee_info", methods=["POST"])
def xbee_info():
    h = json.loads(list(request.form)[0])
    addr = h.get('addr')
    dev = h.get('dev')
    data = {}
    if os.path.isfile("run/addr.pub"):
        with open("run/addr.pub") as fn:
            data = json.load(fn)

    data[dev] = addr
    with open("run/addr.pub", 'w') as fn:
        fn.write(json.dumps(data))
    return '200'

if __name__ == "__main__":
    #output  = sp.check_output("ps", shell=True)
    #running = False
    #for i in output.split("\n"):
    #    if "runbase.py" in i:
    #        running = True
    #if not running:
    #  sp.Popen("cd run && python runbase.py", shell=True)
 
    application.run(host='0.0.0.0', threaded=True)
