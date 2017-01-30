from flask import Flask
from plot import plot2file
import Adafruit_DHT
import datetime

app = Flask(__name__)

@app.route('/climon')
def climon():
    hum, temp = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, 4)
    return '%f %f' % (temp, hum)

@app.route('/')
def index():
    today = datetime.datetime.combine(datetime.datetime.utcnow().date(), datetime.time())
    today_range = [today, today + datetime.timedelta(days=1)]
    hum, temp = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, 4)
    plot2file("static/temps.png", today_range)

    return '<h3>Temperature %d˙C<br/>Humidity: %d%%<br/></h3><img src="/static/temps.png" />' % (temp, hum)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
