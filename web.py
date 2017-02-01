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
    hum, temp = sensors.get_by_id(conf, sensor_id)()
    return '%f %f' % (temp, hum)

@app.route('/')
def index():
    today = datetime.datetime.combine(datetime.datetime.utcnow().date(), datetime.time())
    today_range = [today, today + datetime.timedelta(days=1)]
    plot2file(conf, db(), 'static/temps.png', today_range)

    html = ''
    for sensor_id in sensors.iter_ids(conf):
        hum, temp = sensors.get_by_id(conf, sensor_id)()
        html += '<h3>%s: %.1f°C %.1f%%</h3>' % (sensor_id, hum, temp)
    return html + '<img src="/static/temps.png" />'

if __name__ == '__main__':
    conf = read_conf(sys.argv[1])

    logging.basicConfig(filename='climon.log',
            format='%(asctime)s %(levelname)s %(message)s',
            level=logging.DEBUG)

    app.run(debug=True, host='0.0.0.0', port=int(conf['common']['port']))
