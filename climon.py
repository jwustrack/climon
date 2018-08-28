from multiprocessing import Process
import mon
import web

def main(conf_fname, debug=False):
    monp = Process(target=mon.run, args=(conf_fname, debug))
    monp.start()

    web.run(conf_fname, debug)

    monp.join()

if __name__ == '__main__':
    main('climon.conf', debug=True)
