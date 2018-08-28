from multiprocessing import Process, Queue
import mon
import web

def main(conf_fname, debug=False):
    sensor_queue = Queue()

    monp = Process(target=mon.run, args=(conf_fname, sensor_queue, debug))
    monp.start()

    web.run(conf_fname, sensor_queue, debug)

    monp.join()

if __name__ == '__main__':
    main('climon.conf', debug=True)
