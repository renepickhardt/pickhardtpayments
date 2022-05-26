from typing import List

from pickhardtpayments.ChannelGraph import ChannelGraph
from pickhardtpayments.OracleChannel import OracleChannel
import networkx as nx

DEFAULT_BASE_THRESHOLD = 0


class OracleLightningNetwork(ChannelGraph):

    def __init__(self, channel_graph: ChannelGraph):
        self._channel_graph = channel_graph
        self._network = nx.MultiDiGraph()
        for src, dest, short_channel_id, channel in channel_graph.network.edges(data="channel", keys=True):
            oracle_channel = None

            # If Channel in opposite direction already exists with liquidity information match the channel
            if self._network.has_edge(dest, src):
                if short_channel_id in self._network[dest][src]:
                    capacity = channel.capacity
                    opposite_channel = self._network[dest][src][short_channel_id]["channel"]
                    opposite_liquidity = opposite_channel.actual_liquidity
                    oracle_channel = OracleChannel(
                        channel, capacity - opposite_liquidity)

            if oracle_channel is None:
                oracle_channel = OracleChannel(channel)

            self._network.add_edge(oracle_channel.src,
                                   oracle_channel.dest,
                                   key=short_channel_id,
                                   channel=oracle_channel)

    @property
    def network(self):
        return self._network

    def send_onion(self, path, amt):
        """

        :rtype: object
        """
        for channel in path:
            oracle_channel = self.get_channel(
                channel.src, channel.dest, channel.short_channel_id)
            success_of_probe = oracle_channel.can_forward(
                channel.in_flight + amt)
            # print(channel,amt,success_of_probe)
            channel.update_knowledge(amt, success_of_probe)
            if not success_of_probe:
                return False, channel
        return True, None

    def theoretical_maximum_payable_amount(self, source: str, destination: str, base_fee: int = DEFAULT_BASE_THRESHOLD):
        """
        Uses the information from the oracle to compute the min-cut between source and destination

        This is only useful for experiments and simulations if one wants to know what would be 
        possible to actually send before starting the payment loop
        """
        test_network = nx.DiGraph()
        for src, dest, channel in self.network.edges(data="channel"):
            # liquidity = 0
            # for channel in channels:
            if channel.base_fee > base_fee:
                continue
            liquidity = self.get_channel(
                src, dest, channel.short_channel_id).actual_liquidity
            if liquidity > 0:
                if test_network.has_edge(src, dest):
                    test_network[src][dest]["capacity"] += liquidity
                else:
                    test_network.add_edge(src,
                                          dest,
                                          capacity=liquidity)

        mincut, _ = nx.minimum_cut(test_network, source, destination)
        return mincut

    def settle_payment(self, path: List[OracleChannel], payment_amount: int):
        """
        receives a dictionary with channels and payment amounts and adjusts the balances of the channels along the path.

        settle_payment should only be called after all send_onions for a payment terminated successfully!
        # TODO testing
        """
        for channel in path:
            settlement_channel = self.get_channel(channel.src, channel.dest, channel.short_channel_id)
            return_settlement_channel = self.get_channel(channel.dest, channel.src, channel.short_channel_id)
            if settlement_channel.actual_liquidity > payment_amount:
                # decrease channel balance in sending channel by amount
                settlement_channel.actual_liquidity = settlement_channel.actual_liquidity - payment_amount
                # increase channel balance in the other direction by amount
                return_settlement_channel.actual_liquidity = return_settlement_channel.actual_liquidity + payment_amount
            else:
                raise Exception("""Channel liquidity on Channel {} is lower than payment amount.
                    \nPayment cannot settle.""".format(channel.short_channel_id))
        return 0
