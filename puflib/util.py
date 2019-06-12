"""This module contains generic utilities."""

import numpy as np


def xor_list(c):
    bit_length = len(c[0])
    r = int(c[0], 2)
    for x in c[1:]:
        r = r ^ int(x, 2)
    bit_format = f'{{0:0{str(bit_length)}b}}'
    return bit_format.format(r)


def tri(c1, c2):
    ch = xor_list([c1, c2])
    t = 0
    state = 0
    for x in reversed(ch):
        if x == '0':
            t += state*2
        else:
            t += 1
            state = int(not state)
    return t


def gamma(c1, c2):
    return len(c1) - tri(c1, c2)


def beta(c1, c2):
    return tri(c1, c2)//2


def hamming(c1, c2):
    return sum([int(x1 != x2) for x1, x2 in zip(c1, c2)])


def generate_random_challenges(n=100, b=8, unique=True):
    if unique:
        s = []
        while len(s) < n:
            r = [np.random.choice([0, 1]) for x in range(b)]
            if r not in s or len(s) >= 2**b:
                s.append(r)
        return [''.join([str(y) for y in x]) for x in s]
    else:
        return [''.join([np.random.choice(['0', '1']) for x in range(b)]) for y in range(n)]


def enum_tri(n, t, start_high=None):
    """
    Recursive enumeration of the values that are in the tri-range of 0.
    """
    # resolve start-high for initial conditions:
    if start_high is None:
        if t % 2: # odd
            start_high = True
        else:
            start_high = False

    # trivial case (complexity pruning)
    if not t and not start_high: return [[0]*n]

    # sanity
    if t > 2*n - 1: return False
    if t < 0: return False

    # base case
    if n == 1:
        if t == 1:
            if start_high:
                return [[1]] # \
            return False # cannot end high on last bit
        elif t == 0:
            if not start_high:
                return [[0]] # _
            return False # cannot end high on last bit
        else:
            return False # this should never happen

    # recursive case
    if start_high:
        # case 1: stay straight
        c1 = enum_tri(n-1, t-2, True)
        # case 2: change (go down)
        c2 = enum_tri(n-1, t-1, False)
    else:
        # case 1: stay straight
        c1 = enum_tri(n-1, t, False)
        # case 2: change (go up)
        c2 = enum_tri(n-1, t-1, True)

    # assemble from our partials
    f1 = []
    f2 = []
    if c1:
        f1 = [[0] + x for x in c1 if x]
    if c2:
        f2 = [[1] + x for x in c2 if x]

    return f1 + f2


def srf_interpret(v):
    """
    0110 -> SRRS
    """
    same = True
    result = []
    for x in reversed(v):
        if x:
            result.append('R')
            same = not same
        if not x:
            result.append('S') if same else result.append('F')
    return list(reversed(result))
