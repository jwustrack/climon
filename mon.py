import datetime
import time
import sys
import conf
from datetime import datetime, timedelta
from time import sleep
import logging
import sensors
import database

def sleep_since(since, seconds):
    while since + timedelta(seconds=seconds) > datetime.utcnow():
        sleep(.5)

if __name__ == '__main__':
    conf_fname = sys.argv[1]
    config = conf.read(conf_fname)
    sensor_confs = sensors.get_all(config)

    logging.basicConfig(filename='climon.log',
            format='%(asctime)s %(levelname)s %(message)s',
            level=logging.DEBUG)

    db = database.Database(config['common']['database'])

    while True:
        timestamp = datetime.utcnow()

        for sensor_id, sensor in sensor_confs.items():
            logging.debug('Reading sensor %s', sensor_id)
            hum, temp = sensors.get_from_conf(sensor)()
            logging.debug('Sensor %s returned temp: %f hum %f', sensor_id, temp, hum)
            db.set(sensor_id, timestamp, temp, hum)

        logging.debug('Starting to sleep')
        sleep_since(timestamp, int(config['common']['sensor-interval']))
