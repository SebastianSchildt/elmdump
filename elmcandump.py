#!/usr/bin/python3


import configparser
import serial
import sys,io


config = configparser.ConfigParser()

config.read('config.ini')


cancfg=config['can']
sercfg=config['serial']

canspeed=cancfg.get('speed', '500k')
canack=cancfg.getboolean('canack',False)

serialport=sercfg.get('port','/dev/ttyS0')
serialbaud=sercfg.getint('baud', 115200)


print("CAN bitrate      : {}".format(canspeed))
print("ACK CAN frames   : {}".format(canack))
print("Serial port      : {}".format(serialport))
print("Serial baud rate : {}".format(serialbaud))


elm = serial.Serial()
elm.baudrate = serialbaud
elm.port = serialport
elm.timeout=10

elm.open()

if not elm.is_open:
    print("Can not open serial port")
    sys.exit(-1)

elmio = io.TextIOWrapper(io.BufferedRWPair(elm, elm), newline='\r')


elmio.write('ATI\n')
elmio.flush()

resp=elmio.readline()

print("Got: "+resp)


elm.close()
