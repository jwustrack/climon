import logging

def url_json_get(url):
    import time, random
    from urllib import request
    import json

    for attempt in range(1, 5):
        try:
            logging.debug('GET %s' % url)
            out = request.urlopen(url).read()
            logging.debug('GET %s result: %r' % (url, out))
        except ConnectionResetError:
            logging.debug('Error: ConnectionResetError')
        else:
            try:
                return json.loads(out.decode('utf8'))
            except ValueError:
                logging.debug('ValueError: %s' % out.decode('utf8'))

        time.sleep(attempt*random.random())
    

class FakeToggle(object):

    def __init__(self, source):
        self.state = False

    def set(self, state):
        self.state = bool(state)
        return self.state

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

class EspEasyToggle(object):

    def __init__(self, source):
        self.url, self.gpio = source.split(' ')

    def set(self, state):
        value = '1' if state else '0'
        url = '%s/control?cmd=GPIO,%s,%s' % (self.url, self.gpio, value)
        res = url_json_get(url)
        if res is None or res['state'] not in (0, 1):
            raise ValueError()
        return res['state'] == 1

    def get(self):
        url = '%s/control?cmd=Status,GPIO,%s' % (self.url, self.gpio)
        res = url_json_get(url)
        if res is None or res['state'] not in (0, 1):
            raise ValueError()
        return res['state'] == 1

class RelayToggle(object):

    def __init__(self, source):
        import RPi.GPIO as GPIO

        self.pin = int(source)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)

    def set(self, state):
        import RPi.GPIO as GPIO

        GPIO.output(self.pin, state)
        return self.get()

    def get(self):
        import RPi.GPIO as GPIO

        return GPIO.input(self.pin) in (1, GPIO.HIGH, True)

class InvertedToggle(object):

    def __init__(self, otherToggle):
        self.toggle = otherToggle

    def set(self, state):
        return not self.toggle.set(not state)

    def get(self):
        return not self.toggle.get()

TOGGLES = {
    'FAKE': FakeToggle,
    'CLIMON': ClimonToggle,
    'RELAY': RelayToggle,
    'ESPEASY': EspEasyToggle,
}
