import serial
from serial.tools import list_ports
from datetime import datetime
import logging, logging.config
import lzma
import signal
import argparse
import os
import json
import time

LOG_DIRECTORY   = '/experiments/monroe/nne/log'
DATA_DIRECTORY  = '/experiments/monroe/nne/'
NodeFile = '/etc/nodeid'

class gps_device():
    USB_ID = "067b:2303"
    def __init__(self, serial_port = None):
        self.ser = None
        self.serial_port = serial_port
        if not serial_port:
            self.serial_port = self.get_serial_port()
        else:
            self.serial_port = self.connect(self.serial_port)

    def get_serial_port(self):
        usb_device = list_ports.grep(self.USB_ID)
        if usb_device :
            for udev in usb_device:
                if self.connect(udev.device):
                    return udev.device
        return None

    def connect(self, port):
        try:
            self.ser = serial.Serial(port= port, baudrate=4800, parity=serial.PARITY_NONE,
                               stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=5)
        except Exception as e:
            return False
        if self.ser.isOpen():
            return True

    def _read(self, slice):
        while True:
            if self.ser.isOpen():
                line = self.ser.readline()
                if slice.encode('ascii') in line:
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                    return self.parse_line(ts, line.decode('ascii'))

    def parse_line(self, ts, line):
        items = line.split(',')
        return {'ts': ts, 'lat': str(self.decimal_degrees(*self.dm(float((items[3])))))+items[4],
                    'lon': str(self.decimal_degrees(*self.dm(float((items[5])))))+items[6], 'speed': items[7]}

    def dm(self, x):
        degrees = int(x) // 100
        minutes = x - 100*degrees
        return degrees, minutes

    def decimal_degrees(self, degrees, minutes):
        return format(degrees + minutes/60, '.6f') 

    def disconnect(self):
        self.ser.close()

op = argparse.ArgumentParser(description='NNE metadata')
op.add_argument('--interval', help='Sending time interval', type=int, default=60)
opts = op.parse_args()

running = True
restart = False
compress = True

try:
    NodeIDFile = open(NodeFile)
    nodeID = int(NodeIDFile.read())
except:
    logging.log("Failed to get nodeID")
    exit(1)

filename = DATA_DIRECTORY + 'gps_' + str(nodeID) + '.dat'

def signalHandler(signum, frame):
    global running
    running = False

def CompressingRotator(source, dest):
    os.rename(source, dest)
    f_in = open(dest, 'rb')
    f_out = lzma.LZMAFile('%s.xz' % dest, 'wb')
    f_out.writelines(f_in)
    f_out.close()
    f_in.close()
    os.remove(dest)

MBBM_LOGGING_CONF = {
   'version': 1,
   'handlers': {
      'default': {
         'level': 'DEBUG',
         'class': 'logging.handlers.TimedRotatingFileHandler',
         'formatter': 'standard',
         'filename': (LOG_DIRECTORY + '/gps_%d.log') % (nodeID),
         'when': 'D'
      },
      'mbbm': {
         'level': 'DEBUG',
         'class': 'logging.handlers.TimedRotatingFileHandler',
         'formatter': 'mbbm',
         'filename': (DATA_DIRECTORY + '/gps_%d.dat') % (nodeID),
         'when': 'S',
         'interval': 15,
      }
   },
   'formatters': {
      'standard': {
         'format': '%(asctime)s %(levelname)s [PID=%(process)d] %(message)s'
      },
      'mbbm': {
         'format': '%(message)s',
      }
   },
   'loggers': {
      'mbbm': {
         'handlers': ['mbbm'],
         'level': 'DEBUG',
         'propagate': False,
      }
   },
   'root': {
      'level': 'DEBUG',
      'handlers': ['default'],
   }
}

logging.config.dictConfig(MBBM_LOGGING_CONF)
mlogger = logging.getLogger('mbbm')
if compress == True:
   for loghandler in mlogger.handlers[:]:
      loghandler.rotator = CompressingRotator

signal.signal(signal.SIGINT,  signalHandler)
signal.signal(signal.SIGTERM, signalHandler)

gps = gps_device()

while running:
    logging.debug("gps-dump starting")
    if restart:
        try:
            gps.disconnect()
        except:
            pass

        try:
            gps = gps_device()
        except Exception as e:
            logging.debug('Connection error: %s', e)
            restart = True
            time.sleep(5)
            continue
    restart = False

    while running and not restart:
        try:
            result = gps._read(slice='GPRMC')
            if result:
                result['node_id'] = nodeID
                mlogger.info("%s", json.dumps(result))
            else:
                restart = True
        except Exception as e:
            logging.debug("gps-dump error: %s", e)
            restart = True
            time.sleep(15)

try:
    gps.disconnect()
except:
    pass

logging.debug("gps-dump Exiting")
