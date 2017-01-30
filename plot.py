import sys
import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy
import sqlite3

def plot_day(ax, hum_ax, d_range, yesterday=False):
    times = []
    temps = []
    hums = []
    start_d = None
    
    conn = sqlite3.connect('climon.db', detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.execute('SELECT * FROM climon WHERE time >= ? AND time < ?', (d_range[0], d_range[1]))

    for row in cursor.fetchall():
        timestamp, temp, hum = row
        temps.append(temp)
        if yesterday:
            timestamp += datetime.timedelta(days=1)
        times.append(timestamp)
        hums.append(hum)

    conn.close()

    if temps and hums:
        #N=6 # 6 * 10 min
        #temps = numpy.convolve(numpy.array(temps, dtype=float), numpy.ones((N,))/N, mode='same')
        #hums = numpy.convolve(numpy.array(hums, dtype=float), numpy.ones((N,))/N, mode='same')
        #ax.plot(times[:1-N], temps)
        #ax.plot(times[:1-N], hums)
        style = 'b-' if not yesterday else 'b:'
        ax.plot(times, temps, style, label='temperature')

        hum_ax.plot(times, hums, style, label='humidity')

def plot2file(out_fname, d_range):
    plt.close('all')
    fig, (ax, hum_ax) = plt.subplots(nrows=2)
    fig, ((ax, ax2), (hum_ax, hum_ax2)) = plt.subplots(2, 2, sharex='col', sharey='row', figsize=(16, 8))

    ax.set_ylabel('temperature')
    hum_ax.set_ylabel('humidity')
    ax.grid(which='both', axis='y')
    hum_ax.grid(which='both', axis='y')

    # rotate and align the tick labels so they look better
    fig.autofmt_xdate()

    plot_day(ax, hum_ax, d_range)
    plot_day(ax, hum_ax, (d_range[0] - datetime.timedelta(days=1), d_range[1] - datetime.timedelta(days=1)), yesterday=True)

    min_temps, max_temps, avg_temps = [], [], []
    min_hums, max_hums, avg_hums = [], [], []

    conn = sqlite3.connect('climon.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    cursor = conn.execute('SELECT min(time) as "min_t [timestamp]", max(time) as "max_t [timestamp]" FROM climon')
    min_date, max_date = cursor.fetchone()

    min_date, max_date = min_date.date(), max_date.date()
    n_days = (max_date - min_date).days + 1 # include the day which just started
    days = [ min_date + datetime.timedelta(days=d) for d in range(n_days) ]

    for d in days:
        conn = sqlite3.connect('climon.db', detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.execute('SELECT min(temperature), max(temperature), avg(temperature), min(humidity), max(humidity), avg(humidity) FROM climon WHERE time >= ? AND time < ?', (d, d + datetime.timedelta(days=1)))

        min_temp, max_temp, avg_temp, min_hum, max_hum, avg_hum = cursor.fetchone()
        min_temps.append(min_temp)
        max_temps.append(max_temp)
        avg_temps.append(avg_temp)
        min_hums.append(min_hum)
        max_hums.append(max_hum)
        avg_hums.append(avg_hum)

    ax2.plot(days, avg_temps)
    ax2.fill_between(days, min_temps, max_temps, alpha=0.1, label='temperature range')

    hum_ax2.plot(days, avg_hums)
    hum_ax2.fill_between(days, min_hums, max_hums, alpha=0.1, label='humidity range')

    fig.savefig(out_fname)

if __name__ == '__main__':
    plot2file('climon.db', 'temps.png', (datetime.datetime(2017, 1, 6), datetime.datetime(2017, 1, 7)))
