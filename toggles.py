class FakeToggle():

    def __init__(self, source):
        self.state = False

    def on(self):
        self.state = True

    def off(self):
        self.state = False

    def get(self):
        return self.state

TOGGLES = {
    'FAKE': FakeToggle,
}
