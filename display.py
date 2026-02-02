#!/usr/bin/python3

import sys
import re
import time
import json

ESCAPE_COLOR_RED = b"\x80"
ESCAPE_COLOR_LIGHT_RED = b"\x81"
ESCAPE_COLOR_YELLOW = b"\x82"
ESCAPE_COLOR_GREEN = b"\x87"
ESCAPE_CURSOR_ROW1 = b"\x89"
ESCAPE_CURSOR_ROW2 = b"\x8A"
ESCAPE_RESET = b"\x8E"

try:
    import requests
except:
    import urequests
    requests = urequests

zeilen = []
lauftext = ""

if sys.platform == 'linux':
    #import serial
    #s = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
    s = open('fifo', 'wb')
    #s = open('/dev/null', 'wb')
else:
    import machine
    if sys.platform == 'esp32':
        # ESP 32
        print("UART2 - ESP32")
        s = machine.UART(2, 9600)
    else:
        # RPi Pico W
        print("UART0 - RPI Pico W")
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

def tsdiff_minutes(ts1, ts2):
    return (ts1 - ts2) // 60

sim_buffer = [' ']*32
last_sim_buffer = None
sim_cursor = 0
def sim_display(bts: bytes):
    """
        this function emulates the actual display and prints the current expected output
        of the physical display to the repl console
    """
    global sim_buffer
    global last_sim_buffer
    global sim_cursor

    # update cursor and buffer
    for c in bts:
        if c >= 0x20 and c <= 0x7E:
            sim_buffer[sim_cursor] = chr(c)
            sim_cursor += 1
            sim_cursor = min(31, sim_cursor)
        elif c >= 1 and c <= 32:
            sim_cursor = c - 1
        elif c == 0x89:
            sim_cursor = 0
        elif c == 0x8A:
            sim_cursor = 16
        elif c == 0x8E:
            sim_buffer = [' ']*32
            sim_cursor = 0

    if last_sim_buffer != sim_buffer:
        # render and print buffer contents

        # full display box
        """
        print("+"+"-"*16+"+")
        print("|"+''.join(sim_buffer[0:16])+"|")
        print("|"+''.join(sim_buffer[16:32])+"|")
        print("+"+"-"*16+"+")
        """

        # slim display box
        print("DISPLAY: |"+''.join(sim_buffer[0:16])+"|"+''.join(sim_buffer[16:32])+"|")

        last_sim_buffer = sim_buffer.copy()

def display(bts: bytes):
    s.write(bts)
    try:
        s.flush()
    except:
        # flush() doesn't work when writing to /dev/null or fifo using micropython
        pass
    sim_display(bts)


def display_manual(l1="", l2=""):
    """
    """
    display(b"\x8e\x89\x87"+char_repl(l1).encode()+b"\x8a"+char_repl(l2).encode())


def char_repl(s: str) -> str:
    s = s.replace('ö', 'oe')
    s = s.replace('ä', 'ae')
    s = s.replace('ü', 'ue')
    s = s.replace('Ö', 'OE')
    s = s.replace('Ä', 'AE')
    s = s.replace('Ü', 'UE')
    s = s.replace('ß', 'ss')

    # cleanup escape codes
    for i in range(0x01, 0x1f+1):
        s = s.replace(chr(i), '')
    for i in range(0x80, 0x8f+1):
        s = s.replace(chr(i), '')

    return s


def zeile2_scroll_lauftext(zeilen: list, lauftext: str, interval=0.2):
    """
        zeilen: list of preformatted bytestrings to cycle through (lenght: 0-2)
        lauftext: a string to scroll through zeile2
    """
    lauftext = " "*16 + lauftext + " "*17
    i = 0 # offset of the scrolling message
    while i < len(lauftext) - 16:
        if len(zeilen) == 0:
            z1 = b""
        else:
            z1 = zeilen[min(int(time.time() % 10 > 5), len(zeilen)-1)]
        display(b"\x89\x87" + z1 + b"\x8A\x82" + lauftext[i:i+16].encode())
        i += 1
        time.sleep(interval)

last_update = 0
def update_data():
    """
        if called 30s after last call:
            - query vag API
            - set zeile1 to preformatted bytestring
            - set zeile2 to preformatted bytestring
            - set lauftext to string or list of strings or None
    """
    global last_update
    global zeilen
    global lauftext
    if last_update and (last_update + 30 > int(time.time())):
        return
    print("update_data:")
    last_update = int(time.time())

    # Jakobinenstraße
    #url = "https://start.vag.de/dm/api/abfahrten.json/vgn/2171/"

    # Schoppershof
    #url = "https://start.vag.de/dm/api/abfahrten.json/vgn/341/"

    # Plaerrer
    # https://start.vag.de/dm/api/v1/abfahrten.json/vgn/704?timedelay=0&product=Ubahn,Bus

    # Obere Turmstrasse
    url = "https://start.vag.de/dm/api/abfahrten.json/vgn/730?timedelay=6"

    # HTTP request
    try:
        res = requests.get(url, timeout=10)
        assert res.status_code == 200, "HTTP Status Code: " + str(res.status_code) + ": " + res.reason
    except Exception as e:
        zeilen = ["HTTP req fail   ".encode()]
        lauftext = str(e)
        print(url)
        print(e)
        return

    # JSON decode
    try:
        j = json.loads(res.text)
    except:
        zeilen = ["API ret bad JSON".encode()]
        lauftext = res.text[:100]
        print("API returned bad json:\n" + res.text)
        return

    # Inject json response for testing
    #j = json.load(open('nj/ot.json'))
    #j = json.load(open('nj/ot_none.json'))

    if 'Sonderinformationen' in j and j['Sonderinformationen']:
        lauftext = j['Sonderinformationen']
        # Nicht hilfreiche Lauftexte
        lauftext = [l for l in lauftext if not l.startswith("Umgestaltung des Obstmarkts")]
        lauftext = [l for l in lauftext if not l.startswith("Bauarbeiten Maxfeld")]
        lauftext = [l for l in lauftext if not l.startswith("Bitte achten Sie auf die Bahnsteig")]
    else:
        lauftext = None

    now = parse_isodate(j['Metadata']['Timestamp'])
    abfahrten = j.get("Abfahrten", [])

    abfahrten_noerdlich = [a for a in abfahrten if a['Richtung'] == 'Richtung1']
    abfahrten_suedlich  = [a for a in abfahrten if a['Richtung'] == 'Richtung2']

    zeilen = [
        format_zeile(abfahrten_noerdlich, now, bound='N', empty=ESCAPE_COLOR_LIGHT_RED + b'N ' + ESCAPE_COLOR_GREEN + b'Keine Fahrten'),
        format_zeile(abfahrten_suedlich, now, bound='S', empty=ESCAPE_COLOR_LIGHT_RED + b'S ' + ESCAPE_COLOR_GREEN + b'Keine Fahrten')
    ]
    if lauftext:
        # don't alternate between a useful and no useful info
        if b'Keine Fahrten' in zeilen[0] and not b'Keine Fahrten' in zeilen[1]:
            del zeilen[0]
        elif b'Keine Fahrten' in zeilen[1] and not b'Keine Fahrten' in zeilen[0]:
            del zeilen[1]
    print("  zeilen = "+repr(zeilen))
    print("  lauftext = "+repr(lauftext))

def format_abfahrt(abfahrt, now, color=False) -> bytes:
    linie = abfahrt['Linienname']
    linie = re.findall(r'(\d+)', linie)[0] # strip text - e.g. E4->4 for tram replacement bus
    az = parse_isodate(abfahrt['AbfahrtszeitIst'])
    abfahrt_in_min = tsdiff_minutes(az, now)
    colors_map = {
        '4': (ESCAPE_COLOR_GREEN, ESCAPE_COLOR_GREEN),
        '6': (ESCAPE_COLOR_GREEN, ESCAPE_COLOR_YELLOW),
        '10': (ESCAPE_COLOR_YELLOW, ESCAPE_COLOR_GREEN),
        '36': (ESCAPE_COLOR_YELLOW, ESCAPE_COLOR_YELLOW),
    }
    color1, color2 = (b'', b'')
    if color:
        color1, color2 = colors_map.get(linie, (ESCAPE_COLOR_GREEN, ESCAPE_COLOR_GREEN))
    return color1 + str(abfahrt_in_min).encode() + color2 + b"'"

def format_zeile(abfahrten, now, empty=b"Keine Abfahrten", bound='') -> bytes:
    """
        abfahrten: list from VAG API
        now: current timestamp
        empty: text to display if abfahrten is empty
        bound: common destination indicator (e.g. N or S) used if multiple lines are present
    """
    if not (abfahrten and abfahrten[0]):
        return empty
    linie1_name = abfahrten[0]['Linienname']
    linie1_dest = abfahrten[0]['Richtungstext']
    linie1_prod = abfahrten[0]['Produkt']
    single_linie = not bool([a for a in abfahrten if a['Linienname'] != linie1_name or a['Richtungstext'] != linie1_dest])
    linie = ""
    print(f"{single_linie=}")
    if single_linie:
        max_abfahrten = 2
        linie = 'T' if linie1_prod == 'Tram' else ''
        linie += linie1_name
        # line + space + at least one char of dest + space
        space_for_departures = 16 - len(linie) - 3
    else:
        max_abfahrten = 99
        linie = bound
        # line + space
        space_for_departures = 16 - len(linie) - 1

    num_abfahrten = min(len(abfahrten), max_abfahrten)

    abfahrten = abfahrten[:num_abfahrten]
    while len(b' '.join([format_abfahrt(a, now) for a in abfahrten])) > space_for_departures:
        del abfahrten[-1]
    str_abfahrtszeiten = b' '.join([format_abfahrt(a, now, color=not single_linie) for a in abfahrten])
    str_abfahrtszeiten_len = len(b' '.join([format_abfahrt(a, now) for a in abfahrten]))

    zeile = ESCAPE_COLOR_LIGHT_RED + linie.encode() + ESCAPE_COLOR_GREEN + b" "

    if single_linie:
        space_left_for_dest = 16 - len(linie) - 2 - str_abfahrtszeiten_len
        ziel = char_repl(linie1_dest)
        ziel = ziel.replace("Hauptbahnhof", "Nue Hbf")
        if ziel.startswith("Fue-"):
            ziel = ziel.replace("Fue-", "F.")
        ziel = ziel.replace("Fuerth ", "F.")
        ziel = ziel.replace("Nuernberg ", "N.")
        ziel = ziel.replace("Langwasser ", "L.")
        ziel = ziel.replace("Hauptbahnhof", "Hbf")
        ziel = ziel.replace("N.Hbf", "Nue Hbf")
        ziel = ziel[:space_left_for_dest]
        zeile += ziel.encode() + b" "
        zeile += b" " * (space_left_for_dest - len(ziel))
    else:
        space_left_for_dest = 16 - len(linie) - 1 - str_abfahrtszeiten_len
        zeile += b" " * space_left_for_dest
    zeile += str_abfahrtszeiten
    return zeile

def setup():
    # initialize display
    display(ESCAPE_RESET + ESCAPE_COLOR_GREEN)


def mainloop():
    global zeilen
    global lauftext
    msg_index = 0
    last_text = None
    while True:
        update_data()

        # zeile 1: done via zeile2_scroll_lauftext or in else block

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
            zeile2_scroll_lauftext(zeilen, char_repl(dt))
        else:
            # no lauftext
            display(ESCAPE_CURSOR_ROW1 + zeilen[0] + ESCAPE_CURSOR_ROW2 + zeilen[1])
            time.sleep(10.2)

if __name__ == '__main__':
    setup()
    mainloop()
