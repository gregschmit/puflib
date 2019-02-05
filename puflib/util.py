"""This module contains generic utilities."""


import numpy as np


def xor(c1, c2):
    r = ''
    for x, y in zip(c1, c2):
        if x == y:
            r += '0'
        else:
            r += '1'
    return r


def xor_list(c):
    r = c[0]
    for x in c[1:]:
        r = xor(r, x)
    return r


def tri(c1, c2):
    ch = xor(c1, c2)
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
