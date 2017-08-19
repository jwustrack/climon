import flask
from flask import render_template
from datetime import datetime, timedelta
from collections import defaultdict
import json

import sensors
from conf import read as read_conf
import logging
import database

app = flask.Flask(__name__)
conf = None

def db():
    db = getattr(flask.g, 'db', None)
    if db is None:
        logging.info('Connecting to DB.')
        flask.g.db = database.Database(conf['common']['database'])
    return flask.g.db

@app.teardown_appcontext
def close_db(error):
    logging.info('Closing DB.')

@app.route('/sensor/<sensor_id>')
def climon(sensor_id):
    temp, hum = sensors.get_by_id(conf, sensor_id)()
    return '%f %f' % (temp, hum)

range_dates = dict(
	day=lambda d: (d, d + timedelta(days=1)),
	week=lambda d: (d - timedelta(days=6), d + timedelta(days=1)),
	month=lambda d: (d - timedelta(days=30), d + timedelta(days=1)),
	all=lambda d: (db().getDateSpan()),
)

@app.route('/data/<range>/<yyyymmdd>')
def ganydata(range, yyyymmdd):
    assert range in range_dates
    day = datetime.strptime(yyyymmdd, '%Y%m%d')
    from_date, to_date = range_dates[range](day)
    sensor_data = {}
    labels = []

    for sensor_id in sensors.iter_ids(conf):
        sensor_data[sensor_id] = defaultdict(lambda: [])
        for d, avg_temp, min_temp, max_temp, avg_hum, min_hum, max_hum in db().get_stats(sensor_id, from_date, to_date, range):
            sensor_data[sensor_id]['temperatures'].append(avg_temp)
            sensor_data[sensor_id]['temperatures_min'].append(min_temp)
            sensor_data[sensor_id]['temperatures_max'].append(max_temp)
            sensor_data[sensor_id]['humidities'].append(avg_hum)
            sensor_data[sensor_id]['humidities_min'].append(min_hum)
            sensor_data[sensor_id]['humidities_max'].append(max_hum)

        temp, hum = sensors.get_by_id(conf, sensor_id)()
        sensor_data[sensor_id]['temperatures'].append(temp)
        sensor_data[sensor_id]['humidities'].append(hum)

    for d in database.iter_view_times(from_date, to_date, range):
        labels.append(d.strftime('%Y%m%dT%H%M%S'))

    labels.append(datetime.now().strftime('%Y%m%dT%H%M%S'))

    return json.dumps(dict(labels=labels, data=sensor_data))

@app.route('/')
def index():
    timestamp = datetime.now()
    sensor_confs=dict((sensor_id, conf['sensor:%s' % sensor_id]) for sensor_id in sensors.iter_ids(conf))
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
