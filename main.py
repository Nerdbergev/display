import utime
import machine

print("Waiting 3s")
utime.sleep(1)
print("DONE")

print("Connecting to wifi", end="")
import network
network.hostname('abfahrtsdisplay')
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect("Nerdberg", "ADD_WIFI_PASSWORD")
print("...", end="")

for i in range(20):
	if wlan.isconnected():
		break
	print(".", end="")
	utime.sleep(1)
print("DONE")

ntp_synced = False
print("Initial NTP sync...", end="")
for i in range(5):
    try:
        import ntptime
        ntptime.settime()
        print("DONE")
        ntp_synced = True
        break
    except:
        print(".", end="")
        utime.sleep(1)

if not ntp_synced:
    print("FAILED")
    print("Resetting...")
    utime.sleep(3)
    machine.soft_reset()


import webrepl
webrepl.start()


import display
import sys
import time
from display import display_manual

last_exception = None

try:
    display.setup()
    while True:
        display.mainloop()
except Exception as e:
    print("Exception occured")
    sys.print_exception(e)
    last_exception = e
    print("Resetting in 30s")
    time.sleep(30)
    machine.soft_reset()
