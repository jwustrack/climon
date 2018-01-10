import flask
from flask import render_template, current_app
from datetime import datetime, timedelta
import time
from collections import defaultdict
import json

from conf import Conf
import logging
import database
import threading

app = flask.Flask(__name__)
conf = None

def get_db():
    l = threading.local()
    db = getattr(l, 'db', None)
    if db is None:
        logging.info('Connecting to DB.')
        l.db = database.ReadDB(conf.raw['common']['database'])
    return l.db

@app.route('/sensor/<sensor_id>')
def climon(sensor_id):
    temp, hum = conf.get_element('sensor', sensor_id)()
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

@app.route('/data/toggle/<toggle_id>/<state>')
def settoggle(toggle_id, state):
    toggle = conf.get_element('toggle', toggle_id)
    toggle.set(json.loads(state))
    return json.dumps(toggle.get())

@app.route('/data/toggle/<toggle_id>')
def gettoggle(toggle_id):
    return json.dumps(conf.get_element('toggle', toggle_id).get())

@app.route('/data/now')
def gnowdata():
    sensor_data = dict(now=datetime.now().strftime('%Y%m%dT%H%M%S'), sensors={})
    for sensor_id in conf.iter_ids('sensor'):
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

    for sensor_id in conf.iter_ids('sensor'):
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
def stats():
    timestamp = datetime.now()
    sensor_confs = dict(conf.iter_sections('sensor'))
    return render_template('stats.html', date=timestamp.strftime('%Y%m%d'), sensor_confs=sensor_confs)

@app.route('/overview')
def overview():
    timestamp = datetime.now()
    sensor_confs = dict(conf.iter_sections('sensor'))
    toggle_confs = dict(conf.iter_sections('toggle'))
    return render_template('overview.html', date=timestamp.strftime('%Y%m%d'), sensor_confs=sensor_confs, toggle_confs=toggle_confs)

def main(conf_fname, debug=False):
    global conf

    logging.basicConfig(filename='climon.log',
                        format='%(asctime)s %(levelname)s WEB %(message)s',
                        level=logging.DEBUG)

    logging.info('Reading conf')
    conf = Conf(conf_fname)
    logging.info('Reading conf done')

    app.run(debug=debug, host='0.0.0.0', threaded=not debug, port=int(conf.raw['common']['port']))

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
