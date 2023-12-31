from devices_utils import WifiConnect, Led, AtomLite
import uasyncio as asyncio
from machine import Pin, I2C, SoftI2C
from primitives import Pushbutton
from micropython_sht4x import sht4x
from bmp280 import BMP280
from settings import TEMPMON_API_KEY, WIFI_SSID, WIFI_PWD


import time
import urequests as requests
import ujson

import ntptime
import os


failed_points_dir = 'failed_points'


class ExitButton:
    def __init__(self, device_descriptor):
        self.pin = Pin(device_descriptor.pin_button, Pin.IN, Pin.PULL_DOWN)
        self.button = Pushbutton(self.pin, suppress=True)
        self.button.long_press_ms = 2000

        self.do_exit = False
        self.button.long_func(self.exit_main)

    async def wait(self):
        while not self.do_exit:
            await asyncio.sleep_ms(200)

    def exit_main(self):
        print('Long press - exit program')
        self.do_exit = True


class BlinkingLed(Led):
    def __init__(self, pin, color):
        super().__init__(pin)
        self.color = color
        self.interval = 800

    async def run(self):
        while True:
            if self.np[0] == (0, 0, 0):
                self.set_color(*self.color)
            else:
                self.off()
            await asyncio.sleep_ms(self.interval)

def ts_now():
    timestamp = time.time()
    # Note: ATOM Epoch start on 2000-01-01 00:00, to convert to normal UNIX Epoch
    return timestamp + 946684800

class TempLogger:
    def __init__(self):
        self.interval = 30000
        self.i2c = SoftI2C(scl=32, sda=26)
        self.sht = sht4x.SHT4X(self.i2c)
        self.bm280 = BMP280(self.i2c)
        self.session_time = ts_now()
        self.request_url = 'https://kukanjiten.com/tempmon/add_temp_point/'

    def write_failed_point(self, post_data):
        print(f'Write data in {failed_points_dir}/{self.session_time}.txt')
        with open(f'{failed_points_dir}/{self.session_time}.txt', 'a') as f:
            f.write(post_data)
            f.write('\n')

    async def run(self):
        while True:
            data_pt = {
                'API_KEY': TEMPMON_API_KEY,
                'session_time': self.session_time,
                'current_time': ts_now(),
                'temperature': self.sht.measurements[0],
                'humidity': self.sht.measurements[1],
                'pressure': self.bm280.pressure

            }
            print(data_pt)

            post_data = ujson.dumps(data_pt)
            is_ok = False
            try:
                res = requests.post(
                    self.request_url,
                    headers = {'content-type': 'application/json'},
                    data = post_data).json()
                is_ok = res['result'] == 'OK'
                print(res)
            except Exception as e:
                print(f'Exception raised: {e}')

            try:
                if not is_ok:
                    self.write_failed_point(post_data)
            except Exception as e:
                print(f'Exception raised when trying to write file: {e}')

            await asyncio.sleep_ms(self.interval)


async def main():
    led = BlinkingLed(AtomLite.pin_led, (0, 0, 25))
    led.set_color(0, 200, 200)
    
    wifi_session = WifiConnect(WIFI_SSID, WIFI_PWD)
    wifi_session.connect()
    led.off()
    ntptime.settime()
    try:
        os.mkdir(failed_points_dir)
    except OSError:
        pass
    
    button = ExitButton(AtomLite)
    temp_logger = TempLogger()
    asyncio.create_task(led.run())
    asyncio.create_task(temp_logger.run())
    await button.wait()
    led.set_color(255, 0, 0)


if __name__ == '__main__':
    print('Starting temperature monitoring, long press button to stop...')

    asyncio.run(main())

