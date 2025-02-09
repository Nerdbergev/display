#!/usr/bin/python3

import re
import time
import json

try:
    import requests
except:
    import urequests
    requests = urequests

zeile1 = b""
zeile2 = b""
lauftext = "Hallo Nerdberg"
lauftext = ""

try:
    #import serial
    #s = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
    s = open('fifo', 'wb')
except:
    import machine
    try:
        # ESP 32
        s = machine.UART(2, 9600)
    except:
        # RPi Pico W
        s = machine.UART(0, baudrate=9600) # , tx=Pin(0), rx=Pin(1))
    #s = machine.UART(0, 115200)

def parse_isodate(s):
    m = re.match(r"(\d\d\d\d)-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)\+(\d\d)", s)
    year = int(m.group(1))
    month = int(m.group(2))
    day = int(m.group(3))
    hour = int(m.group(4))
    minute = int(m.group(5))
    second = int(m.group(6))
    timezone = int(m.group(7))
    return int(time.mktime((year, month, day, hour-timezone, minute, second, 0, 0, 0)))

def minutes_until(t):
    # time.mktime expects localtime on cpython so handle the timezone delta
    timezone_delta = time.mktime(time.localtime()) - time.mktime(time.gmtime())
    seconds_until = t - int(time.time()-timezone_delta)
    return seconds_until // 60


def display(bts: bytes):
    s.write(bts)
    s.flush()


def char_repl(s):
    s = s.replace('ö', 'oe')
    s = s.replace('ä', 'ae')
    s = s.replace('ü', 'ue')
    s = s.replace('Ö', 'OE')
    s = s.replace('Ä', 'AE')
    s = s.replace('Ü', 'UE')
    s = s.replace('ß', 'ss')
    return s


def zeile2_scroll_msg(dt: str, interval=0.2):
    """
        dt: a string to scroll through zeile2
    """
    dt = " "*16 + dt + " "*17
    i = 0 # offset of the scrolling message
    while i < len(dt) - 16:
        t = dt[i:i+16]
        display(b"\x8A\x82" + t.encode())
        i += 1
        time.sleep(interval)

last_update = 0
def update_data():
    """
        if called 30s after last call:
            - perform ntp sync
            - query vag API
            - set zeile1 to preformatted bytestring
            - set zeile2 to bytestring without escape codes (string is capped to 16 bytes in display loop)
            - set lauftext to string or list of strings or None
    """
    global last_update
    global zeile1
    global zeile2
    global lauftext
    if not last_update or (last_update + 30 < int(time.time())):
        print("update_data:")
        # ntp sync on micropython
        try:
            import ntptime
            ntptime.settime()
        except:
            pass

        last_update = int(time.time())

        #j = json.load(open('json/js.json'))
        #j = json.load(open('json/night.json'))

        # Jakobinenstraße
        js = requests.get("https://start.vag.de/dm/api/abfahrten.json/vgn/2171/", timeout=10).text
        # Schoppershof
        #j = requests.get("https://start.vag.de/dm/api/abfahrten.json/vgn/341/").json()
        try:
            j = json.loads(js)
        except:
            zeile1 = "Invalid JSON".encode()
            zeile2 = b""
            lauftext = js
            return

        #del js

        if 'Sonderinformationen' in j and j['Sonderinformationen']:
            lauftext = j['Sonderinformationen']
        else:
            lauftext = None

        abfahrten = j.get("Abfahrten", [])
        wichtige_abfahrten = [a for a in abfahrten if
            a["Linienname"].startswith('U') or
            a["Linienname"].startswith('EU') or
            a["Linienname"].startswith('N')]

        # bei nightlinern ist die richtung invertiert
        wichtige_abfahrten = [a for a in wichtige_abfahrten if
            (a["Richtung"] == "Richtung1" and not a["Linienname"].startswith('N')) or
            (a["Richtung"] == "Richtung2" and a["Linienname"].startswith('N'))]

        if wichtige_abfahrten:
            # nur abfahrten der gleichen linie anzeigen
            wichtige_abfahrten = [a for a in wichtige_abfahrten if
                a["Linienname"] == wichtige_abfahrten[0]["Linienname"]]
        else:
            # jetzt ist es auch schon egal
            naechste_abfahrt = abfahrten[0] if len(abfahrten) > 0 else None
            wichtige_abfahrten = [naechste_abfahrt]

        if wichtige_abfahrten:
            max_abfahrten = 2 if lauftext else 3
            num_abfahrten = min(len(wichtige_abfahrten), max_abfahrten)

            abfahrtszeiten = []
            for i in range(0, num_abfahrten):
                a = wichtige_abfahrten[i]
                az = parse_isodate(a['AbfahrtszeitIst'])
                #az = datetime.fromisoformat(a['AbfahrtszeitIst'])
                #az = az.replace(tzinfo=None)
                abfahrt_in_min = minutes_until(az)
                #abfahrt_in_min = (az - datetime.now()).seconds // 60
                abfahrtszeiten.append("%i'" % abfahrt_in_min)
            if len(' '.join(abfahrtszeiten)) > (16 - 4):
                del abfahrtszeiten[-1]
            if lauftext and len(' '.join(abfahrtszeiten)) > (16 - 9):
                del abfahrtszeiten[-1]
            str_abfahrtszeiten = ' '.join(abfahrtszeiten)
            a = wichtige_abfahrten[0]

            space_left_in_line1 = 16 - 1 - int(bool(lauftext)) - \
                len(str_abfahrtszeiten) - len(a['Linienname'])

            zeile1 = b"\x81" + a['Linienname'].encode() + b"\x87 "
            if lauftext:
                ziel = char_repl(a['Richtungstext'])[:space_left_in_line1]
                zeile1 += ziel.encode() + b" "
                zeile1 += b" " * (space_left_in_line1 - len(ziel))
            else:
                zeile1 += b" " * space_left_in_line1
                zeile2 = char_repl(a['Richtungstext']).encode()
            zeile1 += str_abfahrtszeiten.encode()
        else:
            zeile1 = "Keine Abfahrten".encode()
            zeile2 = b""
        print("  zeile1="+repr(zeile1))
        print("  zeile2="+repr(zeile2))
        print("  lauftext="+repr(lauftext))


display_loop = None
def setup():
    global display_loop
    global main_loop

    # initialize display
    s.write(b"\x8e")
    s.write(b"\x87")


def mainloop():
    global zeile1
    global zeile2
    global lauftext
    msg_index = 0
    last_text = None
    while True:
        update_data()

        # zeile 1
        display(b"\x89\x87" + zeile1)

        # zeile 2
        if lauftext:
            my_text = lauftext # working copy of lauftext in case it gets overwritten during http update
            dt = my_text       # dt is the actual currently displayed msg string (and not a list as ensured below)
            if isinstance(my_text, list):
                if last_text == my_text:
                    # if lauftext is list of msgs get next msg from list
                    msg_index += 1
                    msg_index %= len(my_text)
                else:
                    # unless we meanwhile got a different list - then let's start from the first element
                    msg_index = 0
                dt = my_text[msg_index]
            last_text = my_text
            zeile2_scroll_msg(char_repl(dt))
        else:
            # no lauftext
            display(b"\x8A\x87" + zeile2[:16] + b" "*(16-len(zeile2)))
            time.sleep(1)
