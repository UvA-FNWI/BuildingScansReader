#!/usr/bin/python3 -u
from evdev import InputDevice, categorize, ecodes
from typing import List, Deque, Tuple
import threading
import requests
import hashlib
import random
import os
import pygame
import sys
import enum
import json
from datetime import datetime
from glob import glob
import traceback
from collections import deque

dings: List[pygame.mixer.Sound] = []

# use a deque for the request queue, along with a condition variable.
# deque pop/append are thread-safe/atomic, but there's no blocking support,
# so we need a separate condition variable for that.
request_queue: Deque[Tuple[str, bool, bool]] = deque()
request_delta_cond = threading.Condition()

ReaderType = enum.Enum('ReaderType', ['INCHECK', 'UITCHECK'])

try:
    pygame.mixer.init()
    dings = [pygame.mixer.Sound("ding1.wav"), pygame.mixer.Sound("ding2.wav")]
except:
    print("Failed to load sound")

with open('config.json', 'r') as f:
    config = json.load(f)

zone = config['zone']
endpoint = config['endpoint']

def playSound(type: ReaderType):
    try:
        dings[0 if type == ReaderType.UITCHECK else 1].play()
    except:
        print("Failed to play sound")


def handleRead(type: ReaderType, val: str):
    hash = hashlib.sha224(f'{val}'.encode('utf-8')).hexdigest()
    isStudent = val.split(';')[-1].startswith('1')
    isExit = (type == ReaderType.UITCHECK)

    print("Incheck" if not isExit else "Uitcheck")

    with request_delta_cond:
        request_queue.append((hash, isExit, isStudent))
        request_delta_cond.notify()


def request_queue_process():
    while True:
        with request_delta_cond:
            # wait until the request queue is non-empty
            request_delta_cond.wait_for(lambda: request_queue)
            # get a request
            request = request_queue.popleft()
        # process it
        request_process(request)


def request_process(request: Tuple[str, bool, bool]):
    (hash, isExit, isStudent) = request
    print("Processing request in rq thread.")
    try:
        r = requests.post(endpoint, json={
            "Hash": hash,
            "IsExit": isExit,
            "IsStudent": isStudent,
            "Zone": zone
        })
        print("Done.")
    except requests.ConnectionError as e:
        print(f"Error writing data to API, re-adding current request to queue and restarting network: {e}")
        with request_delta_cond:
            # put 'er back.
            request_queue.appendleft((hash, isExit, isStudent))
        run_ifdown_ifup()


def run_ifdown_ifup():
    os.system('sudo ifdown wlan0')
    os.system("timeout 30 bash -c 'while [[ -n `pgrep wpa_supplicant` ]]; do sleep 0.5; done'")
    os.system("sudo ifup wlan0")
    os.system('/lib/ifupdown/wait-online.sh')


def readEvents(device: str, type: ReaderType):
    dev = InputDevice(f"/dev/input/by-id/{device}")
    val = ""

    try:
        for event in dev.read_loop():
            if event.type == ecodes.EV_KEY:
                data = categorize(event)
                code = data.keycode.split('_')
                if data.keystate == 1:
                    # Enter has been pressed; this means done reading pass.
                    if val == "":
                        threading.Thread(target=playSound, args=(type,), daemon=True).start()
                    if code[1] == "ENTER":
                        handleRead(type, val)
                        val = ""
                    # When semicolon gets detected, it means a substring of the input
                    # is done being parsed and the next substring can be parsed.
                    elif code[1] == "SEMICOLON":
                        val += ";"
                    # Finally, if the character is neither enter nor semicolon,
                    # it is a regular input value character.
                    elif len(code[1]) == 1:
                        val += code[1]
    except OSError as e:
        print(f"Scanners probably disconnected, exiting... (OSError: {e})")
        sys.exit()

threadList = []

request_queue_thread = threading.Thread(target=request_queue_process, daemon=True)
request_queue_thread.start()

def startReader(name: str, type: ReaderType):
    newThread = threading.Thread(target=readEvents, args=(name, type),daemon=True)
    newThread.start()
    threadList.append(newThread)

for reader in config["incheck_readers"]:
    startReader(reader, ReaderType.INCHECK)

for reader in config["uitcheck_readers"]:
    startReader(reader, ReaderType.UITCHECK)

for thread in threadList:
    thread.join()
