import network
from time import sleep
from machine import Pin, reset
from DataFetching import DataFetching
import urequests as requests
import dht
from machine import Pin, UART
import utime, time

# Wi-Fi credentials
ssid = 'Rangapg_22'
password = '@password@22'
def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        print('Waiting for connection...')
        sleep(1)
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    #return ip
connect()

dht_vcc_pin = Pin(21, Pin.OUT)  # DHT11 VCC pin connected to pin
dust_vcc_pin = Pin(3, Pin.OUT)  # Dust sensor pin connected to pin 3
mq135_vcc_pin = Pin(17, Pin.OUT)  # MQ135 pin connected to pin 17
ldr_vcc_pin = Pin(19, Pin.OUT)  # LDR pin connected to pin 19
noise_vcc_pin = Pin(21, Pin.OUT)  # Noise sensor pin connected to pin

dust_led = Pin(2, Pin.OUT)
led = Pin(8, Pin.OUT)

ldr_vcc_pin.value(1)
dust_vcc_pin.value(1)
dht_vcc_pin.value(1)
mq135_vcc_pin.value(1)
noise_vcc_pin.value(1)

dust_led.value(1)
led.value(1)

# GPS Module UART Connection
gps_module = UART(0, baudrate=9600, tx=Pin(0), rx=Pin(1))

# Function to adjust time to IST
def adjust_time_to_ist(gps_time):
    hours, minutes, seconds = map(int, gps_time.split(':'))
    adjusted_hours = (hours + 5) % 24  # Adding 5 hours and handling overflow
    adjusted_minutes = (minutes + 30) % 60  # Adding 30 minutes and handling overflow
    adjusted_hours += 1 if minutes + 30 >= 60 else 0  # Adjusting hours if necessary
    return '{:02}:{:02}:{:02}'.format(adjusted_hours, adjusted_minutes, seconds)

# Used to Store NMEA Sentences
buff = bytearray(255)
TIMEOUT = False
FIX_STATUS = False
latitude = ""
longitude = ""
satellites = ""
gpsTime = ""

# Function to get GPS coordinates
def get_position_data(gps_module):
    global FIX_STATUS, TIMEOUT, latitude, longitude, satellites, gpsTime
    
    timeout = time.time() + 5  # 20 seconds from now
    while True:
        led.value(1)
        print("inside gps")
        gps_module.readline()
        buff = str(gps_module.readline())
        parts = buff.split(',')
        
        if parts[0] == "b'$GPGGA" and len(parts) == 15:
            if (
                parts[1]
                and parts[2]
                and parts[3]
                and parts[4]
                and parts[5]
                and parts[6]
                and parts[7]
            ):
                latitude = convert_to_degrees(parts[2])
                if parts[3] == "S":
                    latitude = -latitude
                longitude = convert_to_degrees(parts[4])
                if parts[5] == "W":
                    longitude = -longitude
                satellites = parts[7]
                gpsTime = parts[1][0:2] + ":" + parts[1][2:4] + ":" + parts[1][4:6]
                FIX_STATUS = True
                break

        if time.time() > timeout:
            TIMEOUT = True
            break
        led.value(0)
        utime.sleep_ms(500)
        

# Function to convert raw latitude and longitude to actual degrees
def convert_to_degrees(raw_degrees):
    raw_as_float = float(raw_degrees)
    first_digits = int(raw_as_float / 100)  # degrees
    next_two_digits = raw_as_float - float(first_digits * 100)  # minutes
    converted = float(first_digits + next_two_digits / 60.0)
    converted = '{0:.6f}'.format(converted)  # to 6 decimal places
    return str(converted)

def data_process():
    Sensor_data = DataFetching()
    Data = Sensor_data.read_all()
    dht_sensor = dht.DHT11(machine.Pin(16))
    dht_sensor.measure()
    temperature = dht_sensor.temperature()
    humidity = dht_sensor.humidity()
    Data["dht_temp_data"]=temperature
    Data["dht_humidity_data"]=humidity
    print(Data)
    server_url = 'http://192.168.31.132:5000/upload'
    try:
        response = requests.post(server_url, json=Data, headers={'Content-Type': 'application/json'})
        response.close()
    except Exception as e:
        print("Error sending data to server:", e)

while True:
    get_position_data(gps_module)
    print("inside while")
    data_process()
    if FIX_STATUS:
        print("fix......")
        print(latitude)
        print(longitude)
        print(satellites)
        print(gpsTime)
        
        FIX_STATUS = False
        
    if TIMEOUT:
        print("Request Timeout: No GPS data is found.")
        TIMEOUT = False

