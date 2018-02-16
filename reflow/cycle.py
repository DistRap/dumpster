#!/usr/bin/env python
import os
import sys
import time
import canopen
import select
import datetime

unbuffered_stdin = os.fdopen(sys.stdin.fileno(), 'rb', buffering=0)

# Start with creating a network representing one CAN bus
network = canopen.Network()
network.connect(bustype='socketcan', channel='can0')

if len(sys.argv) > 1:
  print("Performing LSS")
  node_id = network.lss.inquire_node_id()
  network.lss.configure_node_id(1)
  node_id = network.lss.inquire_node_id()
  network.lss.store_configuration()
else:
  node_id = 1

print("Using node_id {}".format(node_id))
node = network.add_node(node_id, 'tempreg.eds')

# Read a variable using SDO
#device_name = node.sdo['Manufacturer device name'].raw
#vendor_struct = node.sdo[0x1018]
#vendor_id = node.sdo[0x1018]
#vendor_id_raw = node.sdo[0x1018][1].raw
#print(vendor_id_raw)

# ------- #
# Profile #
# ------- #

# to 100 in 100 seconds
# from 100 to 110 in 100 seconds
# from 110 to 220 in 120 seconds
# off

# PID
setp = 100
node.sdo['Temperature target'].raw = setp
node.sdo['PID P'].raw = 0.07
node.sdo['PID I'].raw = 0.0015
node.sdo['PID D'].raw = 10.0

# Read PDO configuration from node
#node.pdo.read()
# Transmit SYNC every 100 ms
#network.sync.start(0.1)

# Change state to operational (NMT start)
node.nmt.state = 'OPERATIONAL'

now = datetime.datetime.now()

fmt = "%Y-%m-%d_%H-%M-%S"
f = open('logs/{}'.format(datetime.datetime.strftime(now, fmt)), 'w+')

s = 0
ss = 0
max_t = 180

while True:
  act = node.sdo['Temperature'].raw
  pa = node.sdo['PID P Actual'].raw
  ia = node.sdo['PID I Actual'].raw
  da = node.sdo['PID D Actual'].raw
  pidout = node.sdo['PID Output'].raw
  ce = node.sdo['Control effort'].raw
  x = datetime.datetime.now()
  print("time: {} \t target_t: {} \ttemp: {}".format(s, setp, act))
  f.write("{} {} {} {} {} {} {} {}\n".format(datetime.datetime.strftime(x, fmt), act,
      setp, pa, ia, da, pidout, ce))
  f.flush()
  sys.stdout.flush()

  # temp set
  if s > 100 and act > 100 and ss < 100:
    ss = ss + 1
    setp = 110
    node.sdo['Temperature target'].raw = setp

  if ss > 99:
    ss = ss + 1
    setp = max_t
    node.sdo['Temperature target'].raw = setp
    node.sdo['PID P'].raw = 0.1
    node.sdo['PID D'].raw = 5.0

  if ss > 240 and act > max_t:
    setp = 20
    node.sdo['Temperature target'].raw = setp
    node.sdo['PID D'].raw = 0
    break


  # read stdin 
  if select.select([unbuffered_stdin],[],[],0.0)[0]:
    line = unbuffered_stdin.readline()
    if chr(line[0]) in ['P', 'I', 'D']:
      val = float(line[1:])
      node.sdo['PID {}'.format(chr(line[0]))].raw = val
    else:
      setp = int(line)
      node.sdo['Temperature target'].raw = setp
  time.sleep(1)
  s=s+1

# Disconnect from CAN bus
#network.sync.stop()
network.disconnect()
