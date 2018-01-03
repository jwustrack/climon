'''
Non-business-logic utility functions
'''

def firsts(rows):
    '''
    Returns the set of first elements of all rows:

    >>> sorted(firsts([(7, 1, 2),\
        [5, 4, 0, 3],\
        [8, 4],\
        [5, 4]]))
    [5, 7, 8]
    '''
    return set(r[0] for r in rows)

def pack_by(l, n):
    '''
    Yields elements from l in successive lists of size n

    >>> list(pack_by(list(range(10)), 3))
    [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]
    '''
    rest = l
    while rest:
        curr, rest = rest[:n], rest[n:]
        yield curr

def append_each(l, to_append):
    '''
    >>> append_each(['a', 'b', 'c'], tuple(range(2))) # doctest: +NORMALIZE_WHITESPACE
    [('a', 0, 1),
     ('b', 0, 1),
     ('c', 0, 1)]
    '''
    return [(element, ) + to_append for element in l]
