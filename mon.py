from datetime import datetime, timedelta
from time import sleep
import logging

from conf import Conf
import database

def sleep_since(since, seconds):
    '''
    Sleep until the given number of seconds has elapsed since the given start time.
    In other words, this is equivalent to:
    sleep(seconds - (now - since))
    '''
    while since + timedelta(seconds=seconds) > datetime.utcnow():
        sleep(.5)

def log_sensor_data(db, sensor_id, sensor, timestamp):
    try:
        logging.debug('Reading sensor %s', sensor_id)
        hum, temp = sensor()
        logging.debug('Sensor %s returned temp: %f hum %f', sensor_id, temp, hum)
        db.set(sensor_id, timestamp, temp, hum)
    except Exception:
        logging.exception('Error while reading sensor %s', sensor_id)

def run(conf_fname, debug=False):
    logging.basicConfig(filename='climon.log',
                        format='%(asctime)s %(levelname)s MON %(message)s',
                        level=logging.DEBUG)

    conf = Conf(conf_fname)

    if 'monitor-interval' in conf.raw['common']:
        db = database.WriteDB(conf.raw['common']['database'])

        while True:
            timestamp = datetime.utcnow()
            for sensor_id, sensor in conf.iter_elements('sensor'):
                log_sensor_data(db, sensor_id, sensor, timestamp)

            logging.debug('Starting to sleep')
            sleep_since(timestamp, int(conf.raw['common']['monitor-interval']))

        db.close()
    else:
        logging.debug('Monitor is idle.')
        while True:
            sleep(60)
