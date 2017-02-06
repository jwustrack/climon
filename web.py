import flask
from plot import plot2file
import datetime
import sensors
import sys
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
    temp, hum = sensors.get_by_id(config, sensor_id)()
    return '%f %f' % (temp, hum)

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
