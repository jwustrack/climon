from toggles import TOGGLES, InvertedToggle
from sensors import SENSORS

def iter_elements(conf, group=None):
    for sensor_id, sensor in conf['sensors'].items():
        if group is None or sensor['group'] == group:
            yield sensor_id, sensor

    for toggle_id, toggle in conf['toggles'].items():
        if group is None or toggle['group'] == group:
            yield toggle_id, toggle

def load(fname):
    import yaml
    conf = yaml.load(open(fname, 'r'))

    for sensor_id, sensor in conf['sensors'].items():
        sensor['func'] = SENSORS[sensor['type'].upper()](sensor['source'])
        sensor['element_type'] = 'sensor'

    for toggle_id, toggle in conf['toggles'].items():
        toggle['func'] = TOGGLES[toggle['type'].upper()](toggle['source'])
        toggle['element_type'] = 'toggle'

    for group_id, group in conf['groups'].items():
        group['elements'] = dict(iter_elements(conf, group_id))

    return conf
