import datetime
import sqlite3
import sys

def avg(values):
    return sum(values)/len(values)

if __name__ == '__main__':
    conn = sqlite3.connect('climon.db', detect_types=sqlite3.PARSE_DECLTYPES)

    times = []
    temps = []
    hums = []
    start_timestamp = None

    tz_delta = datetime.datetime.now() - datetime.datetime.utcnow()
    
    for l in sys.stdin.readlines():
        try:
            d_str, temp, hum = l.split(' ', 2)
            temp = float(temp)
            hum = float(hum)
            timestamp = datetime.datetime.strptime(d_str, '%Y%m%dT%H%M%S') - tz_delta
            temps.append(temp)
            times.append(timestamp)
            hums.append(hum)

            if not start_timestamp or timestamp - start_timestamp > datetime.timedelta(seconds=60*10):
                print('reset')
                if start_timestamp:
                    conn.execute("INSERT INTO climon VALUES (?, ?, ?)", (times[0], avg(temps), avg(hums)))
                    conn.commit()

                start_timestamp = timestamp
                times = []
                temps = []
                hums = []

        except Exception as e:
            print('Wrongly formatted line:', e)
