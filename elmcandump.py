#!/usr/bin/python3


import configparser
import serial
import sys,io,time,signal
import threading
from datetime import datetime
import queue



def sigint_received(signum, frame):
    f.flush()
    f.close()
    print("Close worker")
    q.put(None)
    time.sleep(1)
    print("Terminate program")
    sys.exit(0)

#Parsing and saving in seperate thread, to prevent loosing data
def processline(q,f):
    while True:
        line=q.get()
        if line==None:
            print("Received nothing from queue. Terminate thread")
            return
        parseline(f,line)
        #print(line)
        q.task_done()


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
    try:
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
    except:
        print("Error. Log line {}, items {}".format(line,items))
    #t(logline) 
    
class SerReadLineHelper:
    def __init__(self, s):
        self.buf = bytearray()
        self.s = s
    
    def readline(self):
        i = self.buf.find(b"\r")
        if i >= 0:
            r = self.buf[:i+1]
            self.buf = self.buf[i+1:]
            return r
        while True:
            i = max(1, min(2048, self.s.in_waiting))
            data = self.s.read(i)
            i = data.find(b"\r")
            if i >= 0:
                r = self.buf + data[:i+1]
                self.buf[0:] = data[i+1:]
                return r
            else:
                self.buf.extend(data)



config = configparser.ConfigParser()

config.read('config.ini')


cancfg=config['can']
sercfg=config['serial']

canspeed=cancfg.get('speed', '500k')
canack=cancfg.getboolean('canack',False)

serialport=sercfg.get('port','/dev/ttyS0')
serialbaud=sercfg.getint('baud', 115200)

outfile="elmdump-"+datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")

print("CAN bitrate      : {}".format(canspeed))
print("ACK CAN frames   : {}".format(canack))
print("Serial port      : {}".format(serialport))
print("Serial baud rate : {}".format(serialbaud))
print("Logging to       : {}".format(outfile))

f=open(outfile,'w')

q=queue.Queue()

signal.signal(signal.SIGINT, sigint_received)


elm = serial.Serial()
elm.baudrate = serialbaud
elm.port = serialport
elm.timeout=10

elm.open()

if not elm.is_open:
    print("Can not open serial port")
    sys.exit(-1)


initelm(elm, canspeed, canack)

t = threading.Thread(target=processline, args=(q,f,))
t.start()

print("Enter monitoring mode...")

elm.write(b'STMA\r')
elm.read(5) #Consume echo
elm.timout=None

#Buffered readline wrapper, as pyserial's methods are superslow
rlh=SerReadLineHelper(elm)

while True:
    line=rlh.readline()
    #print(line)
    q.put(line.decode('utf-8'))
    
elm.close()
