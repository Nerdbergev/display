#!/usr/bin/python3

import sys
import termcolor


buffer_default = [(' ', 'cyan')]*32
buffer = buffer_default.copy()
cursor = 0
color = 'cyan'

def show():
	sys.stdout.write("[H")
	sys.stdout.write("[K")
	print("+"+"-"*16+"+")
	sys.stdout.write("[K|")
	for i in range(16):
		sys.stdout.write(termcolor.colored(*buffer[i]))
	print("|")
	sys.stdout.write("[K|")
	for i in range(16, 32):
		sys.stdout.write(termcolor.colored(*buffer[i]))
	print("|")
	print("+"+"-"*16+"+")
	sys.stdout.flush()

while True:
	try:
		f = open('fifo', 'rb')
		while True:
			c = f.read(1)[0]
			if c >= 0x20 and c <= 0x7E:
				buffer[cursor] = (chr(c), color)
				show()
				cursor += 1
				cursor = min(31, cursor)
			elif c >= 1 and c <= 32:
				cursor = c - 1
			elif c == 0x89:
				cursor = 0
			elif c == 0x8A:
				cursor = 16
			elif c == 0x8E:
				buffer = buffer_default.copy()
				cursor = 0
				color = 'cyan'
				show()
			elif c == 0x80:
				color = 'red'
			elif c == 0x81:
				color = 'light_red'
			elif c == 0x82:
				color = 'yellow'
			elif c == 0x83:
				color = 'orange'
			elif c == 0x87:
				color = 'green'
	except IndexError:
		pass
