'''
>>> c = Conf('climon.conf.test')

>>> list(c.iter_ids('sensor'))
['sine']
>>> list(c.iter_ids('toggle'))
['fake']

>>> c.get_element('sensor', 'sine') # doctest: +ELLIPSIS
<function sine.<locals>.sine_sensor at ...>
>>> c.get_element('toggle', 'fake') # doctest: +ELLIPSIS
<toggles.FakeToggle object at ...>

>>> list(c.iter_elements('sensor')) # doctest: +ELLIPSIS
[('sine', <function sine... at ...>)]
>>> list(c.iter_elements('toggle')) # doctest: +ELLIPSIS
[('fake', <toggles.FakeToggle object at...>)]
'''

from functools import lru_cache

from toggles import TOGGLES
from sensors import SENSORS

ELEMENTS = {
    'toggle': TOGGLES,
    'sensor': SENSORS,
}

def make_element(element_type, element_conf):
    element = ELEMENTS[element_type][element_conf['type'].upper()]
    return element(element_conf['source'])

class Conf(object):

    def __init__(self, fname):
        import configparser
        self.raw = configparser.ConfigParser()
        self.raw.read(fname)

    def get_section(self, element_type, element_id):
        return self.raw['%s:%s' % (element_type, element_id)]

    @lru_cache(maxsize=None)
    def get_element(self, element_type, element_id):
        return make_element(element_type, self.get_section(element_type, element_id))

    def iter_ids(self, element_type):
        for section in self.raw.sections():
            if section.startswith('%s:' % element_type):
                _, element_id = section.split(':', 1)
                yield element_id

    def iter_sections(self, element_type):
        for element_id in self.iter_ids(element_type):
            yield element_id, self.get_section(element_type, element_id)

    def iter_elements(self, element_type):
        for element_id in self.iter_ids(element_type):
            yield element_id, self.get_element(element_type, element_id)
