import os
import time
import threading
from dataclasses import dataclass
from datetime import datetime
from traceback import print_exc
from queue import Queue
import cv2
import bme680
import smbus
import sqlite3

@dataclass
class AnalogValues:
    water_level: int
    soil_moisture: int
    ultraviolet: int

class Collector(threading.Thread):
    def __init__(self, queue, interval=2.0, photo_interval=60, photo_dir="images"):
        super().__init__(name="Collector", daemon=True)
        print('initialized collector')
        self.queue = queue
        self.interval = interval
        # self.photo_interval = photo_interval
        # self.photo_dir = photo_dir
        self.stop_event = threading.Event()
        
        self.bus = None
        self.bme_sensor = None
        # self.camera = None
        # self.last_photo_time = 0
        # self.bme680_calibration = {}
        
        self.init_sensors()
    
    def init_sensors(self):
            self.bus = smbus.SMBus(1)
            print('bus created')
            
            try:
                BME680_ADDRESS = 0x77
                self.bme_sensor = bme680.BME680(BME680_ADDRESS)
                
                self.bme_sensor.set_humidity_oversample(bme680.OS_2X)
                self.bme_sensor.set_pressure_oversample(bme680.OS_4X)
                self.bme_sensor.set_temperature_oversample(bme680.OS_8X)
                self.bme_sensor.set_filter(bme680.FILTER_SIZE_3)
                self.bme_sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)
                
                self.bme_sensor.set_gas_heater_temperature(320)
                self.bme_sensor.set_gas_heater_duration(150)
                self.bme_sensor.select_gas_heater_profile(0)
                
                print('bme680 initialized')
            except Exception as e:
                print(f'bme680 initialization failed: {e}')
                self.bme_sensor = None
            
            # os.makedirs(self.photo_dir, exist_ok=True)
            # print(f"[Collector] Photo directory: {self.photo_dir}")


    def read_ads1115(self):
            print('ads start')
            ADS1115_ADDR = 0x48

            REG_CONVERSION = 0X00
            REG_CONFIGURATION = 0X01

            OS_SINGLE = 0b1 << 15 # start conversation
            PGA = 0b001 << 9 # voltage range: +-4V
            MODE = 0b1 << 8 # single-shot mode
            DR = 0b100 << 5 # 128 sample per second
            COMP = 0b11 << 0 # disable comparator

            LSB = 4.096 / 2 ** 15

            channels = [
                ("water_level", 0b100 << 12),
                ("soil_moisture", 0b101 << 12),
                ("ultraviolet", 0b110 << 12),
            ]

            try:
                water_level = None
                soil_moisture = None
                ultraviolet = None
                for name, mux in channels:
                    config = (OS_SINGLE|mux|PGA|MODE|DR|COMP)

                    self.bus.write_i2c_block_data(ADS1115_ADDR, REG_CONFIGURATION, [(config >> 8) & 0xFF, config & 0xFF])
                    time.sleep(0.01)

                    data = self.bus.read_i2c_block_data(ADS1115_ADDR, REG_CONVERSION, 2)
                    block = (data[0] << 8) | data[1]

                    if block > 32767:
                        block -= 65536

                    voltage = block * LSB

                    if name == 'water_level':
                        water_level = block
                    elif name == 'soil_moisture':
                        soil_moisture = block
                    else:
                        ultraviolet = block

                    # print(f"[Collector]: ads1115 - {name}: {block}, Voltage: {voltage:.6f}V")
                    time.sleep(0.5)
                    
                analog_values = AnalogValues(water_level, soil_moisture, ultraviolet)

                print('ads finish')
                return analog_values
            except:
                pass
    
    def read_bme680(self):
        print('bm start')
        try:
            if not self.bme_sensor:
                print('bme680 not initialized')
                return None, None, None
            
            temperature, pressure, humidity = None, None, None
            
            for _ in range(10):
                if self.bme_sensor.get_sensor_data():
                    temperature = self.bme_sensor.data.temperature
                    pressure = self.bme_sensor.data.pressure
                    humidity = self.bme_sensor.data.humidity
                    print(f'bme680: {temperature:.2f}C, {pressure:.2f}hPa, {humidity:.2f}%RH')
                    break
                time.sleep(0.5)
            else:
                print('bme680 data not ready after retries')
                
            print('bm finish')
            return temperature, pressure, humidity
        except Exception as e:
            print(f"BME680 failed: {e}")
            print_exc()
            return None, None, None

    def read_ds18p20(self):
        print('ds start')
        try:
            with open('/sys/bus/w1/devices/28-00000056688b/w1_slave', 'r') as f:
                lines = f.readlines()
            
            if lines[0].strip()[-3:] != 'YES':
                return None
            
            temp_pos = lines[1].find('t=')
            if temp_pos != -1:
                temp_string = lines[1][temp_pos+2:]
                temp_c = float(temp_string) / 1000.0
                print('ds finish')
                return temp_c
        except Exception as e:
            print(f"DS18B20 failed: {e}")
            return None
        
    def read_gy302(self):
        print('gy start')
        try:
            BH1750_ADDRESS = 0x23  
            CONTINUOUS_HIGH_RES_MODE = 0x10
            
            data = self.bus.read_i2c_block_data(BH1750_ADDRESS, CONTINUOUS_HIGH_RES_MODE, 2)
            lux = (data[0] << 8 | data[1]) / 1.2
            print('gy finish')
            return lux
        except Exception as e:
            print(f"GY302 failed: {e}")
            return None
    
    def run(self):        
        while not self.stop_event.is_set():
            try:
                print('run started')
                
                sensor_data = self.read_sensors()
                
                print('read finished')
                self.queue.put(sensor_data)

                print('queue updated')
                
                print(f"[Collector] Updated: {sensor_data}")
                
            except Exception as e:
                print (e)
                pass
            
            self.stop_event.wait(self.interval)
        
        if self.bus:
            self.bus.close()

        # if self.camera:
        #     self.camera.close()
    
    def read_sensors(self):
        data = {}
        
        temperature_bm, pressure_bm, humidity_bm = self.read_bme680()
        if pressure_bm is not None:
            data['air_pressure'] = pressure_bm
        if temperature_bm is not None:
            data['air_temperature'] = temperature_bm
        if humidity_bm is not None:
            data['air_humidity'] = humidity_bm

        time.sleep(2)

        analog_values = self.read_ads1115()
        if analog_values is not None:
            data['water_level'] = analog_values.water_level
            data['soil_moisture'] = analog_values.soil_moisture
            data['ultraviolet'] = analog_values.ultraviolet

        time.sleep(2)

        temperature_soil = self.read_ds18p20()
        if temperature_soil is not None:
            data['temperature_soil'] = temperature_soil

        time.sleep(2)
        
        lux = self.read_gy302()
        if lux is not None:
            data['lux'] = lux
        
        # current_time = time.time()
        # if current_time - self.last_photo_time >= self.photo_interval:
        #     photo_path = self.capture_photo()
        #     if photo_path:
        #         data['photo_path'] = photo_path
        #     self.last_photo_time = current_time
        
        return data
    
    # def capture_photo(self):
    #     try:
    #         if not self.camera:
    #             self.camera = Picamera2()
    #             config = self.camera.create_still_configuration(
    #                 main={"size": (640, 480)},
    #                 controls={
    #                     "AeEnable": True,
    #                     "AwbEnable": True,
    #                     "AfMode": 2
    #                 }
    #             )
    #             self.camera.configure(config)
    #             self.camera.start()
    #             time.sleep(2)
    #             print("[Collector] Camera initialized")
            
    #         image = self.camera.capture_array()
            
    #         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #         photo_path = os.path.join(self.photo_dir, f"plant_{timestamp}.jpg")
            
    #         cv2.imwrite(photo_path, image)
            
    #         return photo_path
            
    #     except:
    #         return None
    
    def stop(self):
        self.stop_event.set()


class DBWriter(threading.Thread):
    def __init__(self, queue, db_path):
        super().__init__(name='DBWriter', daemon=True)
        self.queue = queue
        self.db_path = db_path
        self.stop_event = threading.Event()
        self.conn = None

    def run(self):
        self.init_db()

        while not self.stop_event.is_set():
            try:
                observation = self.queue.get(timeout=1)
                
                if observation:
                    print(f"writing measurement: {observation}")
                    self.write_measurement(observation)
                    
                self.queue.task_done()
            except:
                pass

        if self.conn:
            self.conn.close()

    def init_db(self):
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                photo_path TEXT,
                lux REAL,
                plant_height REAL,
                air_temperature REAL,
                temperature_soil REAL,
                air_humidity REAL,
                soil_moisture REAL,
                air_pressure REAL,
                water_level REAL,
                ultraviolet REAL
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ideal_conditions (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                soil_temperature_target REAL,
                soil_humidity_target REAL,
                light_period_start TEXT,
                light_period_end TEXT,
                watering_frequency_hours REAL,
                fan_status INTEGER DEFAULT 0,
                heater_status INTEGER DEFAULT 0,
                pump_status INTEGER DEFAULT 0,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()

    def write_measurement(self, observation):
        cursor = self.conn.cursor()
        
        res = cursor.execute('''
            INSERT INTO measurements (
                photo_path, lux, plant_height,
                air_temperature, temperature_soil,
                air_humidity, soil_moisture,
                air_pressure, water_level, ultraviolet
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            observation.get('photo_path'),
            observation.get('lux'),
            observation.get('plant_height'),
            observation.get('air_temperature'),
            observation.get('temperature_soil'),
            observation.get('air_humidity'),
            observation.get('soil_moisture'),
            observation.get('air_pressure'),
            observation.get('water_level'),
            observation.get('ultraviolet'),
        ))
        
        self.conn.commit()
        print(f"written measurement {res}")

    def stop(self):
        self.stop_event.set()


if __name__ == "__main__":
    queue = Queue()
    
    collector = Collector(queue, interval=30)
    db_writer = DBWriter(queue, "sensors.db")
    
    collector.start()
    db_writer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        collector.stop()
        db_writer.stop()
        collector.join()
        db_writer.join()