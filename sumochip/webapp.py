from __future__ import print_function
from flask import Flask, render_template
from sumorobot import Sumorobot, SensorThread, lock
from flask_sockets import Sockets
from threading import Thread
from time import sleep
import imp
import json
import os
import ast

codeTemplate = """
from threading import Thread
from time import sleep
class AutonomousThread(Thread):
    def __init__(self, sumorobot):
        Thread.__init__(self)
        self.sumorobot = sumorobot

    def run(self):
        self.running = True
        print("Starting AutonomousThread")
        while self.running:
            self.step()
            sleep(0.01)
        print("AutonomousThread was stopped")
        self.sumorobot.stop()
    def step(self):
        sumorobot = self.sumorobot
        isEnemy = sumorobot.isEnemy
        isLine = sumorobot.isLine
"""


sumorobot = Sumorobot()
codeThread = None
codeText = ""
codeBytecode = None
codeSaved = False

app = Flask(__name__)
try:
    with open("/etc/machine-id", "r") as fh:
        app.config['SECRET_KEY'] = fh.read()
except:
    app.config['SECRET_KEY'] = 'secret!'
sockets = Sockets(app)

@app.route('/')
def index():
    print("HTTP request")
    return render_template('index.html')

@sockets.route('/')
def command(ws):
    global codeThread
    global codeText
    global codeBytecode
    while not ws.closed:
        command = ws.receive()
        if command:
            print('Command: ' + command)
        if command == '0':
            print("Stop")
            sumorobot.stop()
        elif command == '1':
            print("Forward")
            sumorobot.forward()
        elif command == '2':
            print("Back")
            sumorobot.back()
        elif command == '3':
            print("Right")
            sumorobot.right()
        elif command == '4':
            print("Left")
            sumorobot.left()
        elif command == 'sensors':
            print("keegi kysib sensoreid")
            sensors = SensorThread(ws, sumorobot)
        elif command == 'getSavedCode':
            with open("code.txt", "r") as fh:
                code = fh.read()
                print(code)
                ws.send(json.dumps({'savedCode':code}))
                codeText = code
                fullCodeText = codeTemplate + "".join((" "*8 + line + "\n" for line in codeText.split("\n")))
                print(fullCodeText)
                codeBytecode = compile(codeText, "<SumorobotCode>", "exec")
        elif command == 'executeCode':
            if codeSaved:
                if codeThread:
                    codeThread.running = False
                slave = {}
                exec(codeBytecode, slave)
                codeThread = slave["AutonomousThread"](sumorobot)
                codeThread.daemon = True
                codeThread.start()
                sumorobot.sensor_power = True
            else:
                ws.send(json.dumps({'Error':'Koodi ei ole salvestatud'}))
        elif command == 'stopCode':
            if codeThread:
                codeThread.running = False
            print("code execution stopped")
            sumorobot.sensor_power = False
        elif command == 'shutDown':
            if codeThread:
                codeThread.running = False
            print("code execution stopped")
            sumorobot.sensor_power = False
            os.system("poweroff")
            print("Robot suletakse")
        elif command == None:
            print("WTF")
        else:
            print("Code to be saved:")
            print(command)
            with open("code.txt", "w") as fh:
                fh.write(str(command))
            codeText = str(command)
            print("Kood scratch:" +codeText)

            if len(codeText) > 0:
                fullCodeText = codeTemplate + "".join((" "*8 + line + "\n" for line in codeText.split("\n")))
                print("Kood "+fullCodeText)
                print("Koodi pikkus: "+str(len(fullCodeText)))
                try:
                    print("####RUNNING#####")
                
                    codeBytecode = compile(fullCodeText, "<SumorobotCode>", "exec")
                    test = compile(fullCodeText, "<SumorobotCode>", "exec", ast.PyCF_ONLY_AST)
                    print('Saved')
                    codeSaved = True
                except TypeError:
                    print("######ERRRROR########")
            else:
                codeSaved = False
                ws.send(json.dumps({'Error':'Do not send empty stuff'}))



def main():
    lock()
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    ip, port = ('0.0.0.0', 5001)
    if os.getuid() == 0:
        port = 80
    server = pywsgi.WSGIServer((ip, port), app, handler_class=WebSocketHandler)
    print("Starting server at http://{}:{}".format(ip, port))
    server.serve_forever()

if __name__ == '__main__':
    main()
