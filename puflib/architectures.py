"""This module is the core of the library, containing the definitions of the
low-level components and architectures."""

import numpy as np
from .util import *


class Gate:
    """
    This represents a gate used for delay-based PUFs. The gate is instantiated
    with an RNG that should represent the PDF that models the delay.

    TODO?: Add drift mechanism
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
    This abstract class represents a single PUF architecture. Subclasses should
    implement `__init__` by calling `super()`, and should implement the
    `run(self, challenge)` method.
    """

    def __init__(self, stages=8, sensitivity=0.01, production_rng=lambda: np.random.normal(10), sample_rng=lambda: 0):
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
        results = {0: 0, 1: 0}
        for i in range(times):
            results[self.run(challenge)] += 1
        if not results[1]:
            return (challenge, '1', 1.0)
        if results[0] > results[1]:
            return (challenge, '0', results[0]/times)
        if not results[0]:
            return (challenge, '0', 1.0)
        return (challenge, '1', results[1]/times)

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

        return 1 if d1 - d2 > 0 else 0


class Arbiter(Architecture):
    """
    This represents an arbiter PUF architecture. Two signals are processed and
    if the up/top is slower, a 1 is returned, else 0.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

        return 1 if d1 - d2 > 0 else 0


class CompositeArchitecture(Architecture):
    """
    This abstract class represents a PUF architecture that is made up of
    multiple PUF Architectures. Subclasses should implement `__init__` by
    calling `super()`, and should implement the `run(self, challenge)` method.

    `*args` and `**kwargs` which are passed to the constructor are passed to the
    constructor of the child PUFs.
    """

    def __init__(self, puf=Arbiter, k=4, pufs=[], *args, **kwargs):
        if not pufs and k<=1:
            raise ValueError("CompositeArchitecture must have at least 2 child PUFs")
        if pufs:
            self.pufs = pufs
        else:
            self.pufs = [puf(*args, **kwargs) for x in range(k)]

class Xor(CompositeArchitecture):
    """
    This represents an Xor PUF composite architecture.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self, challenge):
        """
        Run the architecture with the given challenge. Challenge should be a
        bitstring; return the XOR of the response for each of the child pufs.
        """

        responses = []
        for p in self.pufs:
            responses.append(p.run(challenge))
        return xor_list(responses)
