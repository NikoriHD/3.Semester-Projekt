import network

# Opret forbindelse til WiFi
wifi = network.WLAN(network.STA_IF)
wifi.active(True)

# Forbind til dit WiFi-netværk
wifi.connect('TP-Link_F70A', 'Team1329')

# Vent på, at forbindelsen bliver etableret
while not wifi.isconnected():
    pass

# Print IP-adressen
print('ESP32 IP-adresse:', wifi.ifconfig()[0])
