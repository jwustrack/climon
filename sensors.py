from functools import partial

def sensor_dht11(source):
    import Adafruit_DHT
    return Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, int(source))

def sensor_dht22(source):
    import Adafruit_DHT
    return Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, int(source))

def sensor_climon(source):
    from urllib import request
    return map(float, request.urlopen(source).read().split(' '))

def sensor_random(source):
    import random
    return random.random() * 100, random.random() * 50 - 15

SENSORS = {
    'DHT11': sensor_dht11,
    'DHT22': sensor_dht22,
    'CLIMON': sensor_climon,
    'RANDOM': sensor_random,
        }

def get_from_conf(sensor_conf):
    return partial(SENSORS[sensor_conf['type'].upper()], sensor_conf['source'])

def get_by_id(conf, sensor_id):
    return get_all(conf)[sensor_id]['getter']

def get_all(conf):
    sensors = {}
    for section in conf.sections():
        if section.startswith('sensor:'):
            section_conf = conf[section]
            _, sensor_id = section.split(':', 1)
            sensors[sensor_id] = section_conf
    return sensors
