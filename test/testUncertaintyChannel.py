from pickhardtpayments.UncertaintyChannel import UncertaintyChannel
from pickhardtpayments.Channel import Channel
import unittest
import sys
sys.path.append(r'../pickhardtpayments')


class UncertaintyChannelTestCases(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(UncertaintyChannelTestCases, self).__init__(*args, **kwargs)
        channel_jsn = {"satoshis": 9}
        self._channel = UncertaintyChannel(Channel(channel_jsn))

    def test_min_liquidity(self):
        with self.assertRaises(ValueError) as exception:
            self._channel.min_liquidity = -1

        with self.assertRaises(ValueError) as exception:
            self._channel.min_liquidity = self._channel.max_liquidity + 1

        with self.assertRaises(TypeError) as exception:
            self._channel.min_liquidity = "3.4"

        with self.assertRaises(TypeError) as exception:
            self._channel.min_liquidity = 3.4

    def test_max_liquidity(self):
        with self.assertRaises(ValueError) as exception:
            self._channel.max_liquidity = -1

        with self.assertRaises(ValueError) as exception:
            self._channel.max_liquidity = self._channel.min_liquidity - 1

        with self.assertRaises(ValueError) as exception:
            self._channel.max_liquidity = self._channel.capacity + 1

        with self.assertRaises(TypeError) as exception:
            self._channel.max_liquidity = "3.4"

        with self.assertRaises(TypeError) as exception:
            self._channel.max_liquidity = 3.4

    def test_success_probability(self):
        # channel = UncertaintyChannel(Channel(channel_jsn))

        # can't deliver more than capacity
        assert self._channel.success_probability(self._channel.capacity+1) == 0

        # does basic computation work?
        assert self._channel.success_probability(1) == float(9.0/10)

        # do simple conditional conditional probabilities work?
        self._channel.min_liquidity = 2
        assert self._channel.success_probability(1) == 1.0
        assert self._channel.success_probability(2) == 1.0
        assert self._channel.success_probability(3) == float(7.0/8)

        # does in flight consideration work?
        self._channel.min_liquidity = 2
        p = self._channel.success_probability(3)
        self._channel.in_flight = 3
        assert self._channel.success_probability(0) == p

    def test_conditionals(self):
        self._channel.min_liquidity = self._channel.capacity
        with self.assertRaises(ValueError) as exception:
            self._channel.max_liquidity = 0


if __name__ == '__main__':
    unittest.main()
