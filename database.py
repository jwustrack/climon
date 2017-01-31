import sqlite3
import datetime

class Database(object):

    def __init__(self, fname):
        self.db = fname
        self.setup()

    def setup(self):
        try:
            conn = sqlite3.connect(self.db, detect_types=sqlite3.PARSE_DECLTYPES)
            conn.execute("CREATE TABLE climon (time timestamp, sensor, temperature, humidity)")
            conn.commit()
            conn.close()
        except sqlite3.OperationalError:
            pass

    def set(self, sensor, timestamp, temperature, humidity):
        conn = sqlite3.connect(self.db, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.execute("INSERT INTO climon VALUES (?, ?, ?, ?)", (timestamp, sensor, temperature, humidity))
        conn.commit()
        conn.close()

    def get(self, sensor, time_from, time_to):
        conn = sqlite3.connect(self.db, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.execute('SELECT time, temperature, humidity FROM climon WHERE sensor = ? AND time >= ? AND time < ?', (sensor, time_from, time_to))

        for row in cursor.fetchall():
            yield row

        conn.close()

    def getDateSpan(self):
        conn = sqlite3.connect(self.db, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        cursor = conn.execute('SELECT min(time) as "min_t [timestamp]", max(time) as "max_t [timestamp]" FROM climon')
        return cursor.fetchone()

    def getDayStats(self, sensor, day):
        conn = sqlite3.connect(self.db, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.execute('SELECT min(temperature), max(temperature), avg(temperature), min(humidity), max(humidity), avg(humidity) FROM climon WHERE time >= ? AND time < ?', (day, day + datetime.timedelta(days=1)))

        return cursor.fetchone()
