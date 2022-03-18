#!/usr/bin/python3

import sys

buffer = [' ']*32
cursor = 0

def show():
	sys.stdout.write("[H")
	sys.stdout.write("[K")
	print("+"+"-"*16+"+")
	sys.stdout.write("[K")
	print("|"+''.join(buffer[0:16])+"|")
	sys.stdout.write("[K")
	print("|"+''.join(buffer[16:32])+"|")
	print("+"+"-"*16+"+")
	sys.stdout.flush()

while True:
	try:
		f = open('fifo', 'rb')
		while True:
			c = f.read(1)[0]
			if c >= 0x20 and c <= 0x7E:
				buffer[cursor] = chr(c)
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
				buffer = [' ']*32
				cursor = 0
				show()
	except IndexError:
		pass
