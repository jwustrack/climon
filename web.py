import flask
from flask import render_template
from datetime import datetime, timedelta
import time
from collections import defaultdict
import json

import sensors
from conf import read as read_conf
import logging
import database

app = flask.Flask(__name__)
conf = None

def get_db():
    db = getattr(flask.g, 'db', None)
    if db is None:
        logging.info('Connecting to DB.')
        flask.g.db = database.ReadDB(conf['common']['database'])
    return flask.g.db

@app.teardown_appcontext
def close_db(error):
    logging.info('Closing DB: %s', error)

@app.route('/sensor/<sensor_id>')
def climon(sensor_id):
    temp, hum = sensors.get_by_id(conf, sensor_id)()
    return '%f %f' % (temp, hum)

RANGE_DATES = dict(
    hour=lambda d: (d - timedelta(hours=1), d),
    day=lambda d: (d - timedelta(days=1), d),
    week=lambda d: (d - timedelta(days=7), d),
    month=lambda d: (d - timedelta(days=30), d),
    year=lambda d: (d - timedelta(days=356), d),
    all=lambda d: (get_db().get_date_span()),
)

def utc2local(utc):
    epoch = time.mktime(utc.timetuple())
    offset = datetime.fromtimestamp(epoch) - datetime.utcfromtimestamp(epoch)
    return utc + offset

@app.route('/data/now')
def gnowdata():
    sensor_data = dict(now=datetime.now().strftime('%Y%m%dT%H%M%S'), sensors={})
    for sensor_id in sensors.iter_ids(conf):
        _, temp, hum = get_db().get_latest(sensor_id)
        sensor_data['sensors'][sensor_id] = dict(temperature=temp, humidity=hum)
    return json.dumps(sensor_data)

@app.route('/data/<view_range>')
def ganydata(view_range):
    assert view_range in RANGE_DATES
    day = datetime.utcnow()
    from_date, to_date = RANGE_DATES[view_range](day)
    sensor_data = {}
    labels = []

    for sensor_id in sensors.iter_ids(conf):
        sensor_data[sensor_id] = defaultdict(lambda: [])
        logging.debug("Getting stats for %s", sensor_id)
        for d, avg_temp, min_temp, max_temp, avg_hum, min_hum, max_hum \
                in get_db().get_stats(sensor_id, from_date, to_date, view_range):
            sensor_data[sensor_id]['temperatures'].append(avg_temp)
            sensor_data[sensor_id]['temperatures_min'].append(min_temp)
            sensor_data[sensor_id]['temperatures_max'].append(max_temp)
            sensor_data[sensor_id]['humidities'].append(avg_hum)
            sensor_data[sensor_id]['humidities_min'].append(min_hum)
            sensor_data[sensor_id]['humidities_max'].append(max_hum)
        logging.debug("Getting stats for %s: done" % sensor_id)

        sensor_data[sensor_id]['temperatures'].append(None)
        sensor_data[sensor_id]['humidities'].append(None)

    for d in database.iter_view_times(from_date, to_date, view_range):
        labels.append(utc2local(d).strftime('%Y%m%dT%H%M%S'))

    labels.append(datetime.now().strftime('%Y%m%dT%H%M%S'))

    return json.dumps(dict(labels=labels, data=sensor_data))

@app.route('/')
def index():
    timestamp = datetime.now()
    sensor_confs = dict((sensor_id, conf['sensor:%s' % sensor_id]) for sensor_id in sensors.iter_ids(conf))
    return render_template('index.html', date=timestamp.strftime('%Y%m%d'), sensor_confs=sensor_confs)

def main(conf_fname, debug=False):
    global conf

    logging.basicConfig(filename='climon.log',
                        format='%(asctime)s %(levelname)s WEB %(message)s',
                        level=logging.DEBUG)

    logging.info('Reading conf')
    conf = read_conf(conf_fname)
    logging.info('Reading conf done')
    app.run(debug=debug, host='0.0.0.0', threaded=not debug, port=int(conf['common']['port']))

if __name__ == '__main__':
    import daemon
    import sys

    class Daemon(daemon.Daemon):

        def run(self):
            main('climon.conf')

    daemon = Daemon(pidfile='web.pid')

    if 'start' == sys.argv[1]:
        daemon.start()
    elif 'stop' == sys.argv[1]:
        daemon.stop()
    elif 'restart' == sys.argv[1]:
        daemon.restart()
    elif 'debug' == sys.argv[1]:
        main('climon.conf', debug=True)
