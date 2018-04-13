class FakeToggle(object):

    def __init__(self, source):
        self.state = False

    def set(self, state):
        self.state = bool(state)

    def get(self):
        return self.state

class RelayToggle(object):

    def __init__(self, source):
        import RPi.GPIO as GPIO

        self.pin = source
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(self.pin, GPIO.OUT)

    def set(self, state):
        GPIO.output(self.pin, state)

    def get(self):
        return GPIO.input(self.pin) in (1, GPIO.HIGH, True)

TOGGLES = {
    'FAKE': FakeToggle,
    'RELAY': RelayToggle,
}
