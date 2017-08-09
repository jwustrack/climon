import flask
from flask import render_template
import datetime
from collections import defaultdict
import json

import sensors
from conf import read as read_conf
import logging
import database

app = flask.Flask(__name__)
conf = None

def prettyDate(d):
    diff = datetime.datetime.utcnow() - d
    s = diff.seconds
    if diff.days > 7 or diff.days < 0:
        return d.strftime('%d %b %y')
    elif diff.days == 1:
        return '1 day ago'
    elif diff.days > 1:
        return '{} days ago'.format(diff.days)
    elif s <= 1:
        return 'just now'
    elif s < 60:
        return '{} seconds ago'.format(s)
    elif s < 120:
        return '1 minute ago'
    elif s < 3600:
        return '{:.0f} minutes ago'.format(s/60)
    elif s < 7200:
        return '1 hour ago'
    else:
        return '{:.0f} hours ago'.format(s/3600)

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

@app.route('/data/graph/all/<date>')
def galldata(date):
    fromDate, toDate = db().getDateSpan()
    sensor_data = {}
    for sensor_id in sensors.iter_ids(conf):
        sensor_data[sensor_id] = defaultdict(lambda: [])
        for d, avg_temp, avg_hum in db().get_stats(sensor_id, fromDate, toDate, 'year'):
            sensor_data[sensor_id]['temperatures'].append(dict(x=d.strftime('%Y%m%dT%H%M%S'), y=avg_temp))
            sensor_data[sensor_id]['humidities'].append(dict(x=d.strftime('%Y%m%dT%H%M%S'), y=avg_hum))
    return json.dumps(sensor_data)

@app.route('/data/graph/month/<yyyymmdd>')
def gmdata(yyyymmdd):
    day = datetime.datetime.strptime(yyyymmdd, '%Y%m%d')
    from_date, to_date = day - datetime.timedelta(days=30), day + datetime.timedelta(days=1)
    sensor_data = {}
    for sensor_id in sensors.iter_ids(conf):
        sensor_data[sensor_id] = defaultdict(lambda: [])
        for d, avg_temp, avg_hum in db().get_stats(sensor_id, from_date, to_date, 'month'):
            sensor_data[sensor_id]['temperatures'].append(dict(x=d.strftime('%Y%m%dT%H%M%S'), y=avg_temp))
            sensor_data[sensor_id]['humidities'].append(dict(x=d.strftime('%Y%m%dT%H%M%S'), y=avg_hum))
    return json.dumps(sensor_data)

@app.route('/data/graph/week/<yyyymmdd>')
def gwdata(yyyymmdd):
    day = datetime.datetime.strptime(yyyymmdd, '%Y%m%d')
    from_date, to_date = day - datetime.timedelta(days=6), day + datetime.timedelta(days=1)
    sensor_data = {}
    for sensor_id in sensors.iter_ids(conf):
        sensor_data[sensor_id] = defaultdict(lambda: [])
        for d, avg_temp, avg_hum in db().get_stats(sensor_id, from_date, to_date, 'week'):
            sensor_data[sensor_id]['temperatures'].append(dict(x=d.strftime('%Y%m%dT%H%M%S'), y=avg_temp))
            sensor_data[sensor_id]['humidities'].append(dict(x=d.strftime('%Y%m%dT%H%M%S'), y=avg_hum))
    return json.dumps(sensor_data)

@app.route('/data/graph/day/<yyyymmdd>')
def gdata(yyyymmdd):
    day = datetime.datetime.strptime(yyyymmdd, '%Y%m%d')
    sensor_data = {}
    for sensor_id in sensors.iter_ids(conf):
        data = list(db().get(sensor_id, day, day + datetime.timedelta(days=1)))[::20]
        sensor_data[sensor_id] = {}
        sensor_data[sensor_id]['temperatures'] = [dict(x=timestamp.strftime('%Y%m%dT%H%M%S'), y=temperature) for timestamp, temperature, humidity in data]
        sensor_data[sensor_id]['humidities'] = [dict(x=timestamp.strftime('%Y%m%dT%H%M%S'), y=humidity) for timestamp, temperature, humidity in data]
    return json.dumps(sensor_data)

@app.route('/<range>/<date>')
def jsgraph(range, date):
    assert range in ('day', 'week', 'month', 'year')
    return render_template('index.html', range='day', date=date)

@app.route('/<range>')
def jsgraph_today(range):
    assert range in ('day', 'week', 'month', 'year', 'all')
    timestamp = datetime.datetime.now()
    sensor_confs=dict((sensor_id, conf['sensor:%s' % sensor_id]) for sensor_id in sensors.iter_ids(conf))
    logging.debug("Sensor confs: %r" % sensor_confs)
    return render_template('index.html', range=range, date=timestamp.strftime('%Y%m%d'), sensor_confs=sensor_confs)

@app.route('/')
def index():
    return jsgraph_today('day')

def main(conf_fname):
    global conf

    logging.basicConfig(filename='climon.log',
            format='%(asctime)s %(levelname)s WEB %(message)s',
            level=logging.DEBUG)

    logging.info('Reading conf')
    conf = read_conf(conf_fname)
    logging.info('Reading conf done')
    app.run(debug=False, host='0.0.0.0', threaded=True, port=int(conf['common']['port']))

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
