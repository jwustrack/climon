'''
Database access module abstracting getters and setters.

>>> import tempfile
>>> f = tempfile.NamedTemporaryFile()
>>> db = Database(f.name)
>>> db.setup()
>>> d1 = datetime.datetime.utcnow()
>>> d2 = datetime.datetime.utcnow()
>>> d3 = datetime.datetime.utcnow()
>>> db.set('sensor1', d1, 20.0, 45.5)
>>> db.set('sensor1', d2, 22.0, 50.5)
>>> db.set('sensor2', d3, 30.0, 10.0)

>>> list(db.get('sensor1', d1, d3)) # doctest: +ELLIPSIS
[(..., 20.0, 45.5), (..., 22.0, 50.5)]
>>> list(db.get('sensor2', d1, d3))
[]

>>> db.getLatest('sensor1') # doctest: +ELLIPSIS
(datetime.datetime(...), 22.0, 50.5)
>>> db.getLatest('sensor2') # doctest: +ELLIPSIS
(datetime.datetime(...), 30.0, 10.0)


>>> db.getDayStats('sensor1', datetime.datetime.utcnow().date())
(20.0, 22.0, 21.0, 45.5, 50.5, 48.0)
>>> db.getDayStats('sensor2', datetime.datetime.utcnow().date())
(30.0, 30.0, 30.0, 10.0, 10.0, 10.0)


>>> d_from, d_to = db.getDateSpan()
>>> d_from - d1
datetime.timedelta(0)
>>> d_to - d3
datetime.timedelta(0)
>>> db.close()
'''

import sqlite3
import datetime
import logging

class Database(object):

    def __init__(self, fname):

        self.db = sqlite3.connect(fname, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        self.setup()

    def close(self):
        self.db.close()

    def setup(self):
        try:
            self.db.execute("CREATE TABLE climon (time timestamp, sensor, temperature, humidity)")
            self.db.commit()
        except sqlite3.OperationalError:
            pass

    def set(self, sensor, timestamp, temperature, humidity):
        self.db.execute("INSERT INTO climon VALUES (?, ?, ?, ?)", (timestamp, sensor, temperature, humidity))
        self.db.commit()

    def get(self, sensor, time_from, time_to):
        cursor = self.db.execute('SELECT time, temperature, humidity FROM climon WHERE sensor = ? AND time >= ? AND time < ? ORDER BY time ASC', (sensor, time_from, time_to))

        for row in cursor.fetchall():
            yield row

    def getLatest(self, sensor):
        cursor = self.db.execute('SELECT time, temperature, humidity FROM climon WHERE sensor = ? ORDER BY time desc LIMIT 1', (sensor,))
        return cursor.fetchone()

    def getDateSpan(self):
        cursor = self.db.execute('SELECT min(time) as "min_t [timestamp]", max(time) as "max_t [timestamp]" FROM climon')
        return cursor.fetchone()

    def getDayStats(self, sensor, day):
        cursor = self.db.execute('SELECT min(temperature), max(temperature), avg(temperature), min(humidity), max(humidity), avg(humidity) FROM climon WHERE sensor = ? AND time >= ? AND time < ?', (sensor, day, day + datetime.timedelta(days=1)))

        return cursor.fetchone()

if __name__ == '__main__':
    import doctest
    doctest.testmod()
