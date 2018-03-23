# Intercession Steps to Achieve the Goal

The overarching goal is to plant the seeds necessary to build out the software needed to complete the project.

The project has three components that require software

1. Central Base
2. Base
3. Drones      

## Focus: Central Base

The central base is in charge of the following tasks

1. Registering other Drones and Bases
2. Providing route list to drones
3. Maintaining and updatings it's network map

### Registering Other Drones and Bases

The following steps are needed to register a device (drone or base):

1. Create a user interface to facilate the following actions.
2. Connect the device the Central Base, via Ethernet or USB
3. Send device's MAC address and other necessary information to the Central Base
5. The Central Base generates a public key and private with the MAC address and sends it to the device
6. The Central Base next provides the device with pre-setting.

#### Create a user interface to faciliate the following actions

Creating a user interface is a bit tricky. The encryption code is written in C, so the user interface must be able to call these C programs. The first choice to create the user interfaces was to use C specific GUI library like GTK+, but we decided against this since it would require spending time learning a new libray and debugging. Therefore we decided to look into web.

We decided to use a local webserver to run the C programs and interface with the base's hardware, and for a webpage to handle the input of a user. 

#### Connect the device to the Central base, Via Ethernet or USB

We expected to connect the devices directly to the Central Base, however, this proved to be too burdensome. Instead, we will opt to connect some from of flash drive, register the device and copy over the file the flash drive. This flash drive will then be used to copy the file over the device.

#### Send the Device's MAC Address and other necessary information to the Central Base

Instead of automating this process, we will have the register do this manually.

#### The Central Base generates a public and private key with the MAC address and sends it to the device

The Central Base does not verify that the supplied ID for the device is a MAC address, but it will copy over the private and public key to the device.

#### The Central Base Provides the Device with Pre-Settings

Under the param folder, and exec folder, we copy over the necessary files needed to fully run the system. These files include

* decrypt (exe)
* encrypt (exe)
* ibc (exe)
* global.pub (global key)
* gid.pub (private global key)
* id.pub (id of device)
* p.pub (public master key)
* ppub.pub (generator)
* sqid.pub (private secret key)
* param/a3.param (pairing defaults)
* run(drone or base).py (master device to run system)

### Providing route list to drones
TODO

### Maintaining and updatings it's network map
TODO

## Focus: Base
TODO

## Focus: Drone

The drone is responsible for the following:

1. Listening for Broadcasts and writing encrypted data to file
2. Parsing the Encrypted data and acting on the commands
3. Sending out Ecrypted Broadcasts

### Listening for Broadcasts and writing encrypted data to file
TODO [waiting until James has settled on systemt to broadcast]

### Parsing the Encrypted data and acting on the commands

#### Commands

The following commands, the drone will need to know how to do:

* Confirm Connection
* Request Direction
* Request Release

##### Confirm Connection

The drone will connect to and confirm that is is connected to a base.

CODE: 00

Protocol:

1. Drone send id to Base
2. Base confirms to Drone that is has connected

Message: 

Drone to Base
{
  "code": "00",
  "seq": 1,
  "id": id
} 

Base to Drone
{
  "code": "00",
  "seq": 2,
  "data": "OK"
} 

##### Request Connection

CODE: 01

Protocol:

1. Drone requests for direction of provided base
2. Base send direction to requested Base


### Sending out Ecrypted Broadcasts



gcc ibe.c -o ibe -lpbc -lgmp -lssl -lcrypto


Resources used:
http://ieeexplore.ieee.org/document/5600456/
https://crypto.stanford.edu/~dabo/papers/bfibe.pdf
http://people.csail.mit.edu/alinush/6.857-spring-2015/papers/bilinear-maps.pdf
https://courses.cs.washington.edu/courses/csep590/06wi/finalprojects/youngblood_csep590tu_final_paper.pdf

