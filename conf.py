'''
>>> c = Conf('climon.conf.test')

>>> list(c.iter_ids('sensor'))
['sine', 'web']
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

from toggles import TOGGLES, InvertedToggle
from sensors import SENSORS

ELEMENTS = {
    'toggle': TOGGLES,
    'sensor': SENSORS,
}

def new_element(element_type, element_conf):
    make_element = ELEMENTS[element_type][element_conf['type'].upper()]
    element = make_element(element_conf['source'])
    if element_type == 'toggle' and element_conf.get('invert', None) == 'true':
        element = InvertedToggle(element)
    element.conf = element_conf
    element.conf['element_type'] = element_type
    return element

class Conf(object):

    def __init__(self, fname):
        import configparser
        self.raw = configparser.ConfigParser()
        self.raw.read(fname)

    def get_section(self, element_type, element_id):
        s = self.raw['%s:%s' % (element_type, element_id)]
        s['id'] = element_id
        s['element_type'] = element_type
        return s

    @lru_cache(maxsize=None)
    def get_element(self, element_type, element_id):
        return new_element(element_type, self.get_section(element_type, element_id))

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

    @staticmethod
    def section_type_id(section):
        try:
            s_type, s_id = section.split(':', 1)
            return s_type, s_id
        except ValueError:
            return None, None

    def iter_group_elements(self, group):
        for section in self.raw.sections():
            element_type, element_id = self.section_type_id(section)
            if element_type in ELEMENTS and self.raw[section].get('group', '') == group:
                yield section, self.get_section(element_type, element_id)

    def iter_groups(self):
        groups = [group for group_id, group in self.iter_sections('group')]
        for group in sorted(groups, key=lambda g: g['order']):
            yield group, list(self.iter_group_elements(group['id']))

class ParsedConf(object):

    def __init__(self, fname):
        self.conf = Conf(fname)
        self.groups = list(self.conf.iter_groups())
        self.sensors = dict(self.conf.iter_sections('sensor'))
        self.toggles = dict(self.conf.iter_sections('toggle'))
