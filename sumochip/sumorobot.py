from __future__ import print_function

import os
import sys
import pid
import traceback
from axp209 import AXP209
from time import sleep
from threading import Thread
import json
import os.path

if sys.version_info[0] < 3:
    from ConfigParser import SafeConfigParser as ConfigParser
    from ConfigParser import NoOptionError, NoSectionError
else:
    from configparser import ConfigParser, NoOptionError, NoSectionError


try:
    from CHIP_IO import GPIO
    from CHIP_IO import SOFTPWM as PWM
    __use_chip_io__ = True
except ImportError:
    __use_chip_io__ = False


VALID_PINS = {"sensor_power",
              "enemy_left",
              "enemy_right",
              "line_left",
              "line_right",
              "line_front",
              "green_led",
              "yellow_led",
              "red_led",
              "blue_led"}

def unexport(pin):
    if os.path.exists("/sys/class/gpio/gpio{}".format(pin)):
        with open("/sys/class/gpio/unexport", "w") as fh:
            fh.write(str(pin))

def map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

class AttributeDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

class ChipIOPin(object):

    def __init__(self, pin):
        self.pin = pin
        self.direction = None

    @property
    def value(self):
        if self.direction != "in":
            self.direction = "in"
            GPIO.setup(self.pin, GPIO.IN)
        return GPIO.input(self.pin)

    @value.setter
    def value(self, val):
        if self.direction != "out":
            self.direction = "out"
            GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.HIGH if val else GPIO.LOW)


class PythonIOGPIOExportException(Exception):
    pass


class PythonIOPin(object):

    def __init__(self, pin):
        self.pin = pin
        self.path = path = "/sys/class/gpio/gpio{}".format(pin)
        self.direction = "in"
        if not os.path.exists(path):
            with open("/sys/class/gpio/export", "w") as fh:
                try:
                    fh.write(str(pin))
                except IOError as err:
                    raise PythonIOGPIOExportException("GPIO {} export failed".format(pin))
        if not os.path.exists(path):
            raise PythonIOGPIOExportException("GPIO {} export failed".format(pin))
        self.fhr = open(os.path.join(path, "value"), "r")
        self.fhw = open(os.path.join(path, "value"), "w")

    @property
    def value(self):
        fhr = self.fhr
        fhr.seek(0)
        try:
            return int(fhr.read())
        except:
            return 0

    @value.setter
    def value(self, val):
        if self.direction != "out":
            self.direction = "out"
            with open(os.path.join(self.path, "direction"), "w") as fh:
                fh.write("out")

        self.fhw.write(str(int(val)))
        self.fhw.flush()


class NoIOPin(object):
    """Stub class for I/O pins that don't have a real gpio pin"""
    pin = None
    value = 0

class IOPollThread(Thread):
    """Polls the IO pins"""

    def __init__(self, io_pins, poll_freq):
        Thread.__init__(self)
        self.io_pins = io_pins
        self._stopped_ = False
        self._values_ = {}
        self.poll_freq = poll_freq
        self.daemon = True
        self.update_io_values()
        self.start()

    def run(self):
        while not self._stopped_:
            self.update_io_values()
            sleep(self.poll_freq)

    def update_io_values(self):
        for name, pin in self.io_pins.items():
            self._values_[name] = pin.value

    def __getitem__(self, name):
        return self._values_[name]


class IOProxy(object):
    """Proxies IO access to pins through IOPollThread"""

    def __init__(self, io_pin, io_name, io_poll_thread):
        self.io_pin = io_pin
        self.io_name = io_name
        self.io_poll_thread = io_poll_thread

    @property
    def value(self):
        return self.io_poll_thread[self.io_name]

    @value.setter
    def value(self, value):
        self.io_pin.value = value

class ConfigFileNotFound(Exception):
    pass


class Sumorobot(object):

    def __init__(self, config_file=None):
        self.io = AttributeDict()
        self.io_proxies = {}
        self.config = config = ConfigParser()
        self.name = 'No name'
        if not config_file:
            if os.path.exists("/etc/sumorobot/sumorobot.ini"):
                config_file = "/etc/sumorobot/sumorobot.ini"
            if os.path.exists("sumorobot.ini"):
                config_file = "sumorobot.ini"
       

        if not config_file:
            raise ConfigFileNotFound("No config files found")
        print("Using config file '{}'".format(config_file))

        if sys.version_info[0] < 3:
            import codecs
            with codecs.open(config_file, 'r', encoding='utf-8') as fh:
                config.readfp(fh)
        else:
            config.read(config_file, encoding='utf-8')

        force_use_chip_io = False
        self.axp209 = None
        if "sumorobot" in config.sections():
            sumo_conf = config.options("sumorobot")
            if "use_chip_io" in sumo_conf and config.get("sumorobot", "use_chip_io"):
                force_use_chip_io = config.getboolean("sumorobot", "use_chip_io")
                print("override use_chip_io", __use_chip_io__)

            if "axp209" in sumo_conf:
                i2c_bus = config.getint("sumorobot", "axp209")
                print("Using axp209 library")
                self.axp209 = AXP209(i2c_bus)
            else:
                self.axp209 = None
            self.lineColor = config.getint("sumorobot", "blackLine")
            self.name = config.get("sumorobot","voistlejaNimi")

        if "ChipIO" in config.sections() and (__use_chip_io__ or force_use_chip_io):
            print("Using ChipIO")
            io_conf = config.options("ChipIO")
            chip_io_pins = {key for key, val in config.items("ChipIO") if val} & VALID_PINS
            used_pins = set(chip_io_pins)
            print("ChipIO pins: ", ", ".join(str(pin) for pin in chip_io_pins))
            non_chip_io_pins = VALID_PINS - chip_io_pins

            try:
                stop_on_zero = config.getboolean("ChipIO", "motor_stop_on_zero_speed")
            except NoOptionError:
                stop_on_zero = False

            for pin_name in chip_io_pins:
                unexport(config.get("PythonIO", pin_name))
                self.io[pin_name] = ChipIOPin(config.get("ChipIO", pin_name))

        else:
            used_pins = set()
            non_chip_io_pins = VALID_PINS

        if "PythonIO" in config.sections():
            print("Using PythonIO")
            io_conf = config.options("PythonIO")
            python_io_pins = {key for key, val in config.items("PythonIO") if val} & VALID_PINS
            python_io_pins -= used_pins
            print("PythonIO pins: ", ", ".join(str(pin) for pin in python_io_pins))
            non_python_io_pins = non_chip_io_pins - python_io_pins

            for pin_name in python_io_pins:
                self.io[pin_name] = PythonIOPin(config.get("PythonIO", pin_name))
        else:
            non_python_io_pins = non_chip_io_pins - used_pins


        unconfigured_pins = non_python_io_pins
        if unconfigured_pins:
            for pin_name in unconfigured_pins:
                self.io[pin_name] = NoIOPin()

        io_poll_freq = 0.01
        try:
            io_poll_freq = self.config.getint("sumorobot", "io_poll_freq")
        except (NoSectionError, NoOptionError):
            pass
        self.io_poll_thread = IOPollThread(self.io, io_poll_freq)

        for name, pin in self.io.items():
            if isinstance(pin, NoIOPin):
                continue
            self.io_proxies[pin_name] = IOProxy(pin, name, self.io_poll_thread)


        print("NoIO pins: ", ", ".join(str(pin) for pin in unconfigured_pins))

        from pprint import pprint
        #print("{:<15}: {}".format("motor_left", type(self.motor_left).__name__))
        #print("{:<15}: {}".format("motor_right", type(self.motor_right).__name__))
        for name, pin in self.io.items():
            print("{:<15}: {}".format(name, type(pin).__name__))


        #location = os.path.dirname(os.path.realpath(__file__))
        #os.system('nice -n -20 ionice -n 0 python '+location+'/servos.py '+self.motor_right+' '+self.motor_left+' &')
        #sleep(1)

        if os.path.exists("/var/tmp/sumoServoPid.txt"):
            with open('/var/tmp/sumoServoPid.txt', 'r') as f:
                self.sumoServoPid = int(f.readline())
        
        if not os.path.exists('/proc/'+str(self.sumoServoPid)):
            raise IOError("proccess not found "+str(self.sumoServoPid))



    def __getattr__(self, name):
        if name in self.io_proxies:
            return self.io_proxies[name]
        elif name in self.io:
            return self.io[name]
        else:
            raise AttributeError("'{}' object has no I/O pin named '{}'".format(type(self).__name__, name))


    def forward(self):
        os.kill(self.sumoServoPid,30)

    def back(self):
        os.kill(self.sumoServoPid,10)

    def stop(self):
        os.kill(self.sumoServoPid,16)

    def right(self):
        os.kill(self.sumoServoPid,31)

    def left(self):
        os.kill(self.sumoServoPid,12)

    @property
    def sensor_power(self):
        return bool(self.io["sensor_power"].value)

    @sensor_power.setter
    def sensor_power(self, val):
        if val:
            self.io["sensor_power"].value = 1
        else:
            self.io["sensor_power"].value = 0

    @property
    def battery_gauge(self):
        if self.axp209:
            return self.axp209.battery_gauge
        else:
            return 0

    def isEnemy(self, value):
        if value == 'LEFT':
            return not self.enemy_left.value
        elif value == 'RIGHT':
            return not self.enemy_right.value
        elif value == 'FRONT':
            left = self.enemy_left.value
            right = self.enemy_right.value
            if right == 0 and left == 0:
                return True
            else:
                return False

    def isLine(self, value):
        if value == 'LEFT':
            return not self.line_left.value ^ self.lineColor
        elif value == 'RIGHT':
            return not self.line_right.value ^ self.lineColor
        elif value == 'FRONT':
            test = not self.line_front.value ^ self.lineColor
            #test = (not self.line_front.value) ^ self.lineColor
            #print("Ees joone j22rtus: "+str(test))
            return test



class SensorThread(Thread):
    def __init__(self, ws, sumorobot):
        Thread.__init__(self)
        self.daemon = True
        self.ws = ws
        self.sumorobot = sumorobot
        self.start()
    def run(self):
        while True:
            if self.ws and not self.ws.closed:
                self.ws.send(json.dumps(self.getData()))
                sleep(0.5)
            else:
                print("Websocket closed")
                break

    def getData(self):
        stats = {}
        s = self.sumorobot
        #for filename in os.listdir("/sys/power/axp_pmu/battery/"):
        #    with open ("/sys/power/axp_pmu/battery/" + filename) as fh:
        #        stats[filename] = int(fh.read())
        stats["capacity"] = s.battery_gauge

        right = not s.enemy_right.value
        left = not s.enemy_left.value
        line_right = not s.line_right.value ^ s.lineColor
        line_front = not s.line_front.value ^ s.lineColor
        line_left = not s.line_left.value ^ s.lineColor

#        s.blue_led.value = not left
#        s.green_led.value = not right

#        if line_front:
#            s.red_led.value = s.yellow_led.value = not line_front
#        else:
#            s.red_led.value = not line_left
#            s.yellow_led.value = not line_right
        if s.sensor_power== True:
            s.green_led.value = 1 if not line_right else 0
            s.yellow_led.value = 1 if not line_front else 0
            s.red_led.value = 1 if not line_front else 0
            s.blue_led.value = 1 if not line_left else 0
        else:
            s.green_led.value = 1
            s.yellow_led.value = 1
            s.red_led.value = 1
            s.blue_led.value = 1

        stats["enemy_right"] = 1 if right else 0
        stats["enemy_left"] = 1 if left else 0
        stats["line_left"] = 1 if line_left else 0
        stats["line_right"] = 1 if line_right else 0
        stats["line_front"] = 1 if line_front else 0
        return stats


def self_test(s):
    from time import sleep

    print("powering on the sensors")
    s.sensor_power = True

    t=0.1
    print("LED test", end="")
    for x in range(5):
        s.blue_led.value = False
        s.red_led.value = True
        s.yellow_led.value = True
        s.green_led.value = True
        sleep(t)
        s.blue_led.value = True
        s.red_led.value = False
        s.yellow_led.value = True
        s.green_led.value = True
        sleep(t)
        s.blue_led.value = True
        s.red_led.value = True
        s.yellow_led.value = False
        s.green_led.value = True
        sleep(t)
        s.blue_led.value = True
        s.red_led.value = True
        s.yellow_led.value = True
        s.green_led.value = False
        sleep(t)
        s.blue_led.value = True
        s.red_led.value = True
        s.yellow_led.value = False
        s.green_led.value = True
        sleep(t)
        s.blue_led.value = True
        s.red_led.value = False
        s.yellow_led.value = True
        s.green_led.value = True
        sleep(t)
        print(".", end="")
        sys.stdout.flush()
    print()


    print("motor_left test")
    for x in range(-100, 100, 2):
        s.motor_left.speed = x/100.0
        print(x, end="   \r")
        sys.stdout.flush()
        sleep(0.01)
    print()
    s.motor_left.speed = 0

    print("motor_right test")
    for x in range(-100, 100, 2 ):
        s.motor_right.speed = x/100.0
        print(x, end="   \r")
        sys.stdout.flush()
        sleep(0.01)
    print()
    s.motor_left.speed = 0


    print("sumorobot.forward()")
    s.forward()
    sleep(1)
    s.stop()

    print("sumorobot.back()")
    s.back()
    sleep(1)
    s.stop()

    print("Entering play mode")
    while True:
        right = not s.enemy_right.value
        left = not s.enemy_left.value
        line_right = not s.line_right.value
        line_front = not s.line_front.value
        line_left = not s.line_left.value

        s.blue_led.value = not left
        s.green_led.value = not right

        if line_front:
            s.red_led.value = s.yellow_led.value = not line_front
        else:
            s.red_led.value = not line_left
            s.yellow_led.value = not line_right



        if right and left:
            s.forward()
        elif left:
            s.left()
        elif right:
            s.right()
        else:
            s.stop()

        print(1 if right else 0,
              1 if left else 0,
              "  ",
              1 if line_right else 0,
              1 if line_front else 0,
              1 if line_left else 0,
              end="\r")
        sys.stdout.flush()

        sleep(0.01)

def lock():
    lock = pid.PidFile(pidname="sumochip")
    try:
        lock.create()
    except (pid.PidFileAlreadyRunningError, pid.PidFileAlreadyLockedError) as err:
        print("There is another instance of sumorobot software running")
        print("Please make sure that sumochip web interface is not running!")
        print("You can stop the web interface with this command:\n\n\t systemctl stop sumochip\n")
        exit(1)
    except pid.PidFileError as err:
        traceback.print_exc()
    return lock

def main():
    l = lock()
    try:
        s = Sumorobot()
        self_test(s)
    except KeyboardInterrupt:
        print("\nGraceful shutdown (Leds and sensors off)")
        l.close()
        s.sensor_power = False
        s.blue_led.value = 1
        s.red_led.value = 1
        s.yellow_led.value = 1
        s.green_led.value = 1

if __name__ == "__main__":
    main()
