import sys
import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy
import sensors
import logging

def plot_day(sensor_id, db, ax, hum_ax, d_range, yesterday=False):
    times = []
    temps = []
    hums = []
    start_d = None
    
    for row in db.get(sensor_id, d_range[0], d_range[1]):
        timestamp, temp, hum = row
        temps.append(temp)
        if yesterday:
            timestamp += datetime.timedelta(days=1)
        times.append(timestamp)
        hums.append(hum)

    if temps and hums:
        #N=6 # 6 * 10 min
        #temps = numpy.convolve(numpy.array(temps, dtype=float), numpy.ones((N,))/N, mode='same')
        #hums = numpy.convolve(numpy.array(hums, dtype=float), numpy.ones((N,))/N, mode='same')
        #ax.plot(times[:1-N], temps)
        #ax.plot(times[:1-N], hums)
        style = 'b-' if not yesterday else 'b:'
        ax.plot(times, temps, style, label='temperature')

        hum_ax.plot(times, hums, style, label='humidity')

def plot2file(config, db, out_fname, d_range):
    plt.close('all')
    fig, (ax, hum_ax) = plt.subplots(nrows=2)
    fig, ((ax, ax2), (hum_ax, hum_ax2)) = plt.subplots(2, 2, sharex='col', sharey='row', figsize=(16, 8))

    ax.set_ylabel('temperature')
    hum_ax.set_ylabel('humidity')
    ax.grid(which='both', axis='y')
    hum_ax.grid(which='both', axis='y')

    # rotate and align the tick labels so they look better
    fig.autofmt_xdate()

    min_date, max_date = db.getDateSpan()
    min_date, max_date = min_date.date(), max_date.date()
    n_days = (max_date - min_date).days + 1 # include the day which just started
    days = [ min_date + datetime.timedelta(days=d) for d in range(n_days) ]


    for sensor_id in sensors.iter_ids(config):
        plot_day(sensor_id, db, ax, hum_ax, d_range)
        plot_day(sensor_id, db, ax, hum_ax, (d_range[0] - datetime.timedelta(days=1), d_range[1] - datetime.timedelta(days=1)), yesterday=True)

        min_temps, max_temps, avg_temps = [], [], []
        min_hums, max_hums, avg_hums = [], [], []
        for d in days:
            min_temp, max_temp, avg_temp, min_hum, max_hum, avg_hum = db.getDayStats(sensor_id, d)
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

    logging.debug('Writing graph')
    fig.savefig(out_fname)
    logging.debug('Writing graph done')
