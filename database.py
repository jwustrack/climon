'''
Database access module abstracting getters and setters.
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
VIEW_RANGES = dict(
    hour=td(minutes=1),
    day=td(minutes=10),
    week=td(hours=1),
    month=td(days=1),
    year=td(days=7),
    all=td(days=7),
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
    datetime.datetime(2017, 8, 28, 0, 0)
    >>> round_datetime(dt, 'year')
    datetime.datetime(2017, 8, 24, 0, 0)
    '''
    interval = VIEW_RANGES[view_range].total_seconds()
    timestamp = int(dt.replace(tzinfo=tz.utc).timestamp() / interval) * interval
    return datetime.datetime.utcfromtimestamp(timestamp)

def iter_view_times(time_from, time_to, view_range):
    '''
    >>> d1 = datetime.datetime(2017, 8, 28, 14, 15, 31)
    >>> d2 = datetime.datetime(2017, 9, 7,  0, 51)
    >>> d3 = datetime.datetime(2017, 8, 28, 14, 21, 31)
    >>> list(iter_view_times(d1, d2, 'year'))
    [datetime.datetime(2017, 8, 31, 0, 0), datetime.datetime(2017, 9, 7, 0, 0)]
    >>> list(iter_view_times(d1, d3, 'day'))
    [datetime.datetime(2017, 8, 28, 14, 20)]
    '''
    current = round_datetime(time_from, view_range)
    while current < time_to:
        if current >= time_from:
            yield current
        current += VIEW_RANGES[view_range]

def null_stats(view_times):
    '''
    >>> null_stats(range(4)) # doctest: +NORMALIZE_WHITESPACE
    [(0, None, None, None, None, None, None),
     (1, None, None, None, None, None, None),
     (2, None, None, None, None, None, None),
     (3, None, None, None, None, None, None)]
    '''
    res = []
    for view_time in view_times:
        res.append((view_time, None, None, None, None, None, None))
    return res

def get_view_times(rows):
    view_times = set()
    for row in rows:
        time, _, _, _, _, _, _ = row
        view_times.add(time)
    return view_times

def pack_by(l, n):
    '''
    >>> list(pack_by(list(range(10)), 3))
    [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
    '''
    rest = l
    while rest:
        curr, rest = rest[:n], rest[n:]
        yield curr

class DB(object):
    'Base Database class'

    def __init__(self, fname):
        self.db = sqlite3.connect(fname,
                                  detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

    def close(self):
        self.db.close()

class ReadDB(DB):
    'Read-only Database class.'

    def get(self, sensor, time_from, time_to):
        logging.debug('Getting data for sensor %r from %r to %r', sensor, time_from, time_to)
        cursor = self.db.execute('\
                SELECT time, temperature, humidity\
                FROM climon\
                WHERE sensor = ? AND time >= ? AND time < ?\
                ORDER BY time ASC', (sensor, time_from, time_to))

        for row in cursor.fetchall():
            yield row

    def get_stats(self, sensor, time_from, time_to, view_range):
        assert view_range in VIEW_RANGES

        view_times = set(iter_view_times(time_from, time_to, view_range))

        # Don't attempt to get anything outside of the date range
        db_time_from, db_time_to = self.get_date_span()
        time_from = max(db_time_from, time_from)
        time_to = min(db_time_to, time_to)

        cursor = self.db.execute('\
                SELECT time [timestamp],\
                    temperature_avg, temperature_min, temperature_max,\
                    humidity_avg, humidity_min, humidity_max\
                FROM climon_stats\
                WHERE sensor = ? AND view_range = ? AND time >= ? AND time < ?\
                ORDER BY time ASC', (sensor, view_range, time_from, time_to))
        rows = cursor.fetchall()

        logging.debug('Found %d rows in stats table', len(rows))

        # Fill anything outside of what we have in DB with NULL values
        rows += null_stats(view_times - get_view_times(rows))

        return sorted(rows, key=lambda r: r[0])

    def get_latest(self, sensor):
        cursor = self.db.execute('SELECT time, temperature, humidity\
                FROM climon\
                WHERE sensor = ?\
                ORDER BY time desc\
                LIMIT 1', (sensor,))
        return cursor.fetchone()

    def get_date_span(self):
        # Getting min and max separately is much faster in sqlite3
        cursor = self.db.execute('SELECT min(time) as "min_t [timestamp]" FROM climon')
        time_from = cursor.fetchone()[0]
        cursor = self.db.execute('SELECT max(time) as "max_t [timestamp]" FROM climon')
        time_to = cursor.fetchone()[0]
        return time_from, time_to

class WriteDB(DB):

    def __init__(self, fname):
        super(WriteDB, self).__init__(fname)
        self.setup()

    def commit(self):
        self.db.commit()

    def setup(self):
        try:
            self.db.execute("\
                    CREATE TABLE climon_stats (\
                        time timestamp, sensor, view_range,\
                        temperature_avg, temperature_min, temperature_max,\
                        humidity_avg, humidity_min, humidity_max,\
                        CONSTRAINT pk PRIMARY KEY (time, sensor, view_range))")
            self.db.execute("CREATE TABLE climon (time timestamp, sensor,\
                        temperature, humidity,\
                        CONSTRAINT pk PRIMARY KEY (time, sensor))")
            self.db.execute("CREATE INDEX climon_index ON climon(sensor, time)")
            self.commit()
        except sqlite3.OperationalError:
            pass

    def set(self, sensor, timestamp, temperature, humidity):
        self.db.execute("INSERT INTO climon VALUES (?, ?, ?, ?)",
                        (timestamp, sensor, temperature, humidity))
        self.update_stats(sensor, timestamp)
        self.commit()

    def update_view_stats(self, sensor, view_range, timestamps):
        view_timestamps = set(round_datetime(timestamp, view_range) for timestamp in timestamps)
        logging.info('Updating stats %s %s %d', sensor, view_range, len(view_timestamps))
        stats = list(self.get_stats_from_raw(sensor, view_range, view_timestamps))
        self.set_stats(stats, sensor, view_range)

    def update_stats(self, sensor, timestamp):
        for view_range in VIEW_RANGES:
            view_timestamp = round_datetime(timestamp, view_range)
            stats = list(self.get_stats_from_raw(sensor, view_range, [view_timestamp]))
            self.set_stats(stats, sensor, view_range)

    def get_stats_from_raw(self, sensor, view_range, view_times):
        logging.debug('Getting raw stats for %r', view_times)
        interval = floor(VIEW_RANGES[view_range].total_seconds())
        # we need to make datetime timezone unaware for the WHERE ... IN to work
        view_times = [t.replace(tzinfo=None) for t in view_times]
        for view_times in pack_by(view_times, 9999):
            query = '\
                    SELECT datetime((strftime(\'%%s\', time) / ?) * ?, \'unixepoch\') as "interval [timestamp]",\
                        avg(temperature), min(temperature), max(temperature),\
                        avg(humidity), min(humidity), max(humidity)\
                    FROM climon\
                    WHERE sensor = ? AND "interval [timestamp]" in (%s)\
                    GROUP BY "interval [timestamp]"\
                    ORDER BY "interval [timestamp]"' % ",".join(["?"]*len(view_times))
            logging.debug('Query %r args %r', query, [interval, interval, sensor] + view_times)
            cursor = self.db.execute(query, [interval, interval, sensor] + view_times)
            for row in cursor:
                yield row

    def set_stats(self, rows, sensor, view_range):
        for rows in pack_by(rows, 9999):
            logging.debug('INSERT %r %r %r', sensor, view_range, rows)
            self.db.executemany('\
                    INSERT OR REPLACE INTO climon_stats (sensor, view_range, time,\
                        temperature_avg, temperature_min, temperature_max,\
                        humidity_avg, humidity_min, humidity_max)\
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                                [[sensor, view_range] + list(r) for r in rows])

    def reindex(self):
        for row in self.db.execute('SELECT distinct sensor FROM climon'):
            sensor, = row
            logging.debug('Getting timestamps for %s', sensor)
            timestamps = [row[0] for row in self.db.execute('\
                    SELECT time [timestamp]\
                    FROM climon\
                    WHERE sensor = ?\
                    ORDER BY time', (sensor,))]

            for view_range in VIEW_RANGES:
                self.update_view_stats(sensor, view_range, timestamps)
        self.commit()


if __name__ == '__main__':
    import doctest
    doctest.testmod()
    #import sys
    #logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    #db = WriteDB('climon.db')
    #db.reindex()
