import RPi.GPIO as GPIO

class FakeToggle(object):

    def __init__(self, source):
        self.state = False

    def set(self, state):
        self.state = bool(state)

    def get(self):
        return self.state

class ClimonToggle(object):

    def __init__(self, source):
        self.url = source

    def set(self, state):
        from urllib import request
        value = '/true' if state else '/false'
        return request.urlopen(self.url + value).read() == 'true'

    def get(self):
        from urllib import request
        return request.urlopen(self.url).read() == b'true'

class RelayToggle(object):

    def __init__(self, source):
        self.pin = int(source)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)

    def set(self, state):
        GPIO.output(self.pin, not state)

    def get(self):
        return GPIO.input(self.pin) not in (1, GPIO.HIGH, True)

TOGGLES = {
    'FAKE': FakeToggle,
    'CLIMON': ClimonToggle,
    'RELAY': RelayToggle,
}
