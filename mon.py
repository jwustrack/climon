import datetime
import time
import sys
from conf import read as read_conf
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
    conf = read_conf(conf_fname)

    logging.basicConfig(filename='climon.log',
            format='%(asctime)s %(levelname)s %(message)s',
            level=logging.DEBUG)

    db = database.Database(conf['common']['database'])

    while True:
        timestamp = datetime.utcnow()

        for sensor_id in sensors.iter_ids(conf):
            try:
                logging.debug('Reading sensor %s', sensor_id)
                hum, temp = sensors.get_by_id(conf, sensor_id)()
                logging.debug('Sensor %s returned temp: %f hum %f', sensor_id, temp, hum)
                db.set(sensor_id, timestamp, temp, hum)
            except Exception as e:
                logging.exception('Error while reading sensor')

        logging.debug('Starting to sleep')
        sleep_since(timestamp, int(conf['common']['sensor-interval']))

    db.close()
