'''
A sensor is a callable taking no arguments,
returning a humidity and a temperature.
It is constructed with a `source' parameter.
'''

from functools import partial

def sensor(func):
    '''
    The sensor decorator converts a function
    taking a source parameter into a sensor.

    >>> @sensor
    ... def test(source):
    ...     return source * 2

    >>> sensor = test('foo')
    >>> sensor()
    'foofoo'
    '''
    def func_wrapper(source):
        return partial(func, source)
    return func_wrapper

@sensor
def dht11(source):
    import Adafruit_DHT
    hum, temp = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, int(source))
    if hum < 0 or hum > 100:
        raise ValueError('humidity out of bounds')
    return hum, temp

@sensor
def dht22(source):
    import Adafruit_DHT
    hum, temp = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, int(source))
    if hum < 0 or hum > 100:
        raise ValueError('humidity out of bounds')
    return hum, temp

@sensor
def climon(source):
    from urllib import request
    return map(float, request.urlopen(source).read().split())

@sensor
def rand(source):
    import random
    return random.random() * 100, random.random() * 50 - 15

def sine(source):
    '''
    A sensor returning metrics with variation visible both
    at day and year scale, if called once a minute.

    >>> s = sine('')
    >>> s()
    (12.17, 50.42)
    >>> for _ in range(9): _ = s()
    >>> s()
    (13.82, 54.56)
    >>> for _ in range(49): _ = s()
    >>> s()
    (20.51, 71.27)
    '''
    x = hash(source)
    def sine_sensor():
        nonlocal x
        x += 1
        from math import sin
        # Make y vary from -.5 to .5
        y = .25*(sin(x/60) + sin(x/60/24/100))
        return round(40*(y+.3), 2), round(100*(y+.5), 2)
    return sine_sensor

def empty(source):
    class EmptySensor(object):
        pass

    return EmptySensor()

SENSORS = {
    'DHT11': dht11,
    'DHT22': dht22,
    'CLIMON': climon,
    'RANDOM': rand,
    'SINE': sine,
    'WEB': empty
}
