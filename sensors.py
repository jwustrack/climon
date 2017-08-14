'''
Accessors for the sensors defined in the configuration

>>> import conf
>>> c = conf.read('climon.conf.test')
>>> list(iter_ids(c))
['sine']
>>> get_by_id(c, 'sine') # doctest: +ELLIPSIS
functools.partial(<function sensor_sine... at ...>, 'null')
'''

from functools import partial

def sensor_dht11(source):
    import Adafruit_DHT
    return Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, int(source))

def sensor_dht22(source):
    import Adafruit_DHT
    hum, temp = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, int(source))
    if hum < 0 or hum > 100:
        raise ValueError('humidity out of bounds')
    return hum, temp

def sensor_climon(source):
    from urllib import request
    return map(float, request.urlopen(source).read().split())

def sensor_random(source):
    import random
    return random.random() * 100, random.random() * 50 - 15

def sensor_sine_factory():
    '''
    A sensor returning metrics with variation visible both
    at day and year scale, if called once a minute.

    >>> s = sensor_sine_factory()
    >>> s(0)
    (12.17, 50.42)
    >>> for _ in range(9): _ = s(0)
    >>> s(0)
    (13.82, 54.56)
    >>> for _ in range(49): _ = s(0)
    >>> s(0)
    (20.51, 71.27)
    '''
    x = 0
    def sensor_sine(source):
        nonlocal x
        x += 1
        from math import sin
        # Make y vary from -.5 to .5
        y = .25*(sin(x/60) + sin(x/60/24/100))
        return round(40*(y+.3), 2), round(100*(y+.5), 2)
    return sensor_sine

SENSORS = {
    'DHT11': sensor_dht11,
    'DHT22': sensor_dht22,
    'CLIMON': sensor_climon,
    'RANDOM': sensor_random,
    'SINE': sensor_sine_factory(),
        }

def get_by_id(conf, sensor_id):
    sensor_conf = conf['sensor:%s' % sensor_id]
    sensor = SENSORS[sensor_conf['type'].upper()]
    return partial(sensor, sensor_conf['source'])

def iter_ids(conf):
    for section in conf.sections():
        if section.startswith('sensor:'):
            _, sensor_id = section.split(':', 1)
            yield sensor_id

def iter(conf):
    for sensor_id in iter_ids(conf):
        yield sensor_id, get_by_id(conf, sensor_id)

if __name__ == '__main__':
    import doctest
    doctest.testmod()
