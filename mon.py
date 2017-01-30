import Adafruit_DHT
import datetime
import time
import sys
import sqlite3

def averageHumTemp(seconds, samples):
    hums, temps = [], []
    for _ in range(samples):
        print('Reading', _)
        hum, temp = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, 4)
        hums.append(hum)
        temps.append(temp)
        print('Sleeping', float(seconds)/samples)
        time.sleep(float(seconds)/samples)
    return sum(hums)/len(hums), sum(temps)/len(temps)

if __name__ == '__main__':
    db = sys.argv[1]

    while True:
        timestamp = datetime.datetime.utcnow()
        #hum, temp = averageHumTemp(10*6, 10)
        hum, temp = Adafruit_DHT.read_retry(Adafruit_DHT.DHT11, 4)
        if hum is not None and temp is not None:
            conn = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES)
            print('Writing', timestamp, temp, hum)
            conn.execute("INSERT INTO climon VALUES (?, ?, ?)", (timestamp, temp, hum))
            conn.commit()
            conn.close()
            time.sleep(9*60)
