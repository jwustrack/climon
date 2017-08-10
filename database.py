'''
Database access module abstracting getters and setters.

>>> import tempfile
>>> f = tempfile.NamedTemporaryFile()
>>> db = Database(f.name)
>>> db.setup()
>>> d0 = datetime.datetime(2017, 8, 28, 0)
>>> d1 = datetime.datetime(2017, 8, 28, 14, 31, 15)
>>> d2 = d1 + td(minutes=8)
>>> d3 = d2 + td(minutes=1)
>>> d4 = d3 + td(seconds=1)
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

>>> d_from, d_to = db.getDateSpan()
>>> d_from - d1
datetime.timedelta(0)
>>> d_to - d3
datetime.timedelta(0)

>>> list(db.get_stats_from_raw('sensor1', 'month', [round_datetime(d1, 'month')]))
[(datetime.datetime(2017, 8, 28, 12, 0), 21.0, 48.0)]
>>> list(db.get_stats_from_raw('sensor2', 'month', [round_datetime(d1, 'month')]))
[(datetime.datetime(2017, 8, 28, 12, 0), 30.0, 10.0)]
>>> list(db.get_stats_from_raw('sensor1', 'week', [round_datetime(d1, 'week')]))
[(datetime.datetime(2017, 8, 28, 14, 0), 21.0, 48.0)]
>>> list(db.get_stats_from_raw('sensor2', 'week', [round_datetime(d1, 'week')]))
[(datetime.datetime(2017, 8, 28, 14, 0), 30.0, 10.0)]
>>> list(db.get_stats_from_raw('sensor1', 'day', [round_datetime(d1, 'day')]))
[(datetime.datetime(2017, 8, 28, 14, 30), 21.0, 48.0)]
>>> list(db.get_stats_from_raw('sensor2', 'day', [round_datetime(d1, 'day')]))
[]
>>> list(db.get_stats_from_raw('sensor1', 'hour', [round_datetime(d1, 'hour')]))
[(datetime.datetime(2017, 8, 28, 14, 31), 20.0, 45.5)]
>>> list(db.get_stats_from_raw('sensor2', 'hour', [round_datetime(d1, 'hour')]))
[]

>>> list(db.get_stats('sensor1', d0, d4, 'month'))
[(datetime.datetime(2017, 8, 28, 12, 0), 21.0, 48.0)]
>>> list(db.get_stats('sensor2', d0, d4, 'month'))
[(datetime.datetime(2017, 8, 28, 12, 0), 30.0, 10.0)]
>>> list(db.get_stats('sensor1', d0, d4, 'week'))
[(datetime.datetime(2017, 8, 28, 14, 0), 21.0, 48.0)]
>>> list(db.get_stats('sensor2', d0, d4, 'week'))
[(datetime.datetime(2017, 8, 28, 14, 0), 30.0, 10.0)]
>>> list(db.get_stats('sensor1', d0, d4, 'day'))
[(datetime.datetime(2017, 8, 28, 14, 30), 21.0, 48.0)]
>>> list(db.get_stats('sensor2', d0, d4, 'day'))
[(datetime.datetime(2017, 8, 28, 14, 40), 30.0, 10.0)]
>>> list(db.get_stats('sensor1', d0, d4, 'hour'))
[(datetime.datetime(2017, 8, 28, 14, 31), 20.0, 45.5), (datetime.datetime(2017, 8, 28, 14, 39), 22.0, 50.5)]
>>> list(db.get_stats('sensor2', d0, d4, 'hour'))
[(datetime.datetime(2017, 8, 28, 14, 40), 30.0, 10.0)]

Delete all raw metrics and make sure we can still get the cached stats
>>> db.db.execute('DELETE FROM climon') # doctest: +ELLIPSIS
<sqlite3.Cursor object at ...>
>>> list(db.get_stats('sensor1', d0, d4, 'hour'))
[(datetime.datetime(2017, 8, 28, 14, 31), 20.0, 45.5), (datetime.datetime(2017, 8, 28, 14, 39), 22.0, 50.5)]
>>> list(db.get_stats('sensor2', d0, d4, 'hour'))
[(datetime.datetime(2017, 8, 28, 14, 40), 30.0, 10.0)]

>>> db.close()
'''

import sqlite3
import datetime
from datetime import timedelta as td
from datetime import timezone as tz
import logging
from math import floor

# Climon stores raw values in the climon table.
# Other tables can be reconstructed from climon.

# Intervals between values in seconds.
# The target is to have graphs show approx 100 values.
view_ranges = dict(
    hour=td(minutes=1),
    day=td(minutes=10),
    week=td(hours=1),
    month=td(hours=6),
    year=td(days=3),
    )

def round_datetime(dt, view_range):
    '''
    >>> dt = datetime.datetime(2017, 8, 28, 14, 31, 15)
    >>> round_datetime(dt, 'hour')
    datetime.datetime(2017, 8, 28, 14, 31)
    >>> round_datetime(dt, 'day')
    datetime.datetime(2017, 8, 28, 14, 30)
    >>> round_datetime(dt, 'week')
    datetime.datetime(2017, 8, 28, 14, 0)
    >>> round_datetime(dt, 'month')
    datetime.datetime(2017, 8, 28, 12, 0)
    >>> round_datetime(dt, 'year')
    datetime.datetime(2017, 8, 28, 0, 0)
    '''
    interval = view_ranges[view_range].total_seconds()
    ts = int(dt.replace(tzinfo=tz.utc).timestamp() / interval) * interval
    return datetime.datetime.utcfromtimestamp(ts)

def iter_view_times(time_from, time_to, view_range):
    '''
    >>> start, end = datetime.datetime(2017, 8, 28, 14), datetime.datetime(2017, 9, 3, 00, 51)
    >>> list(iter_view_times(start, end, 'year'))
    [datetime.datetime(2017, 8, 31, 0, 0), datetime.datetime(2017, 9, 3, 0, 0)]
    >>> list(iter_view_times(datetime.datetime(2017, 8, 28, 14, 15, 31), datetime.datetime(2017, 8, 28, 14, 21, 31), 'day'))
    [datetime.datetime(2017, 8, 28, 14, 20)]
    '''
    current = round_datetime(time_from, view_range)
    while (current < time_to):
        if current >= time_from:
            yield current
        current += view_ranges[view_range]

class Database(object):

    def __init__(self, fname):

        self.db = sqlite3.connect(fname, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        self.setup()

    def close(self):
        self.db.close()

    def setup(self):
        try:
            self.db.execute("CREATE TABLE climon_stats (time timestamp, sensor, view_range, temperature_avg, humidity_avg)")
            self.db.execute("CREATE TABLE climon (time timestamp, sensor, temperature, humidity)")
            self.db.commit()
        except sqlite3.OperationalError:
            pass

    def set(self, sensor, timestamp, temperature, humidity):
        self.db.execute("INSERT INTO climon VALUES (?, ?, ?, ?)", (timestamp, sensor, temperature, humidity))
        self.db.commit()

    def get(self, sensor, time_from, time_to):
        logging.debug('Getting data for sensor %r from %r to %r' % (sensor, time_from, time_to))
        cursor = self.db.execute('SELECT time, temperature, humidity FROM climon WHERE sensor = ? AND time >= ? AND time < ? ORDER BY time ASC', (sensor, time_from, time_to))

        for row in cursor.fetchall():
            yield row

    def get_stats_from_raw(self, sensor, view_range, view_times):
        logging.debug('Getting raw stats for %r' % view_times)
        interval = floor(view_ranges[view_range].total_seconds())
        # we need to make datetime timesone unaware for the WHERE ... IN to work
        view_times = [ t.replace(tzinfo=None) for t in view_times ]
        query = 'select datetime((strftime(\'%%s\', time) / ?) * ?, \'unixepoch\') as "interval [timestamp]", avg(temperature), avg(humidity) from climon where sensor = ? AND "interval [timestamp]" in (%s) group by "interval [timestamp]" order by "interval [timestamp]"' % ",".join(["?"]*len(view_times))
        logging.debug('Query %r args %r' % (query, [interval, interval, sensor] + view_times))
        cursor = self.db.execute(query, [interval, interval, sensor] + view_times)

        for row in cursor.fetchall():
            yield row

    def set_stats(self, rows, sensor, view_range):
        logging.debug('INSERT %r %r %r' % (sensor, view_range, rows))
        self.db.executemany('INSERT INTO climon_stats (sensor, view_range, time, temperature_avg, humidity_avg) VALUES (?, ?, ?, ?, ?)', [[sensor, view_range] + list(r) for r in rows])
        self.db.commit()

    def get_null_stats(self, view_times):
        for view_time in view_times:
            yield view_time, None, None

    def get_view_times(self, rows):
        view_times = set()
        for row in rows:
            time, _, _ = row
            view_times.add(time)
        return view_times

    def get_stats(self, sensor, time_from, time_to, view_range):
        assert view_range in view_ranges

        cursor = self.db.execute('SELECT time [timestamp], temperature_avg, humidity_avg FROM climon_stats WHERE sensor = ? AND view_range = ? AND time >= ? AND time < ? ORDER BY time ASC', (sensor, view_range, time_from, time_to))

        stat_view_times = set()
        rows = cursor.fetchall()
        stat_view_times = self.get_view_times(rows)
        logging.debug('Found %d rows in stats table' % len(stat_view_times))

        view_times = set(iter_view_times(time_from, time_to, view_range))
        missing_view_times = view_times - stat_view_times
        if missing_view_times:
            logging.debug('Need to fetch raw stats for: %r' % missing_view_times)
            raw_rows = list(self.get_stats_from_raw(sensor, view_range, missing_view_times))
            raw_view_times = self.get_view_times(raw_rows)
            null_rows = list(self.get_null_stats(missing_view_times - raw_view_times))
            self.set_stats(raw_rows + null_rows, sensor, view_range)
            rows += raw_rows + null_rows

        return sorted(rows, key=lambda r: r[0])

    def getLatest(self, sensor):
        cursor = self.db.execute('SELECT time, temperature, humidity FROM climon WHERE sensor = ? ORDER BY time desc LIMIT 1', (sensor,))
        return cursor.fetchone()

    def getDateSpan(self):
        cursor = self.db.execute('SELECT min(time) as "min_t [timestamp]", max(time) as "max_t [timestamp]" FROM climon')
        return cursor.fetchone()

if __name__ == '__main__':
    import doctest
    doctest.testmod()
