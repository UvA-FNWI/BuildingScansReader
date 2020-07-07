from evdev import InputDevice, categorize, ecodes
import threading
import requests
import hashlib
import random
import os
import jsonpickle
import pygame
import sys
from datetime import datetime
from glob import glob

pygame.mixer.init()
dings = [pygame.mixer.Sound("ding1.wav"), pygame.mixer.Sound("ding2.wav")]

endpoint = ""


class Settings:
    def __init__(self):
        self.currentDate = datetime.today().date()
        self.salt = random.randint(0, 2**32)
        self.logfolder = f"./logs/{datetime.today().strftime('%Y%m%d')}/"
        if not os.path.exists(self.logfolder):
            os.mkdir(self.logfolder)
        self.employees = set()
        self.students = set()
        self.totalEmployees = set()
        self.totalStudents = set()
        print(f"Created settings: {self.logfolder}")

try:
    lastFolder = sorted(glob('./logs/*/'))[-1]
    lastFile = sorted(os.listdir(lastFolder))[-1]
    with open(f"{lastFolder}{lastFile}", 'r') as f:
        settings = jsonpickle.decode(f.read())
    print(f"Loaded settings ({len(settings.totalStudents)} students, {len(settings.totalEmployees)} employees, {settings.logfolder})")
    if settings.currentDate != datetime.today().date():
        settings = Settings()
except:
    print(f"Failed to load settings from disk: {sys.exc_info()[0]}")
    settings = Settings()

def playSound(event):
    dings[event].play()

def handleRead(event, val):
    global settings
    if settings.currentDate != datetime.today().date():
        settings = Settings()
    h = hashlib.sha224(f'{settings.salt}{val}'.encode('utf-8')).hexdigest()
    isStudent = val.split(';')[-1].startswith('1') 
    target = settings.students if isStudent else settings.employees
    if event == 1:
        target.add(h)
    elif h in target:
        target.remove(h) 
    totalTarget = settings.totalStudents if isStudent else settings.totalEmployees
    totalTarget.add(h)
    writeData()

def writeData():
    global settings
    try:
        r = requests.post(endpoint, json={
            "Date": str(datetime.now()),
            "Students": len(settings.students),
            "Employees": len(settings.employees),
            "TotalStudents": len(settings.totalStudents),
            "TotalEmployees": len(settings.totalEmployees)
        })
        print(r)
    except:
        print("Error writing data to API")
    try:
        with open(f"{settings.logfolder}{datetime.now().strftime('%H%M%S%f.json')}", "w") as f:
            f.write(jsonpickle.encode(settings))
    except:
        print(f"Error writing data to disk: {sys.exc_info()[0]}")

def readEvents(device):
    dev = InputDevice(f'/dev/input/event{device}')
    val = ""
    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY:
            data = categorize(event)
            code = data.keycode.split('_')
            if data.keystate == 1:
                if val == "":
                    threading.Thread(target=playSound, args=(device,)).start()
                if code[1] == "ENTER":
                    print(f'{device}: {val}')
                    threading.Thread(target=handleRead, args=(device, val)).start()                   
                    val = ""
                elif code[1] == "SEMICOLON":
                    val += ";"
                elif len(code[1]) == 1:
                    val += code[1]

writeData()
e1 = threading.Thread(target=readEvents, args=(0,),daemon=True)
e2 = threading.Thread(target=readEvents, args=(1,),daemon=True)
e1.start()
e2.start()

e1.join()
e2.join()
