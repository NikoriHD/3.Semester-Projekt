import network
import socket
import time
from machine import Pin
import ntptime  # Synkronisering via NTP
import urequests  # Til HTTP-anmodninger
import ujson  # JSON-formatering

# WiFi-opsætning
wifi_ssid = "TP-Link_F70A"
wifi_password = "Team1329"

wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(wifi_ssid, wifi_password)

while not wifi.isconnected():
    time.sleep(1)

print('Connected to WiFi:', wifi.ifconfig())

# Synkronisering af tid via NTP
try:
    ntptime.settime()
    print("Tid synkroniseret")
except Exception as e:
    print(f"Fejl ved synkronisering af tid: {e}")

# Flask-serverens URL
flask_url = "http://192.168.0.226:5000/update_stop_time"

# Opsætning af hardware
LED_PIN = 25
MOTOR_PIN = 26
PIR_PIN = 27
led = Pin(LED_PIN, Pin.OUT)
motor = Pin(MOTOR_PIN, Pin.OUT)
pir_sensor = Pin(PIR_PIN, Pin.IN)

# Funktion til vibration og LED-kontrol
def start_vibration():
    print("Vibration startet.")
    motor.value(1)  # Tænd motor (HIGH)

def stop_vibration():
    print("Vibration stoppet.")
    motor.value(0)  # Sluk motor (LOW)

def led_blink(times=1):
    for _ in range(times):
        led.value(1)
        time.sleep(0.5)
        led.value(0)
        time.sleep(0.5)

def led_off():
    led.value(0)  # Sluk LED

# Funktion til justering til dansk tid
def adjust_to_danish_time(current_time):
    year, month, day, hour, minute, second, weekday, yearday = current_time
    hour += 1  # CET (UTC+1)
    if month > 3 and month < 10:  # Simpel sommertidskontrol
        hour += 1
    hour %= 24
    return (year, month, day, hour, minute, second, weekday, yearday)

# Tjekker alarmtid
def check_alarm_time(target_time):
    current_time = adjust_to_danish_time(time.localtime())
    current_hour = f"{current_time[3]:02}"
    current_minute = f"{current_time[4]:02}"
    current_time_str = f"{current_hour}:{current_minute}"
    print(f"Tjekker tiden: {current_time_str}")
    return current_time_str == target_time

# Funktion til at sende stop-tidspunkt og username til databasen
def send_stop_time_to_db(stop_time_str, username):
    try:
        headers = {"Content-Type": "application/json"}
        data = ujson.dumps({"username": username, "stop_time": stop_time_str})
        response = urequests.post(flask_url, data=data, headers=headers)
        print(f"Server respons: {response.text}")
        response.close()
    except Exception as e:
        print(f"Fejl ved HTTP-anmodning: {e}")

# Start server
addr = socket.getaddrinfo('0.0.0.0', 8080)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)
print('Listening on', addr)

alarm_time = None
alarm_active = False
username = ""

try:
    while True:
        # Håndter klientforespørgsler
        try:
            s.settimeout(0.5)
            cl, addr = s.accept()
            print('Client connected from', addr)
            request = cl.recv(1024)
            request = str(request)

            if '?status=' in request and 'alarm_time=' in request and 'username=' in request:
                # Udpak status, alarm_time og username
                status_start = request.find('?status=') + len('?status=')
                status_end = request.find('&', status_start)
                if status_end == -1:
                    status_end = len(request)

                alarm_time_start = request.find('alarm_time=') + len('alarm_time=')
                alarm_time_end = request.find('&', alarm_time_start)
                if alarm_time_end == -1:
                    alarm_time_end = len(request)

                username_start = request.find('username=') + len('username=')
                username_end = request.find(' ', username_start)
                if username_end == -1:
                    username_end = len(request)

                status = request[status_start:status_end]
                alarm_time = request[alarm_time_start:alarm_time_end]
                username = request[username_start:username_end]

                print(f"Forbundet - Alarm time: {alarm_time}, username: {username}")

                # Blink LED 3 gange ved forbindelsen
                if status == "forbundet":
                    led_blink(times=3)

                response = f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nForbundet - Alarm time: {alarm_time}, username: {username}"
                cl.send(response)

            cl.close()
        except OSError:
            pass

        # Kontroller alarmen
        if alarm_time and not alarm_active:
            if check_alarm_time(alarm_time):
                print(f"Alarm aktiveret: {alarm_time}")
                start_vibration()
                alarm_active = True

        # Blink LED og stop ved bevægelse
        if alarm_active:
            if pir_sensor.value() == 1:
                stop_time = adjust_to_danish_time(time.localtime())
                stop_time_str = f"{stop_time[3]:02}:{stop_time[4]:02}:{stop_time[5]:02}"
                print(f"Bevægelse registreret - stopper alarm. Tidspunkt: {stop_time_str}")
                stop_vibration()
                led_off()
                send_stop_time_to_db(stop_time_str, username)
                alarm_active = False
                alarm_time = None
            else:
                led_blink()

        time.sleep(0.1)
except KeyboardInterrupt:
    print("Afslutter programmet.")
    stop_vibration()
    led_off()
s.close()
