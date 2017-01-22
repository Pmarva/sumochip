from CHIP_IO import GPIO
from CHIP_IO import SOFTPWM as PWM
import sys
import signal
import os

from time import sleep

# 5% duty -- 1ms forward
# 7.5 duty -- 1.5ms stop
# 10% duty -- 2ms reverse


print "Starting sumoServo process"
pid = os.getpid()
pin = sys.argv
print(str(pin[1]) +' '+ str(pin[2]))

RIGHT = pin[1]
LEFT = pin[2]

with open('/var/tmp/sumoServoPid.txt', 'w') as f:
    f.write(str(pid))

#def unexport(pin):
#    if os.path.exists("/sys/class/gpio/gpio{}".format(pin)):
#        with open("/sys/class/gpio/unexport", "w") as fh:
#                fh.write(str(pin))

#unexport(120)
#unexport(119)

PWM.start(RIGHT, 0, 50) #parem ratas
PWM.start(LEFT, 0, 50) #vasak ratas




#def fwd1(signum, frame): PWM.set_duty_cycle("LCD-CLK", 5)
#def rev1(signum, frame): PWM.set_duty_cycle("LCD-CLK", 10)
#def stop1(signum, frame): PWM.set_duty_cycle("LCD-CLK", 0)
#def fwd2(signum, frame): PWM.set_duty_cycle("LCD-D23", 10)
#def rev2(signum, frame): PWM.set_duty_cycle("LCD-D23", 5)
#def stop2(signum, frame): PWM.set_duty_cycle("LCD-D23", 0)

def forward(signum, frame):
    PWM.set_duty_cycle(RIGHT, 5)
    PWM.set_duty_cycle(LEFT, 10)

def backward(signum, frame):
    PWM.set_duty_cycle(RIGHT, 10)
    PWM.set_duty_cycle(LEFT, 5)

def stop(signum, frame):
    PWM.set_duty_cycle(RIGHT, 0)
    PWM.set_duty_cycle(LEFT, 0)

def left(signum, frame):
    PWM.set_duty_cycle(RIGHT, 5)
    PWM.set_duty_cycle(LEFT, 5)

def right(signum, frame):
    PWM.set_duty_cycle(RIGHT, 10)
    PWM.set_duty_cycle(LEFT, 10)


#PAREM RATAS
#signal.signal(30, fwd1)
#signal.signal(10, rev1)
#signal.signal(16, stop1)

#VASAK RATAS
#signal.signal(31, fwd2)
#signal.signal(12, rev2)
#signal.signal(17, stop2)

signal.signal(30, forward)
signal.signal(10, backward)
signal.signal(16, stop)
signal.signal(31, right)
signal.signal(12, left)

#if not os.fork():
#    print "Hello I am", os.getpid()
while True:
    sleep(9999)
