# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()

# MOVED ALL TO main.py as USB stack is only initialized after boot.py exited on RP2 port
