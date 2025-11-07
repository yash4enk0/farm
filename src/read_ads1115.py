# https://www.ti.com/lit/ds/symlink/ads1114.pdf?ts=1763570663373

import smbus
import time

ADS1115_ADDR = 0x48
bus = smbus.SMBus(1)

REG_CONVERSION = 0X00
REG_CONFIGURATION = 0X01

OS_SINGLE = 0b1 << 15 # start conversation
PGA = 0b001 << 9 # voltage range: +-4V
MODE = 0b1 << 8 # single-shot mode
DR = 0b100 << 5 # 128 sample per second
COMP = 0b11 << 0 # disable comparator

LSB = 4.096 / 2 ** 15

channels = [
    ("Water Level", 0b100 << 12),
    ("Soil Moisture", 0b101 << 12),
    ("Ultraviolet", 0b110 << 12),
]

while True:
    try:
        for name, mux in channels:
            config = (OS_SINGLE|mux|PGA|MODE|DR|COMP)
            bus.write_i2c_block_data(ADS1115_ADDR, REG_CONFIGURATION, [(config >> 8) & 0xFF, config & 0xFF])
            time.sleep(0.01)
            
            data = bus.read_i2c_block_data(ADS1115_ADDR, REG_CONVERSION, 2)
            block = (data[0] << 8) | data[1]
            
            if block > 32767:
                block -= 65536
            voltage = block * LSB
            print(f"{name}: {block}, Voltage: {voltage:.6f}V")
            time.sleep(0.5)
    except KeyboardInterrupt:
        bus.close()
        break