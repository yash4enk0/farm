# https://www.halvorsen.blog/documents/programming/python/resources/powerpoints/Raspberry%20Pi%20and%20AM2320%20Temperature%20and%20Humidity%20Sensor%20with%20I2C%20Interface.pdf

import time
import smbus

I2C_BUS = 1
ADDRESS = 0x5C

bus = smbus.SMBus(I2C_BUS)

while True:
    try:
        bus.write_i2c_block_data(ADDRESS, 0x00, [])
        bus.write_i2c_block_data(ADDRESS, 0x03, [0x00, 0x04])
        time.sleep(0.5)
        
        try:
            block = bus.read_i2c_block_data(ADDRESS, 0, 6)
        except Exception as e:
            print(e)

        humidity = float(block[2] << 8 | block[3]) / 10
        temperature = float(block[4] << 8 | block[5]) / 10
        print(f'temperature: {temperature} °C')
        print(f'humidity: {humidity} %RH')
        time.sleep(0.5)
        
    except KeyboardInterrupt:
        break

    except:
        pass