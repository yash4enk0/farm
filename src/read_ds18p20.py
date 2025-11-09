import time

""" 
/boor/firmware/config.txt
dtoverlay=w1-gpio,gpiopin=17,pullup=1
"""


def read_temp():
    with open('/sys/bus/w1/devices/28-00000056688b/w1_slave', 'r') as f:
        lines = f.readlines()
    
    if lines[0].strip()[-3:] != 'YES':
        return None
    
    temp_pos = lines[1].find('t=')
    if temp_pos != -1:
        temp_string = lines[1][temp_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c

if __name__ == '__main__':
    while True:
        temp = read_temp()
        if temp is not None:
            print(f"Temperature: {temp:.2f}°C")
        else:
            print("Error reading temperature")
        time.sleep(0.016)