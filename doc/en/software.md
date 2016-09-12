
##Software

The underlying software for the sumorobot is written in Python using web framework Flask.
The underlying source code can be attained from GitHub at https://github.com/laurivosandi/sumochip and corrections and additions are welcome.


###Software installation

Sumorobot is programmable through the web, but in order to do that we will need to install a web application on the robot. 
Since CHIP does not have video outputs, connecting an HDMI screen is problematic.
Instead we use USB cable to attach to the serial port on the robot.
The following steps will guide you through this.
This is necessary to be done only once, afterwards you can use the network.
For Windows additional driver installation is needed to be able to use the USB cable.
Mac OS X or Linux do not have these problems.

![Serial](../img/kit/62-connecting-via-usb.jpg)

###Installing drivers

For Ubuntu and Mac OS X driver installation is not needed, for Windows driver installation is necessary. Open Device Manager:

![Device manager](../img/usbser/01.png)

Find CDC Composite Gadget marked with a yellow triangle and right click on it and select *Update Driver Software...*:

![Device manager](../img/usbser/02.png)

Click on *Browse my computer for driver software*:

![Device manager](../img/usbser/03.png)

Select *Let me pick from a list of device drivers on my computer*:

![Device manager](../img/usbser/04.png)

Select *Show All Devices* and click on *Next*:

![Device manager](../img/usbser/05.png)

Scroll down on the list on the left and choose *Microsoft*. After scroll down in the righthand list and select *USB Serial Device*:

![Device manager](../img/usbser/06.png)

On the pop-up warning window click *Yes*:

![Device manager](../img/usbser/07.png)

Drivers should now be installed:

![Device manager](../img/usbser/08.png)

A new *USB Serial Device* should appear to device list. Remember or note the serial number as it will be needed later. On this particular screenshot it is COM6:

![Device manager](../img/usbser/09.png)


###Opening serial connection

For connecting to your robot via serial connection Windows users can use [PuTTY](http://www.chiark.greenend.org.uk/~sgtatham/putty/download.html).
Ubuntu and other UNIX operating systems can use programs like `screen`, `picocom` or your own preference.
Serial connection allows access to command line inside CHIP and many other smart devices. CHIP uses Debian as its operating system and many commands are the same as Ubuntu.

###Opening serial connection in Ubuntu

With picocom use the command:
Ctrl-A, Ctrl-X to exit picocom

```bash
picocom -b 115200 /dev/ttyACM0
```

If that fails try to find the correct serial port name with following command:

```bash
dmesg | grep tty
```

###Opening serial connection in Windows

Run PuTTY:
Choose *Connection type*:
*Serial*:
*Serial line* same serial number as previously noted.
*Speed* 115200


###Logging into the robot

Username is *root* and password *chip*.

###Setting up the network

First we need to connect CHIP to Internet using WiFi. For that we use NetworkManager pseudografical interface:

```bash
nmtui
```
To verify Internet connection use the `ping` command. Press Ctrl-C to abort:

```bash
ping neti.ee
```

Due do CHIP not having a real time clock that keeps track of time,
the CHIP will try to request the time from the Internet, but sometimes this may fail.
To verify the clock is correct you can use the following command, safe connections to Internet(e.g. GitHub) will fail if the clock is wrong.

```bash
date
```

To change the network name of the robot change the hostname in /etc/hostname and /etc/hosts:

  echo robot_name > /etc/hostname


###Updating the operating system

If the connection is present we can do a software update to CHIP's OS:

```bash
apt update       # Refresh the packet list
apt full-upgrade   # Update the packages
```


### Installing dependencies

Install Git version control software:

```bash
apt install python-pip python-dev git
```

###Installing the sumorobot software

After those steps we are ready to install the sumorobot software:

```bash
pip install sumochip
```

If all has gone according to plan so far then we can find out what is the CHIP's IP address. For this we can use the command:

```bash
ifconfig
```

###Setting up the software for sumorobot

Get the configuration file, that has the information about which legs the servomotors and sensors are connected to:

```bash
mkdir -p /etc/sumorobot/
curl https://raw.githubusercontent.com/artizirk/sumochip/master/sumochip/config/sumochip_v1.1.ini > /etc/sumorobot/sumorobot.ini
```

Run test program, to abort press Ctrl-C:

```bash
sumochip_test
```

Check that the line sensors LEDs work. For this look into the line sensors with your mobile phone camera. Infrared will appear as violet in the camera:
![Checking line sensors](../img/kit/63-checking-line-sensors.jpg)

Perform the same check on the sensors for detecting enemies:

![Checking enemy sensors](../img/kit/64-checking-enemy-sensors.jpg)

To test the web application:

```bash
sumochip_web
```

If you wish to run the robot off battery power use the command:

```bash
systemctl start sumochip
```

To enable the sumochip use the command:
```bash
systemctl enable sumochip
```

To make sure the battery is connected to the CHIP run:

```bash
axp209
```

If you need to shut down the robot then use the command:

```bash
shutdown -h now
```


##Using the terminal

###Most frequently used commands

Commands used on CHIP also work the same on Raspberry Pi and Ubuntu:

* Current directory: `pwd`
* Displaying files and directories in the current directory: `ls -lah`
* Enter directory: `cd directoryname`
* Move up a directory: `cd ..`
* Delete a file: `rm filename`

###Editing files in the terminal

As many other Linux systems CHIP has a text editor called `nano`, to open a file with this program:

```bash
nano path/filename.py
```
Use the keyboard shortcut Ctrl-K to cut the text and Ctrl-U to paste the text. Ctrl-X allows you to save and exit the program.

For a more convenient text editing experience you can use Midnight Commander. To install try:
```Bash
apt install mc
```

:
Opening files is the same:

```bash
mcedit path/filename.py
```

Navigating the menus is similar to graphical applications, Alt-F opens the main menu. Most important shortcuts are F5 to copy, F6 to cut and F10 to exit the program.

![mcedit](../img/mcedit.png)


[Back to main page](index.md "Main page")
