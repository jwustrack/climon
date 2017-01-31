from flask import Flask
from plot import plot2file
import datetime
import sensors
import sys
import conf
import logging
import database

app = Flask(__name__)
db = None
config = None

@app.route('/sensor/<sensor_id>')
def climon(sensor_id):
    temp, hum = sensors.get_by_id(config, sensor_id)()
    return '%f %f' % (temp, hum)

@app.route('/')
def index():
    today = datetime.datetime.combine(datetime.datetime.utcnow().date(), datetime.time())
    today_range = [today, today + datetime.timedelta(days=1)]
    plot2file(config, db, 'static/temps.png', today_range)

    html = ''
    for sensor_id, sensor in sensors.get_all(config).items():
        temp, hum = sensors.get_from_conf(sensor)()
        html += '<h3>%s: %.1f°C %.1f%%</h3>' % (sensor_id, hum, temp)
    return html + '<img src="/static/temps.png" />'

if __name__ == '__main__':
    conf_fname = sys.argv[1]
    config = conf.read(conf_fname)
    sensor_confs = sensors.get_all(config)

    logging.basicConfig(filename='climon.log',
            format='%(asctime)s %(levelname)s %(message)s',
            level=logging.DEBUG)

    db = database.Database(config['common']['database'])

    app.run(debug=True, host='0.0.0.0', threaded=True, port=int(config['common']['port']))
