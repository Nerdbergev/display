Abfahrtsdisplay für Öffis
=========================

Dieser code läuft auf einem ESP32 oder RPi Pico W mit MicroPython.
- Zur Installation die boot.py anpassen.
- Dann auf einem Gerät MicroPython installieren.
- Dependencies installieren:
```
mpremote mip install urequests
```
- Passwort für webrepl setzen (der Befehl startet einen dialog)
```
mpremote
>>> import webrepl_setup

```
- Dateien kopieren:
```
mpremote cp display.py :display.py
mpremote cp main.py :main.py
mpremote cp boot.py :boot.py
```
- Debug ansehen via mpremote oder via webrepl (url wird von mpremote angezeigt - http port ist 8266)
```
mpremote
```


### boot.py
Does nothing anymore.
All moved to main.py as the usb stack
(including serial) is only initialized after boot.py
finished.

### main.py
Stellt WLAN-Verbindung her und führt NTP-Sync durch.
WLAN-Zugangsdaten hier eintragen.
Startet zudem ein webrepl für Zugriff via Netzwerk.
Ruft das Hauptprogramm auf.

### sim.py
Simulator für display, der für lokale Tests unter Linux mittels fifo (`mkfifo fifo`)
statt serieller Verbindung mit dem Hauptprogramm verbunden ist.

### display.py
Enthält das Hauptprogramm.
Zum testen (mit cPython unter Linux - benötigt `sim.py` falls physisches display nicht per RS232 verbunden ist):
```
python3 -i display.py
>>> setup()
>>> mainloop()
```

## Testen unter Linux
Im ersten Terminal:
```
mkfifo fifo
./sim.py
```

Im zweiten Terminal:
```
python3 -i display
```
… oder falls micropython unter Linux installiert ist:
```
micropython -i display
```
… und anschließend:
```
>>> setup()
>>> mainloop()
```
