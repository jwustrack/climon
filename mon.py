from datetime import datetime, timedelta
from time import sleep
import logging

import conf_yaml
import database
import queue

def interval_over(since, seconds):
    return since + timedelta(seconds=seconds) <= datetime.utcnow()

def sleep_since(since, seconds):
    '''
    Sleep until the given number of seconds has elapsed since the given start time.
    In other words, this is equivalent to:
    sleep(seconds - (now - since))
    '''
    while since + timedelta(seconds=seconds) > datetime.utcnow():
        sleep(.5)

def log_toggle_state(db, toggle_id, toggle, timestamp):
    try:
        state = toggle['object'].get()
        logging.debug('Toggle %s returned %s', toggle_id, state)
        db.set(toggle_id, timestamp, database.Metrics.toggle, state)
    except Exception:
        logging.exception('Error getting state of toggle %s', toggle_id)

def log_sensor_data(db, sensor_id, sensor, timestamp):
    if not callable(sensor['object']):
        return

    try:
        logging.debug('Reading sensor %s', sensor_id)
        data = sensor['object']()
        logging.debug('Sensor %s returned %r', sensor_id, data)
        db.set(sensor_id, timestamp, database.Metrics.temperature, data['temperature'])
        db.set(sensor_id, timestamp, database.Metrics.humidity, data['humidity'])
    except Exception:
        logging.exception('Error while reading sensor %s', sensor_id)

def control(rdb):
    if rdb.get_latest('bathtemp', database.Metrics.temperature) < 20 \
            and datetime.time(5,0) > datetime.datetime.utcnow().time() > datetime.time(7, 0) \
            and not rdb.get_latest('bathheat', database.Metrics.toggle):
        pass

def run(conf_fname, sensor_queue, debug=False):
    logging.basicConfig(filename='climon.log',
                        format='%(asctime)s %(levelname)s MON[%(process)d/%(thread)d] %(message)s',
                        level=logging.DEBUG)

    conf = conf_yaml.load(conf_fname)
    
    if 'monitor-interval' in conf:
        db = database.WriteDB(conf['database'])

        missing_stats = set()

        queue_timestamp = monitor_timestamp = stats_timestamp = datetime.min

        while True:
            logging.debug('Queue size: %d', sensor_queue.qsize())

            while not sensor_queue.empty():
                try:
                    item = sensor_queue.get_nowait()
                    logging.debug('db.set(%r, %r, %r, %r)', item['sensor_id'], item['timestamp'], item['metric'], item['value'])
                    db.set(item['sensor_id'], item['timestamp'], item['metric'], item['value'])
                    missing_stats.add((item['sensor_id'], item['timestamp']))
                except queue.Empty:
                    logging.debug('empty sensor_queue')
                    break

            if interval_over(monitor_timestamp, conf['monitor-interval']):
                monitor_timestamp = datetime.utcnow()
                for sensor_id, sensor in conf['sensors'].items():
                    log_sensor_data(db, sensor_id, sensor, monitor_timestamp)
                    missing_stats.add((sensor_id, monitor_timestamp))
    
                for toggle_id, toggle in conf['toggles'].items():
                    log_toggle_state(db, toggle_id, toggle, monitor_timestamp)
                    missing_stats.add((toggle_id, monitor_timestamp))

            if interval_over(stats_timestamp, conf['stats-interval']):
                stats_timestamp = datetime.utcnow()
                for id, timestamp in missing_stats:
                    db.update_stats(id, timestamp)
                missing_stats = set()

            logging.debug('Starting to sleep')
            sleep_since(queue_timestamp, conf['queue-interval'])
            queue_timestamp = datetime.utcnow()

        db.close()
    else:
        logging.debug('Monitor is idle.')
        while True:
            sleep(60)
