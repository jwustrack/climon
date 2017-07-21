import flask
from flask import render_template
from plot import plot2file
import datetime
import json
import sys

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
    sensor_data = {}
    for sensor_id in sensors.iter_ids(conf):
        from collections import defaultdict
        sensor_data[sensor_id] = defaultdict(lambda: [])
        for d, min_temp, max_temp, avg_temp, min_hum, max_hum, avg_hum in db().getDailyStats(sensor_id):
            sensor_data[sensor_id]['temperatures'].append(dict(x=d.strftime('%Y%m%dT%H%M%S'), y=avg_temp))
            sensor_data[sensor_id]['humidities'].append(dict(x=d.strftime('%Y%m%dT%H%M%S'), y=avg_hum))
    return json.dumps(sensor_data)

@app.route('/data/graph/week/<yyyymmdd>')
def gwdata(yyyymmdd):
    day = datetime.datetime.strptime(yyyymmdd, '%Y%m%d')
    sensor_data = {}
    for sensor_id in sensors.iter_ids(conf):
        data = list(db().get(sensor_id, day - datetime.timedelta(days=6), day + datetime.timedelta(days=1)))[::20]
        sensor_data[sensor_id] = {}
        sensor_data[sensor_id]['temperatures'] = [dict(x=timestamp.strftime('%Y%m%dT%H%M%S'), y=temperature) for timestamp, temperature, humidity in data]
        sensor_data[sensor_id]['humidities'] = [dict(x=timestamp.strftime('%Y%m%dT%H%M%S'), y=humidity) for timestamp, temperature, humidity in data]
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

@app.route('/jsgraph/<range>/<date>')
def jsgraph(range, date):
    assert range in ('day', 'week', 'month', 'year')
    return render_template('index.html', range='day', date=date)

@app.route('/jsgraph/<range>')
def jsgraph_today(range):
    assert range in ('day', 'week', 'month', 'year', 'all')
    timestamp = datetime.datetime.now()
    return render_template('index.html', range=range, date=timestamp.strftime('%Y%m%d'))

@app.route('/')
def index():
    today = datetime.datetime.combine(datetime.datetime.utcnow().date(), datetime.time())
    today_range = [today, today + datetime.timedelta(days=1)]
    plot2file(conf, db(), 'static/temps.png', today_range)

    html = ''
    for sensor_id in sensors.iter_ids(conf):
        timestamp, temp, hum = db().getLatest(sensor_id)
        color = conf['sensor:%s' % sensor_id]['color']
        html += '<p style="font-family: sans-serif;color: %s">%s: %.1f°C %.1f%% (%s)</p>' % (color, sensor_id, hum, temp, prettyDate(timestamp))
    return html + '<img src="/static/temps.png" />'

if __name__ == '__main__':
    conf = read_conf(sys.argv[1])

    logging.basicConfig(filename='climon.log',
            format='%(asctime)s %(levelname)s WEB %(message)s',
            level=logging.DEBUG)

    app.run(debug=True, host='0.0.0.0', threaded=True, port=int(conf['common']['port']))
