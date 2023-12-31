import sys
from time import sleep
import machine
from machine import Pin, Timer
import network
import struct
import socket
from neopixel import NeoPixel
import time


class WifiConnect:
    def __init__(self, ssid, key):
        self.ssid = ssid
        self.key = key
        self.wlan = network.WLAN(network.STA_IF)
        self.last_wol_time = 0

    @property
    def my_ip(self):
        return self.wlan.ifconfig()[0]

    @property
    def isconnected(self):
        return self.wlan.isconnected()

    def connect(self):
        self.wlan.active(True)
        if not self.wlan.isconnected():
            print('connecting to network...')
            self.wlan.connect(self.ssid, self.key)
            while not self.wlan.isconnected():
                pass
        print('network config:', self.wlan.ifconfig())

    def wol(self, mac_address):
        print('start send magic packet to ' + mac_address)
        mac_address_fmt = mac_address.replace('-', '').replace(':', '')
        host_ip = self.my_ip
        host = (host_ip[: host_ip.rindex('.') + 1] + '255', 9)
        data = ''.join(['FFFFFFFFFFFF', mac_address_fmt * 16])
        send_data = b''

        for i in range(0, len(data), 2):
            send_data = b''.join([send_data, struct.pack('B', int(data[i: i + 2], 16))])

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(send_data, host)
        self.last_wol_time = time.time()


class Button:
    def __init__(self, pin_number, on_click_fct, long_press_fct=None):
        self.pin_number = pin_number
        self.click_count = 0
        self.pin = Pin(self.pin_number, Pin.IN, Pin.PULL_DOWN)
        self.pin.irq(handler=self.action, trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING,
                     wake=machine.DEEPSLEEP)
        # self.pin.irq(handler=self.released, trigger=Pin.IRQ_RISING)
        self.fct = on_click_fct
        self.long_press_fct = long_press_fct
        self.timer = Timer(0)

    def action(self, change):
        print(f'Action: {change.value()}')
        if change.value():
            self.released()
        else:
            self.clicked()

    def clicked(self):
        self.click_count += 1
        print(f'Clicked {self.click_count} times')
        self.timer = Timer(0)
        self.timer.init(period=2000, mode=Timer.ONE_SHOT, callback=self.long_press)

    def released(self):
        print(f'Released')
        if self.timer:
            print('Normal click processing')
            self.timer.deinit()
            self.timer = None
            self.fct()

    def long_press(self, timer):
        print(f'This is a long press')
        if self.long_press_fct:
            self.long_press_fct()
            self.timer = None
        else:
            self.released()


class Led:
    def __init__(self, pin_number):
        self.pin_number = pin_number
        self.pin = machine.Pin(self.pin_number, machine.Pin.OUT)
        self.np = NeoPixel(self.pin, 1)
        self.off()

    def set_color(self, r, g, b):
        if (r, g, b) != self.np[0]:
            self.np[0] = (r, g, b)
            self.np.write()

    def off(self):
        self.set_color(0, 0, 0)


class AtomLite:
    pin_led = 27
    pin_button = 39