#!/usr/bin/python3 -u
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
import traceback
import queue

dings = []

request_queue = queue.Queue()

try:
    pygame.mixer.init()
    dings = [pygame.mixer.Sound("ding1.wav"), pygame.mixer.Sound("ding2.wav")]
except:
    print("Failed to load sound")


zone = "ZONE" # "G" or "C"
endpoint = "ENDPOINT"

def playSound(event):
    try:
        dings[event].play()
    except:
        print("Failed to play sound")

def handleRead(device, val):
    hash = hashlib.sha224(f'{val}'.encode('utf-8')).hexdigest()
    isStudent = val.split(';')[-1].startswith('1')
    isExit = (device == 1)

    print("Incheck" if not isExit else "Uitcheck")

    writeData(hash, isExit, isStudent)

def writeData(hash, isExit, isStudent):
    global settings
    try:
        r = requests.post(endpoint, json={
            "Hash": hash,
            "IsExit": isExit,
            "IsStudent": isStudent,
            "Zone": zone
        })
        print(r)
        while not request_queue.empty():
            try:
                (hash, isExit, isStudent) = request_queue.get_nowait()
            except queue.Empty:
                break
            r = requests.post(endpoint, json={
                "Hash": hash,
                "IsExit": isExit,
                "IsStudent": isStudent,
                "Zone": zone
            })

            print(r)
    except:
        print("Error writing data to API, adding to queue and restarting network:")
        traceback.print_exc()
        request_queue.put((hash, isExit, isStudent))
        run_ifdown_ifup()

def run_ifdown_ifup():
    os.system('sudo ifdown wlan0')
    os.system('sudo ifup wlan0')

def readEvents(device):
    dev = InputDevice(f"/dev/input/event{device}")
    val = ""

    for event in dev.read_loop():
        if event.type == ecodes.EV_KEY:
            data = categorize(event)
            code = data.keycode.split('_')
            if data.keystate == 1:
                # Enter has been pressed; this means done reading pass.
                if val == "":
                    threading.Thread(target=playSound, args=(device,)).start()
                if code[1] == "ENTER":
                    threading.Thread(target=handleRead, args=(device, val)).start()
                    val = ""
                # When semicolon gets detected, it means a substring of the input
                # is done being parsed and the next substring can be parsed.
                elif code[1] == "SEMICOLON":
                    val += ";"
                # Finally, if the character is neither enter nor semicolon,
                # it is a regular input value character.
                elif len(code[1]) == 1:
                    val += code[1]


readerType1 = glob('/dev/input/by-id/*OMNIKEY*')
readerType2 = glob('/dev/input/by-id/*NEDAP*')
numReaders = len(readerType1 + readerType2)
threadList = []

for reader in range(numReaders):
    newThread = threading.Thread(target=readEvents, args=(reader,),daemon=True)
    newThread.start()
    threadList.append(newThread)

for thread in threadList:
    thread.join()
