import network
import ubinascii

# Opret forbindelse til WiFi
wifi = network.WLAN(network.STA_IF)
wifi.active(True)

# Forbind til dit WiFi-netværk
wifi.connect('NETVÆRKS NAVN', 'KODE')

# Vent på, at forbindelsen bliver etableret
while not wifi.isconnected():
    pass

# Hent IP-adresse og MAC-adresse
ip_adresse = wifi.ifconfig()[0]
mac_adresse = ubinascii.hexlify(wifi.config('mac'), ':').decode().upper()

# Udskriv IP- og MAC-adresse
print('ESP32 IP-adresse:', ip_adresse)
print('ESP32 MAC-adresse:', mac_adresse)
