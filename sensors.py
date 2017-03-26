'''
Accessors for the sensors defined in the configuration

>>> import conf
>>> c = conf.read('climon.conf.test')
>>> list(iter_ids(c))
['test']
>>> get_by_id(c, 'test') # doctest: +ELLIPSIS
functools.partial(<function sensor_random at ...>, 'null')
'''


from functools import partial

def sensor_dht11(source):
    import Adafruit_DHT
    return Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, int(source))

def sensor_dht22(source):
    import Adafruit_DHT
    hum, temp = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, int(source))
    if hum < 0 or hum > 100:
        raise ValueError('hunidity out of bounds')
    return hum, temp

def sensor_climon(source):
    from urllib import request
    return map(float, request.urlopen(source).read().split())

def sensor_random(source):
    import random
    return random.random() * 100, random.random() * 50 - 15

SENSORS = {
    'DHT11': sensor_dht11,
    'DHT22': sensor_dht22,
    'CLIMON': sensor_climon,
    'RANDOM': sensor_random,
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

if __name__ == '__main__':
    import doctest
    doctest.testmod()
