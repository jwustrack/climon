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
view_ranges = dict(
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

class DB(object):

    def __init__(self, fname):
        self.db = sqlite3.connect(fname, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

    def close(self):
        self.db.close()

class ReadDB(DB):

    def get(self, sensor, time_from, time_to):
        logging.debug('Getting data for sensor %r from %r to %r' % (sensor, time_from, time_to))
        cursor = self.db.execute('SELECT time, temperature, humidity FROM climon WHERE sensor = ? AND time >= ? AND time < ? ORDER BY time ASC', (sensor, time_from, time_to))

        for row in cursor.fetchall():
            yield row

    def get_null_stats(self, view_times):
        for view_time in view_times:
            yield view_time, None, None, None, None, None, None

    def get_view_times(self, rows):
        view_times = set()
        for row in rows:
            time, _, _, _, _, _, _ = row
            view_times.add(time)
        return view_times

    def get_stats(self, sensor, time_from, time_to, view_range):
        assert view_range in view_ranges

        view_times = set(iter_view_times(time_from, time_to, view_range))

        # Don't attempt to get anything outside of the date range
        minDate, maxDate = self.getDateSpan()

        null_view_times = [vtime for vtime in view_times if vtime < minDate or vtime > maxDate]
        logging.debug('Null stats: %r' % null_view_times)

        # Fill anything outside of what we have in DB with NULL values
        rows = list(self.get_null_stats([vtime for vtime in view_times if vtime < minDate or vtime > maxDate]))
    
        time_from = max(minDate, time_from)
        time_to = min(maxDate, time_to)

        cursor = self.db.execute('SELECT time [timestamp], temperature_avg, temperature_min, temperature_max, humidity_avg, humidity_min, humidity_max FROM climon_stats WHERE sensor = ? AND view_range = ? AND time >= ? AND time < ? ORDER BY time ASC', (sensor, view_range, time_from, time_to))

        stat_view_times = set()
        rows += cursor.fetchall()
        logging.debug('Found %d rows in stats table' % len(rows))

        missing_view_times = view_times - self.get_view_times(rows)
        if missing_view_times:
            rows += list(self.get_null_stats(missing_view_times))

        return sorted(rows, key=lambda r: r[0])

    def getLatest(self, sensor):
        cursor = self.db.execute('SELECT time, temperature, humidity FROM climon WHERE sensor = ? ORDER BY time desc LIMIT 1', (sensor,))
        return cursor.fetchone()

    def getDateSpan(self):
        # Getting min and max separately is much faster in sqlite3
        cursor = self.db.execute('SELECT min(time) as "min_t [timestamp]" FROM climon')
        minTime = cursor.fetchone()[0]
        cursor = self.db.execute('SELECT max(time) as "max_t [timestamp]" FROM climon')
        maxTime = cursor.fetchone()[0]
        return minTime, maxTime

class WriteDB(DB):

    def __init__(self, fname):
        super(WriteDB, self).__init__(fname)
        self.setup()

    def commit(self):
        self.db.commit()

    def setup(self):
        try:
            self.db.execute("CREATE TABLE climon_stats (time timestamp, sensor, view_range, temperature_avg, temperature_min, temperature_max, humidity_avg, humidity_min, humidity_max)")
            self.db.execute("CREATE TABLE climon (time timestamp, sensor, temperature, humidity)")
            self.db.execute("CREATE INDEX time_index ON climon(time)")
            self.commit()
        except sqlite3.OperationalError:
            pass

    def reindex(self):
        for row in self.db.execute('SELECT distinct sensor FROM climon'):
            sensor, = row
            logging.debug('Getting timestamps for %s' % (sensor,))
            timestamps = [row[0] for row in self.db.execute('SELECT time [timestamp] FROM climon WHERE sensor = ? ORDER BY time', (sensor,))]
            for view_range in view_ranges:
                self.update_view_stats(sensor, view_range, timestamps)
        self.commit()

    def set(self, sensor, timestamp, temperature, humidity):
        self.db.execute("INSERT INTO climon VALUES (?, ?, ?, ?)", (timestamp, sensor, temperature, humidity))
        self.update_stats(sensor, timestamp)
        self.commit()

    def update_view_stats(self, sensor, view_range, timestamps):
        view_timestamps = set(round_datetime(timestamp, view_range) for timestamp in timestamps)
        logging.info('Updating stats %s %s %d' % (sensor, view_range, len(view_timestamps)))
        stats = list(self.get_stats_from_raw(sensor, view_range, view_timestamps))
        self.set_stats(stats, sensor, view_range)

    def update_stats(self, sensor, timestamp):
        for view_range in view_ranges:
            view_timestamp = round_datetime(timestamp, view_range)
            stats = list(self.get_stats_from_raw(sensor, view_range, [view_timestamp]))
            self.set_stats(stats, sensor, view_range)

    def get_stats_from_raw(self, sensor, view_range, view_times):
        logging.debug('Getting raw stats for %r' % view_times)
        interval = floor(view_ranges[view_range].total_seconds())
        # we need to make datetime timezone unaware for the WHERE ... IN to work
        view_times = [ t.replace(tzinfo=None) for t in view_times ]
        for view_times in pack_by(view_times, 9999):
            query = 'select datetime((strftime(\'%%s\', time) / ?) * ?, \'unixepoch\') as "interval [timestamp]", avg(temperature), min(temperature), max(temperature), avg(humidity), min(humidity), max(humidity) from climon where sensor = ? AND "interval [timestamp]" in (%s) group by "interval [timestamp]" order by "interval [timestamp]"' % ",".join(["?"]*len(view_times))
            logging.debug('Query %r args %r' % (query, [interval, interval, sensor] + view_times))
            cursor = self.db.execute(query, [interval, interval, sensor] + view_times)
            for row in cursor:
                yield row

    def set_stats(self, rows, sensor, view_range):
        for rows in pack_by(rows, 9999):
            logging.debug('INSERT %r %r %r' % (sensor, view_range, rows))
            self.db.executemany('INSERT INTO climon_stats (sensor, view_range, time, temperature_avg, temperature_min, temperature_max, humidity_avg, humidity_min, humidity_max) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', [[sensor, view_range] + list(r) for r in rows])

def pack_by(l, n):
    rest = l
    while rest:
        curr, rest = rest[:999], rest[999:]
        yield curr


if __name__ == '__main__':
    import doctest
    doctest.testmod()
    #import sys
    #logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    #db = WriteDB('climon.db')
    #db.reindex()
