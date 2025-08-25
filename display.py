#!/usr/bin/python3

import sys
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
zeile1_alt = b""
zeile2_alt = b""
lauftext = "Hallo Nerdberg"
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

def minutes_until(t):
    # time.mktime expects localtime on cpython so handle the timezone delta
    timezone_delta = time.mktime(time.localtime()) - time.mktime(time.gmtime())
    seconds_until = t - int(time.time()-timezone_delta)
    return seconds_until // 60

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


def zeile2_scroll_msg(zeile1, zeile1_alt, dt: str, interval=0.2):
    """
        dt: a string to scroll through zeile2
    """
    dt = " "*16 + dt + " "*17
    i = 0 # offset of the scrolling message
    while i < len(dt) - 16:
        z1 = zeile1 if time.time() % 10 > 5 else zeile1_alt
        t = dt[i:i+16]
        display(b"\x89\x87" + z1 + b"\x8A\x82" + t.encode())
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
    global zeile1_alt
    global zeile2_alt
    global lauftext
    if not last_update or (last_update + 30 < int(time.time())):
        print("update_data:")
        # ntp sync on micropython
        if sys.implementation.name == 'micropython' and sys.platform != 'linux':
            import ntptime
            try:
                ntptime.settime()
            except:
                print("NTP failed")

        last_update = int(time.time())

        # Jakobinenstraße
        url = "https://start.vag.de/dm/api/abfahrten.json/vgn/2171/"

        # Schoppershof
        #url = "https://start.vag.de/dm/api/abfahrten.json/vgn/341/"

        # HTTP request
        try:
            res = requests.get(url, timeout=10)
            assert res.status_code == 200, "HTTP Status Code: " + str(res.status_code) + ": " + res.reason
        except Exception as e:
            zeile1 = "HTTP req fail   ".encode()
            zeile2 = b""
            zeile1_alt = b""
            zeile2_alt = b""
            lauftext = str(e)
            print(url)
            print(e)
            return

        # JSON decode
        try:
            j = json.loads(res.text)
        except:
            zeile1 = "API ret bad JSON".encode()
            zeile2 = b""
            zeile1_alt = b""
            zeile2_alt = b""
            lauftext = res.text[:100]
            print("API returned bad json:\n" + res.text)
            return

        # Inject json response for testing
        #j = json.load(open('json_files/sonderinfo.json'))

        if 'Sonderinformationen' in j and j['Sonderinformationen']:
            lauftext = j['Sonderinformationen']
            lauftext = [l for l in lauftext if not l.startswith("Umgestaltung des Obstmarkts")]
            lauftext = [l for l in lauftext if not l.startswith("Bauarbeiten Maxfeld")]
        else:
            lauftext = None

        abfahrten = j.get("Abfahrten", [])
        wichtige_abfahrten = [a for a in abfahrten if
            a["Linienname"].startswith('U') or
            a["Linienname"].startswith('EU') or
            a["Linienname"].startswith('N')]

        # bei nightlinern ist die richtung invertiert
        wichtige_abfahrten_gegenrichtung = [a for a in wichtige_abfahrten if
            (a["Richtung"] == "Richtung2" and not a["Linienname"].startswith('N')) or
            (a["Richtung"] == "Richtung1" and a["Linienname"].startswith('N'))]

        wichtige_abfahrten = [a for a in wichtige_abfahrten if
            (a["Richtung"] == "Richtung1" and not a["Linienname"].startswith('N')) or
            (a["Richtung"] == "Richtung2" and a["Linienname"].startswith('N'))]

        if wichtige_abfahrten:
            # nur abfahrten der gleichen linie anzeigen
            wichtige_abfahrten = [a for a in wichtige_abfahrten if
                a["Linienname"] == wichtige_abfahrten[0]["Linienname"]]

            if wichtige_abfahrten_gegenrichtung:
                # nur abfahrten der gleichen linie anzeigen
                wichtige_abfahrten_gegenrichtung = [a for a in wichtige_abfahrten_gegenrichtung if
                    a["Linienname"] == wichtige_abfahrten_gegenrichtung[0]["Linienname"]]
        else:
            # jetzt ist es auch schon egal - zeige einfach die naechste abfahrt
            naechste_abfahrt = abfahrten[0] if len(abfahrten) > 0 else None
            wichtige_abfahrten = [naechste_abfahrt]
            wichtige_abfahrten_gegenrichtung = []

        zeile1, zeile2 = format_zeilen(wichtige_abfahrten, lauftext)
        zeile1_alt, zeile2_alt = format_zeilen(wichtige_abfahrten_gegenrichtung, lauftext, empty=b"")
        if not zeile1_alt:
            zeile1_alt = zeile1
        if not zeile2_alt:
            zeile2_alt = zeile1
        print("  zeile1 = "+repr(zeile1))
        print("  zeile2 = "+repr(zeile2))
        print("  zeile1_alt = "+repr(zeile1_alt))
        print("  zeile2_alt = "+repr(zeile2_alt))
        print("  lauftext = "+repr(lauftext))

def format_zeilen(abfahrten, lauftext, empty=b"Keine Abfahrten"):
        zeile2 = b""
        if abfahrten and abfahrten[0]:
            max_abfahrten = 2 if lauftext else 3
            num_abfahrten = min(len(abfahrten), max_abfahrten)

            abfahrtszeiten = []
            for i in range(0, num_abfahrten):
                a = abfahrten[i]
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
            a = abfahrten[0]

            space_left_in_line1 = 16 - 1 - int(bool(lauftext)) - \
                len(str_abfahrtszeiten) - len(a['Linienname'])

            zeile1 = b"\x81" + a['Linienname'].encode() + b"\x87 "
            ziel = char_repl(a['Richtungstext'])
            if ziel == "Hauptbahnhof":
                ziel = "Nuernberg Hbf"
            if ziel.startswith("Fue-"):
                ziel = ziel.replace("Fue-", "F.")
            if lauftext:
                print(f"{ziel=}")
                ziel = ziel.replace("Fuerth ", "F.")
                ziel = ziel.replace("Nuernberg ", "N.")
                ziel = ziel.replace("Langwasser ", "L.")
                ziel = ziel.replace("Hauptbahnhof", "Hbf")
                ziel = ziel.replace("N.Hbf", "Nue Hbf")
                ziel = ziel[:space_left_in_line1]
                zeile1 += ziel.encode() + b" "
                zeile1 += b" " * (space_left_in_line1 - len(ziel))
            else:
                zeile1 += b" " * space_left_in_line1
                zeile2 = ziel.encode()
            zeile1 += str_abfahrtszeiten.encode()
        else:
            zeile1 = empty
            zeile2 = b""
        return (zeile1, zeile2)

def setup():
    # initialize display
    display(b"\x8e\x87")


def mainloop():
    global zeile1
    global zeile1_alt
    global zeile2
    global zeile2_alt
    global lauftext
    msg_index = 0
    last_text = None
    while True:
        update_data()

        # zeile 1: done via zeile2_scroll_msg or in else block

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
            zeile2_scroll_msg(zeile1, zeile1_alt, char_repl(dt))
        else:
            # no lauftext
            display(b"\x89\x87" + zeile1 + b"\x8A\x87" + zeile2[:16] + b" "*(16-len(zeile2)))
            time.sleep(5.1)
            display(b"\x89\x87" + zeile1_alt + b"\x8A\x87" + zeile2_alt[:16] + b" "*(16-len(zeile2_alt)))
            time.sleep(5.1)

if __name__ == '__main__':
    setup()
    mainloop()
