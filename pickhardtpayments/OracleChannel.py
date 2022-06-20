from .Channel import Channel

import random


class OracleChannel(Channel):
    """
    An OracleChannel is used in experiments and Simulations to form the (Oracle)LightningNetwork.

    It contains a ground truth about the Liquidity of a channel
    """

    def __init__(self, channel: Channel, actual_liquidity: int = None):
        super().__init__(channel.cln_jsn)
        self._actual_liquidity = actual_liquidity
        if actual_liquidity is None or actual_liquidity >= self.capacity or actual_liquidity < 0:
            self._actual_liquidity = random.randint(0, self.capacity)

    def __str__(self):
        return super().__str__()+" actual Liquidity: {}".format(self.actual_liquidity)

    @property
    def actual_liquidity(self):
        """
        Tells us the actual liquidity according to the oracle. 

        This is useful for experiments but must of course not be used in routing and is also
        not available if mainnet remote channels are being used.
        """
        return self._actual_liquidity

    @actual_liquidity.setter
    def actual_liquidity(self,amt):
        self._actual_liquidity = amt

    
    def can_forward(self, amt: int):
        """
        check if the oracle channel can forward a certain amount
        """
        if amt <= self.actual_liquidity:
            return True
        else:
            return False
