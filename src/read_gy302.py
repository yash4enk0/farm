import smbus2
import time

BH1750_ADDRESS = 0x23  
CONTINUOUS_HIGH_RES_MODE = 0x10

def read_light(bus):
    data = bus.read_i2c_block_data(BH1750_ADDRESS, CONTINUOUS_HIGH_RES_MODE, 2)
    lux = (data[0] << 8 | data[1]) / 1.2
    return lux

bus = smbus2.SMBus(1)
print("Reading light values...")
while True:
    try:
        lux = read_light(bus)
        print(f"Light Level: {lux:.2f} lux")
        time.sleep(1)
    except KeyboardInterrupt:
        break
