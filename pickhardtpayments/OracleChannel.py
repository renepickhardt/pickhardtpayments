import logging

from Channel import Channel
import random


class OracleChannel(Channel):
    """
    An OracleChannel us used in experiments and Simulations to form the (Oracle)LightningNetwork.

    It contains a ground truth about the Liquidity of a channel
    """

    def __init__(self, channel: Channel, actual_liquidity: int = None):
        super().__init__(channel.cln_jsn)
        self._actual_liquidity = actual_liquidity
        self._in_flight = 0
        seed = 64
        random.seed(seed)
        if actual_liquidity is None or actual_liquidity >= self.capacity or actual_liquidity < 0:
            # self._actual_liquidity = 0.5 * self.capacity
            logging.debug("Oracle Channels initialised with seed: {}".format(seed))
            self._actual_liquidity = random.randint(0, self.capacity)

    def __str__(self):
        return super().__str__() + " actual Liquidity: {}".format(self.actual_liquidity)

    @property
    def actual_liquidity(self):
        """
        Tells us the actual liquidity according to the oracle. 

        This is useful for experiments but must of course not be used in routing and is also
        not available if mainnet remote channels are being used.
        """
        return self._actual_liquidity

    @actual_liquidity.setter
    def actual_liquidity(self, amt: int):
        """Sets the liquidity of a channel in the Oracle Network

        :param amt: amount to be assigned to channel liquidity
        :type amt: int
        """
        if 0 <= amt <= self.capacity:
            self._actual_liquidity = amt
        else:
            raise ValueError(
                f"Liquidity for channel {self.short_channel_id} cannot be set. "
                f"Amount {amt} is negative or higher than capacity")

    @property
    def in_flight(self):
        """
        Tells us the actual liquidity according to the oracle.

        This is useful for experiments but must of course not be used in routing and is also
        not available if mainnet remote channels are being used.
        """
        return self._in_flight

    @in_flight.setter
    def in_flight(self, in_flight_amt: int):
        """Sets the liquidity of a channel in the Oracle Network

        :param in_flight_amt: amount to be assigned to channel liquidity
        :type in_flight_amt: int
        """
        if 0 <= in_flight_amt <= self.capacity:
            self._in_flight = in_flight_amt
            logging.debug("in_flight on {}-{} now {:,} ".format(self.src, self.dest, in_flight_amt))
        else:
            raise ValueError(f"inflight amount for channel {self.short_channel_id} cannot be set. "
                             f"Amount {in_flight_amt} is negative or higher than capacity")

    def can_forward(self, amt: int):
        """
        check if the oracle channel can forward a certain amount
        """
        if amt <= self.actual_liquidity:
            return True
        else:
            return False
