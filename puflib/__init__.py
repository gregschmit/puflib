"""This module is a library for emulating physically unclonable functions."""

import numpy as np
from .version import get_version


__version__ = get_version()


def xor(c1, c2):
    r = ''
    for x, y in zip(c1, c2):
        if x == y:
            r += '0'
        else:
            r += '1'
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


def generate_random_challenges(n=100, b=8, unique=False):
    return [''.join([np.random.choice(['0', '1']) for x in range(b)]) for y in range(n)]


class Gate:
    """
    This represents a gate used for delay-based PUFs. The gate is instantiated
    with an RNG that should represent the PDF that models the delay.

    TODO: Add drift mechanism
    """

    def __init__(self, delay=None, production_rng=None, sample_rng=None):
        if not delay:
            if not production_rng:
                delay = np.random.normal(10)
            else:
                delay = production_rng()
        if not sample_rng:
            sample_rng = lambda: 0
        self.delay = delay
        self.sample_rng = sample_rng
        self.times_sampled = 0

    def sample(self):
        self.times_sampled += 1
        return self.delay + self.sample_rng()


class Mux:
    """
    This just represents two `Gate` objects, up and down.
    """

    def __init__(self, gate_up=None, gate_down=None, production_rng=None, sample_rng=None):
        if not gate_up:
            gate_up = Gate(production_rng=production_rng, sample_rng=sample_rng)
        if not gate_down:
            gate_down = Gate(production_rng=production_rng, sample_rng=sample_rng)
        self.gates = [gate_up, gate_down]

    @property
    def up(self):
        return self.gates[0]

    @property
    def down(self):
        return self.gates[1]


class Stage:

    def __init__(self, mux_up=None, mux_down=None, production_rng=None, sample_rng=None):
        if not mux_up:
            mux_up = Mux(production_rng=production_rng, sample_rng=sample_rng)
        if not mux_down:
            mux_down = Mux(production_rng=production_rng, sample_rng=sample_rng)
        self.muxes = [mux_up, mux_down]

    @property
    def up(self):
        return self.muxes[0]

    @property
    def down(self):
        return self.muxes[1]


class Architecture:
    """
    Generic inheritable class for delay-based PUF architectures.
    """

    def __init__(self, stages=8, sensitivity=0.0, production_rng=None, sample_rng=None):
        if not isinstance(stages, list):
            self.stages = []
            for i in range(stages):
                self.stages.append(Stage(production_rng=production_rng, sample_rng=sample_rng))
        else:
            self.stages = stages
        self.sensitivity = sensitivity
        self.last_d1 = None
        self.last_d2 = None

    def run_set(self, challenges=[]):
        r = []
        for ch in challenges:
            r.append(self.run(ch))
        return r

    def quicktest(self, challenge=None, times=100):
        """
        Perform a quick reliability test and return a tuple consisting of the
        challenge, winning value, and the frequency, respectively.
        """
        if not challenge:
            challenge = ''.join([str(x) for x in np.random.choice([0,1], len(self.stages))])
        if len(challenge) != len(self.stages):
            raise ValueError("challenge must have same number of bits as the PUF has stages")
        results = {'0': 0, '1': 0}
        for i in range(times):
            results[self.run(challenge)] += 1
        if not results['1']:
            return (challenge, '1', 1.0)
        if results['0'] > results['1']:
            return (challenge, '0', results['0']/times)
        if not results['0']:
            return (challenge, '0', 1.0)
        return (challenge, '1', results['1']/times)

    def get_bitstring(self, x):
        """
        Return a bitstring representation of the passed integer, most
        significant bits truncated or padded with zeros to match the number of
        stages in the architecture.
        """
        return ('{:0' + str(len(self.stages)) + 'b}').format(x)[-len(self.stages):]

    def generate_random_crps(self, n=100):
        c_set = generate_random_challenges(n, len(self.stages))
        r = []
        for c in c_set:
            r.append((c, self.run(c)))
        return r


class Loop(Architecture):
    """
    This represents a loop PUF architecture. A challenge is run along with its
    complement, and the winner determines the output. If the delay difference
    is within the `sensitivity` range, then the winner will be random.
    """

    def __init__(self, stages=8, sensitivity=0.01, production_rng=lambda: np.random.normal(10), sample_rng=lambda: 0):
        super().__init__(stages, sensitivity, production_rng, sample_rng)

    def run(self, challenge):
        """
        Run the architecture with the given challenge. Challenge should be a
        bitstring; returns 1 if the challenge delay was higher than its
        complement; 0 otherwise.
        """

        # reverse challenge for R-to-L read
        challenge = challenge[::-1]

        d1 = 0.0
        d2 = 0.0

        # run the puf
        for i, s in enumerate(self.stages):
            if challenge[i] == '0':
                d1 += s.up.up.sample() + s.down.down.sample()
                d2 += s.up.down.sample() + s.down.up.sample()
            else:
                d1 += s.up.down.sample() + s.down.up.sample()
                d2 += s.up.up.sample() + s.down.down.sample()

        # add sensitivity randomly
        if np.random.choice([True, False]):
            d1 += self.sensitivity
        else:
            d2 += self.sensitivity

        return '1' if d1 - d2 > 0 else '0'


class Arbiter(Architecture):
    """
    This represents an arbiter PUF architecture. Two signals are processed and
    if the up/top is slower, a 1 is returned, else 0.
    """

    def __init__(self, stages=8, sensitivity=0.01, production_rng=lambda: np.random.normal(10), sample_rng=lambda: 0):
        super().__init__(stages, sensitivity, production_rng, sample_rng)

    def run(self, challenge):
        """
        Run the architecture with the given challenge. Challenge should be a
        bitstring; returns 1 if the challenge delay on the top is slower, else
        0.
        """

        # reverse challenge for R-to-L read
        challenge = challenge[::-1]

        d1 = 0.0
        d2 = 0.0
        flip = False

        # run the puf
        for i in range(len(self.stages)):
            s = self.stages[i]
            if challenge[i] == '0':
                if flip:
                    d2 += s.up.up.sample()
                    d1 += s.down.up.sample()
                else:
                    d1 += s.up.up.sample()
                    d2 += s.down.up.sample()
            else:
                flip = not flip
                if flip:
                    d2 += s.down.down.sample()
                    d1 += s.up.down.sample()
                else:
                    d1 += s.down.down.sample()
                    d2 += s.up.down.sample()

        # add sensitivity randomly
        if np.random.choice([True, False]):
            d1 += self.sensitivity
        else:
            d2 += self.sensitivity

        return '1' if d1 - d2 > 0 else '0'
