import puflib
import unittest

class TestPUFArch(unittest.TestCase):

    def test_loop(self):
        x = puflib.Loop()
        y = x.run('10101010')
        self.assertEqual(type(y), str)

    def test_arbiter(self):
        x = puflib.Arbiter()
        y = x.run('10101010')
        self.assertEqual(type(y), str)

if __name__ == '__main__':
    unittest.main()
