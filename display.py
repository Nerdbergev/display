#!/usr/bin/python3

import re
import time
import json

try:
	import requests
except:
	import urequests
	requests = urequests

try:
	import threading
	lock = threading.Lock()
except:
	import _thread
	lock = _thread.allocate_lock()

zeile1 = b""
zeile2 = b""
#lauftext = "Hallo Nerdberg"
lauftext = ""

try:
	import serial
	#s = serial.Serial('/dev/ttyUSB0', 9600, timeout=1)
	s = open('fifo', 'wb')
except:
	import machine
	s = machine.UART(2, 9600)
	#s = machine.UART(0, 115200)

def parse_isodate(s):
	m = re.match("(\d\d\d\d)-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)\+(\d\d)", s)
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
	try:
		lock.acquire(blocking=True)
	except:
		lock.acquire()
	s.write(bts)
	lock.release()
	try:
		s.flush()
	except:
		pass


"""
def intlen(i):
	i = max(0, i)
	return math.floor(math.log(i, 10))+1
"""


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
			display(b"\x8A\x87" + zeile2 + b" "*(16-len(zeile2)))
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
			display(b"\x8A\x82" + t.encode())
			i += 1
			time.sleep(0.2)

display_loop = None
def setup():
	global display_loop
	global main_loop

	# initialize display
	s.write(b"\x8e")
	s.write(b"\x87")
	try:
		display_loop = threading.Thread(target=display_zeile2)
		display_loop.setDaemon(True)
		display_loop.start()
	except:
		display_loop = _thread.start_new_thread(display_zeile2, [])


#while True:
def mainloop():
	global zeile1
	global zeile2
	global lauftext

	#TODO: loop
	while True:
		try:
			import ntptime
			ntptime.settime()
		except:
			pass

		#j = json.load(open('json/js.json'))
		#j = json.load(open('json/night.json'))

		# Jakobinenstraße
		js = requests.get("https://start.vag.de/dm/api/abfahrten.json/vgn/2171/").text
		# Schoppershof
		#j = requests.get("https://start.vag.de/dm/api/abfahrten.json/vgn/341/").json()
		j = json.loads(js)
		#del js

		if 'Sonderinformationen' in j and j['Sonderinformationen']:
			lauftext = j['Sonderinformationen']
		else:
			lauftext = None

		abfahrten = j["Abfahrten"]
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
			display(b"\x89\x87" + zeile1)
		else:
			zeile1 = "Keine Abfahrten".encode()
			display(b"\x89\x87" + zeile1)
			zeile2 = b""
		time.sleep(20)
