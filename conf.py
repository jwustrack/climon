def read(fname):
    import configparser
    conf = configparser.ConfigParser()
    conf.read(fname)
    return conf

if __name__ == '__main__':
    conf = read('climon.conf')
    print(dict(conf['common']))
    for s_id, s in sensors(conf).items():
        print(s_id, dict(s))
