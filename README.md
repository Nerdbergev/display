Abfahrtsdisplay für Öffis
=========================

### boot.py
Stellt WLAN-Verbindung her und führt NTP-Sync durch.
WLAN-Zugangsdaten hier eintragen.
Startet zudem ein webrepl für Zugriff via Netzwerk.

### main.py
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
