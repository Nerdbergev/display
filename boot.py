# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()

import utime

print("Waiting 3s")
utime.sleep(1)
print("DONE")

print("Connecting to wifi", end="")
import network
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

print("Initial NTP sync...", end="")
import ntptime
ntptime.settime()
print("DONE")

import webrepl
webrepl.start()
