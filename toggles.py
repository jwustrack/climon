class FakeToggle():

    def __init__(self, source):
        self.state = False

    def set(self, state):
        self.state = bool(state)

    def get(self):
        return self.state

TOGGLES = {
    'FAKE': FakeToggle,
}
