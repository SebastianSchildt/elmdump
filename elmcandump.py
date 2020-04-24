#!/usr/bin/python3


import configparser
import serial
import sys,io,time 
from datetime import datetime


def waitforprompt(elm):
    while elm.read() != b'>':
        pass

def writetoelm(elm,data):
    #print("Write")
    length=len(data)
    elm.write(data)
    echo=elm.read(length)
    if echo != data:
        print("Not the same {}/{}".format(data, echo))
    #print("Write Done")

def readresponse(elm):
    response=""
    while True:
        d=elm.read()
        if d == b'\r':
            return response
        response=response+d.decode('utf-8')
        #print("DEBUG: "+response)

def executecommand(elm,command, expectok=True):
    writetoelm(elm,command)
    resp=readresponse(elm)
    if expectok and resp.strip() != "OK" :
        print("Invalid response {} for command {}".format(resp,command))
        sys.exit(-1)
    waitforprompt(elm)
    return resp

def initelm(elm, baud, ack):
    print("Detecting ELM...")
    elm.write(b'\r\r')
    waitforprompt(elm)
    writetoelm(elm,b'ATI\r')
    resp=readresponse(elm)
    if not resp.startswith("ELM"):
        print("Unexpected respsne to ATI: {}".format(resp))
        sys.exit(-1)

    waitforprompt(elm)
    print("Enable Headers")
    executecommand(elm,b'AT H1\r')
    print("Enable Spaces")
    executecommand(elm,b'AT S1\r')
    print("Disable DLC")
    executecommand(elm,b'AT D0\r')
    print("Set CAN speed")
    executecommand(elm,b'STP 32\r')
    cmd="STPBR "+str(baud)+"\r"
    executecommand(elm,cmd.encode('utf-8'))
    baud=executecommand(elm,b'STPBRR\r',expectok=False)
    print("Speed is {}".format(baud))
    if ack:
        executecommand(elm,b'STCMM 1\r')
    else:
        executecommand(elm,b'STCMM 0\r')

    
def parseline(f, line):
    #print("DEBUG: parse "+line)
    tf=float(time.time())
    logline="({:.6f}) {} ".format(tf,"vcan0")
    items = line.split()
    if len(items[0]) == 3: #short id
        logline=logline+items[0]+"#"
        del items[0]
    else: #extende id
        logline=logline+items[0]+items[1]+items[2]+items[3]+"#"
        items=items[4:]

    for data in items:
        logline+=data
    f.write(logline+"\n")
    #t(logline) 
    




config = configparser.ConfigParser()

config.read('config.ini')


cancfg=config['can']
sercfg=config['serial']

canspeed=cancfg.get('speed', '500k')
canack=cancfg.getboolean('canack',False)

serialport=sercfg.get('port','/dev/ttyS0')
serialbaud=sercfg.getint('baud', 115200)

outfile="elmdump"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")

print("CAN bitrate      : {}".format(canspeed))
print("ACK CAN frames   : {}".format(canack))
print("Serial port      : {}".format(serialport))
print("Serial baud rate : {}".format(serialbaud))
print("Logging to       : {}".format(outfile))

f=open(outfile,'w')


elm = serial.Serial()
elm.baudrate = serialbaud
elm.port = serialport
elm.timeout=10

elm.open()

if not elm.is_open:
    print("Can not open serial port")
    sys.exit(-1)


initelm(elm, canspeed, canack)

print("Enter monitoring mode...")

elm.write(b'STMA\r')
elm.read(5) #Consume echo
elm.timout=None

while True:
    line=readresponse(elm)
    parseline(f,line)
    print(line)

elm.close()
