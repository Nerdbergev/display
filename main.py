import display
import sys
import time
import machine

try:
	display.setup()
	while True:
		display.mainloop()
except Exception as e:
	print("Exception occured")
	sys.print_exception(e)
	print("Resetting in 30s")
	time.sleep(30)
	machine.reset()
