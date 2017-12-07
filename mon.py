import datetime
import time
from conf import read as read_conf
from datetime import datetime, timedelta
from time import sleep
import logging
import sensors
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
    except Exception as e:
        logging.exception('Error while reading sensor %s', sensor_id)

def main(conf_fname):
    global conf

    logging.basicConfig(filename='climon.log',
            format='%(asctime)s %(levelname)s MON %(message)s',
            level=logging.DEBUG)

    conf = read_conf(conf_fname)

    if 'monitor-interval' in conf['common']:
        db = database.WriteDB(conf['common']['database'])

        while True:
            timestamp = datetime.utcnow()
            for sensor_id, sensor in sensors.iter(conf):
                log_sensor_data(db, sensor_id, sensor, timestamp)

            logging.debug('Starting to sleep')
            sleep_since(timestamp, int(conf['common']['monitor-interval']))

        db.close()
    else:
        logging.debug('Monitor is idle.')
        while True:
            sleep(60)

if __name__ == '__main__':
    import daemon
    import sys

    class Daemon(daemon.Daemon):

        def run(self):
            main('climon.conf')

    daemon = Daemon(pidfile='mon.pid')

    if 'start' == sys.argv[1]:
        daemon.start()
    elif 'stop' == sys.argv[1]:
        daemon.stop()
    elif 'restart' == sys.argv[1]:
        daemon.restart()
