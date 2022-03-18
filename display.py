#!/usr/bin/python3

import time
import json
import threading

from datetime import datetime

import requests
import serial

zeile1 = ""
zeile2 = ""
lauftext = "Hallo Welt"

lock = threading.Lock()
s = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
#s = open('fifo', 'wb')
#s.close()


def display(bts: bytes):
	lock.acquire(blocking=True)
	s.write(bts)
	lock.release()
	s.flush()
	

def intlen(i):
	i = max(0, i)
	return math.floor(math.log(i, 10))+1


def char_repl(s):
	s = s.replace('ö', 'oe')
	s = s.replace('ä', 'ae')
	s = s.replace('ü', 'ue')
	s = s.replace('Ö', 'OE')
	s = s.replace('Ä', 'AE')
	s = s.replace('Ü', 'UE')
	s = s.replace('ß', 'ss')
	return s


def display_zeile2():
	n = 0
	last_text = None
	while True:
		while not lauftext:
			display(b"\x8A\x87" + zeile2)
			time.sleep(0.5)
		# lauftext
		my_text = lauftext
		dt = my_text
		if isinstance(my_text, list):
			if last_text == my_text:
				n += 1
				n %= len(my_text)
			else:
				n = 0
			dt = my_text[n]
		last_text = my_text
		dt = char_repl(dt)
		dt = " "*16 + dt + " "*17
		i = 0
		while i < len(dt) - 16:
			t = dt[i:i+16]
			display(b"\x8A\x82" + t.encode('ascii', errors="ignore"))
			i += 1
			time.sleep(0.2)


s.write(b"\x8e")
s.write(b"\x87")
loop = threading.Thread(target=display_zeile2)
loop.setDaemon(True)
loop.start()

while True:
	#j = json.load(open('sh.json'))

	# Jakobinenstraße
	j = requests.get("https://start.vag.de/dm/api/abfahrten.json/vgn/2171/").json()
	# Schoppershof
	#j = requests.get("https://start.vag.de/dm/api/abfahrten.json/vgn/341/").json()

	if 'Sonderinformationen' in j and j['Sonderinformationen']:
		lauftext = j['Sonderinformationen']
	else:
		lauftext = None

	abfahrten = [a for a in j['Abfahrten'] if a["Richtung"] == "Richtung1"]
	wichtige_abfahrten = [a for a in abfahrten if
		a["Linienname"].startswith('U') or
		a["Linienname"].startswith('EU') or
		a["Linienname"].startswith('N')]
	naechste_abfahrt = abfahrten[0] if len(abfahrten) > 0 else None
	if wichtige_abfahrten:
		# nur abfahrten der gleichen linie anzeigen
		wichtige_abfahrten = [a for a in wichtige_abfahrten if
			a["Linienname"] == wichtige_abfahrten[0]["Linienname"]]
	else:
		# jetzt ist es auch schon egal
		wichtige_abfahrten = [naechste_abfahrt]

	if wichtige_abfahrten:
		max_abfahrten = 2 if lauftext else 3
		num_abfahrten = min(len(wichtige_abfahrten), max_abfahrten)

		abfahrtszeiten = []
		for i in range(0, num_abfahrten):
			a = wichtige_abfahrten[i]
			az = datetime.fromisoformat(a['AbfahrtszeitIst'])
			az = az.replace(tzinfo=None)
			abfahrt_in_min = (az - datetime.now()).seconds // 60
			abfahrtszeiten.append('%i"' % abfahrt_in_min)
		if len(' '.join(abfahrtszeiten)) > (16 - 4):
			del abfahrtszeiten[-1]
		if lauftext and len(' '.join(abfahrtszeiten)) > (16 - 9):
			del abfahrtszeiten[-1]
		str_abfahrtszeiten = ' '.join(abfahrtszeiten)
		a = wichtige_abfahrten[0]
		
		space_left_in_line1 = 16 - 1 - int(bool(lauftext)) - \
			len(str_abfahrtszeiten) - len(a['Linienname'])

		zeile1 = a['Linienname'].encode() + b" "
		if lauftext:
			ziel = char_repl(a['Richtungstext'])[:space_left_in_line1]
			zeile1 += ziel.encode() + b" "
			zeile1 += b" " * (space_left_in_line1 - len(ziel))
		else:
			zeile1 += b" " * space_left_in_line1
			zeile2 = char_repl(a['Richtungstext']).encode()
		zeile1 += str_abfahrtszeiten.encode()
		display(b"\x89\x87" + zeile1)
	else:
		zeile1 = "Keine Abfahrten".encode()
		display(b"\x89\x87" + zeile1)
		zeile2 = b""
	time.sleep(20)
