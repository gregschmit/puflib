"""This module is a library for emulating physically unclonable functions."""

import numpy as np


def generate_random_challenges(n=100, b=8):
    return [''.join([np.random.choice(['0', '1']) for x in range(b)]) for y in range(n)]


class Gate:
    """
    This represents a gate used for delay-based PUFs. The gate is instantiated
    with an RNG that should represent the PDF that models the delay.

    TODO: Add drift mechanism
    """

    def __init__(self, delay=10, sample_rng=None):
        if not sample_rng:
            sample_rng = lambda: 0
        self.sample_rng = sample_rng
        self.times_sampled = 0
        self.delay = delay

    def sample(self):
        self.times_sampled += 1
        return self.delay + self.sample_rng()

class Mux:
    """
    This just represents two `Gate` objects, up and down.
    """

    def __init__(self, gate_up=None, gate_down=None, delay=10, sample_rng=None):
        if not gate_up:
            if sample_rng:
                gate_up = Gate(delay, sample_rng)
            else:
                gate_up = Gate(delay)
        if not gate_down:
            if delay_rng:
                gate_down = Gate(delay, sample_rng)
            else:
                gate_down = Gate(delay)
        self.gates = [gate_up, gate_down]

    @property
    def up(self):
        return self.gates[0]

    @property
    def down(self):
        return self.gates[1]


class Stage:

    def __init__(self, mux_up=None, mux_down=None, production_rng=np.random.normal(10), sample_rng=lambda: 0):
        if not mux_up:
            r1a = production_rng()
            r1b = production_rng()
            mux_up = Mux(Gate(r1a, sample_rng), Gate(r1b, sample_rng))
        if not mux_down:
            r2a = production_rng()
            r2b = production_rng()
            mux_down = Mux(Gate(r2a, sample_rng), Gate(r2b, sample_rng))
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

    def __init__(self, stages=8, sensitivity=0.0, production_rng=lambda: np.random.normal(10, 0.1), sample_rng=lambda: 0):
        if not isinstance(stages, list):
            self.stages = []
            for i in range(stages):
                self.stages.append(Stage(production_rng=production_rng, sample_rng=sample_rng))
        else:
            self.stages = stages
        self.sensitivity = sensitivity

    def run_set(self, challenges=[]):
        r = []
        for ch in challenges:
            r.append(self.run(ch))
        return r

    def quicktest(self, challenge='10101010', times=100):
        """
        Perform a quick reliability test and return a tuple consisting of the
        winning value and the frequency, respectively.
        """
        results = {'0': 0, '1': 0}
        for i in range(times):
            results[self.run(challenge)] += 1
        if results['0'] > results['1']:
            return ('0', results['0']/results['1'])
        return ('1', results['1']/results['0'])


class Loop(Architecture):
    """
    This represents a loop PUF architecture. A challenge is run along with its
    complement, and the winner determines the output. If the delay difference
    is within the `sensitivity` range, then the winner will be random.
    """

    def __init__(self, stages=8, sensitivity=0.01):
        super().__init__(stages, sensitivity)

    def run(self, challenge):
        """
        Run the architecture with the given challenge. Challenge should be a
        bitstring; returns 1 if the challenge delay was higher than its
        complement; 0 otherwise.
        """

        if not len(challenge) == len(self.stages):
            return

        for c in challenge:
            if not (c == '0' or c == '1'):
                return

        d1 = 0.0
        d2 = 0.0

        challenge_comp = ''.join(list(map(
            lambda x: '1' if x == '0' else '0', challenge
        )))

        # iterate once for challenge
        for i, s in enumerate(self.stages):
            if challenge[i] == '0':
                d1 += s.up.up.sample() + s.down.down.sample()
            else:
                d1 += s.up.down.sample() + s.down.up.sample()

        # iterate once more for challenge complement
        for i, s in enumerate(self.stages):
            if challenge_comp[i] == '0':
                d2 += s.up.up.sample() + s.down.down.sample()
            else:
                d2 += s.up.down.sample() + s.down.up.sample()

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

    def __init__(self, stages=8, sensitivity=0.01):
        super().__init__(stages, sensitivity)

    def run(self, challenge):
        """
        Run the architecture with the given challenge. Challenge should be a
        bitstring; returns 1 if the challenge delay was higher than its
        complement; 0 otherwise.
        """

        if not len(challenge) == len(self.stages):
            return

        for c in challenge:
            if not (c == '0' or c == '1'):
                return

        d1 = 0.0
        d2 = 0.0
        flip = False

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
