import time
import smbus
import bme680

I2C_BUS = 1
ADDRESS = 0x5C

bus = smbus.SMBus(I2C_BUS)

try:
    sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
except (RuntimeError, IOError):
    sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)

sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_filter(bme680.FILTER_SIZE_3)
sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)

sensor.set_gas_heater_temperature(320)
sensor.set_gas_heater_duration(150)
sensor.select_gas_heater_profile(0)

measurements = {
    "bme680_start_temperature": -1,
    "am2320_start_temperature": -1,
    "bme680_end_temperature": -1,
    "am2320_end_temperature": -1,
}


calibration_start = time.time()

humidity_am = -1
temperature_am = -1
pressure_bm = -1
humidity_bm = -1
temperature_bm =-1

try:
    while time.time() - calibration_start < 120: 
        for i in range(3):

            try:
                bus.write_i2c_block_data(ADDRESS, 0x00, [])
                bus.write_i2c_block_data(ADDRESS, 0x03, [0x00, 0x04])
                time.sleep(0.5)
                block = bus.read_i2c_block_data(ADDRESS, 0, 6)
                humidity_am = float(block[2] << 8 | block[3]) / 10
                temperature_am = float(block[4] << 8 | block[5]) / 10

                if measurements['am2320_start_temperature'] == -1:
                    measurements['am2320_start_temperature'] = temperature_am
                print("[Success am]")
                break

            except Exception as e:
                print(e)
            time.sleep(1)

        time.sleep(0.5)
        if sensor.get_sensor_data():
            print("[Success bm]")
            temperature_bm = sensor.data.temperature
            pressure_bm = sensor.data.pressure
            humidity_bm = sensor.data.humidity

            if measurements['bme680_start_temperature'] == -1:
                measurements['bme680_start_temperature'] = temperature_bm
                
            if sensor.data.heat_stable:
                pass

        print(f"[{time.time() - calibration_start:5.1f}] am: {temperature_am:5.1f} bm: {temperature_bm:5.1f}")
        time.sleep(1)

except KeyboardInterrupt:
    pass

measurements['am2320_end_temperature'] = temperature_am
measurements['bme680_end_temperature'] = temperature_bm

diff_am = measurements['am2320_end_temperature'] - measurements['am2320_start_temperature']
diff_bm = measurements['bme680_end_temperature'] - measurements['bme680_start_temperature']

heater_influence_degrees = diff_bm - diff_am
final_temperature_bme680_adjusted = measurements['bme680_end_temperature'] - heater_influence_degrees 

print(f""" 
bme680: {measurements['bme680_start_temperature']:5.1f} - {measurements['bme680_end_temperature']:5.1f}
am2320: {measurements['am2320_start_temperature']:5.1f} - {measurements['am2320_end_temperature']:5.1f}

bme680 diff: {diff_am:5.1f}
am2320 diff: {diff_bm:5.1f}

heater influence: {heater_influence_degrees:5.1f}

bme680 final temperature adjusted with heater influence: {final_temperature_bme680_adjusted:5.1f}

""")

