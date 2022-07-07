import logging

from Attempt import Attempt, AttemptStatus
from ChannelGraph import ChannelGraph
from OracleChannel import OracleChannel
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

    def allocate_in_flight_on_path(self, attempt: Attempt):
        """
        allocates `amt` as in_flights to all channels of the path
        """
        for channel in attempt.path:
            ch = self.get_channel(channel.src, channel.dest, channel.short_channel_id)
            ch.in_flight += attempt.amount

    def send_onion(self, attempt: Attempt):
        """
        :rtype: object
        """
        for channel in attempt.path:
            oracle_channel = self.get_channel(channel.src, channel.dest, channel.short_channel_id)
            # probing for current amount in addition to current in_flights
            success_of_probe = oracle_channel.can_forward(channel.in_flight + attempt.amount)
            # updating knowledge about the probed amount (amount PLUS in_flight)
            channel.update_knowledge(channel.in_flight + attempt.amount, success_of_probe)
            if not success_of_probe:
                logging.debug(f"failed channel {oracle_channel.short_channel_id}")

                # Status change on attempt to FAILED removes in_flights from UncertaintyChannels in path
                attempt.status = AttemptStatus.FAILED
                logging.debug(f"Attempt status: {attempt}")
                return False, channel

        # setting AttemptStatus from PLANNED to INFLIGHT does not adjust ANY in_flight amounts
        attempt.status = AttemptStatus.INFLIGHT

        # in_flight amounts in UncertaintyNetwork have been placed when calling _min_cost_flow.Solve()
        # channel balances in UncertaintyNetwork have been adjusted when getting result from send_onion
        # so on further adjustment necessary in UncertaintyNetwork

        # replicate HTLCs on the Channels
        # self.oracle_network.allocate_in_flight_on_path(attempt)
        self.allocate_in_flight_on_path(attempt)

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

    def settle_payment(self, attempt: Attempt):
        """
        receives a payment attempt and adjusts the balances of the OracleChannels and its reverse channels
        along the path.

        settle_payment should only be called after all send_onions for a payment terminated successfully!
        """
        for channel in attempt.path:
            settlement_channel = self.get_channel(channel.src, channel.dest, channel.short_channel_id)
            return_settlement_channel = self.get_channel(channel.dest, channel.src, channel.short_channel_id)
            if settlement_channel.actual_liquidity > attempt.amount:
                # decrease channel balance in sending channel by amount
                settlement_channel.actual_liquidity = settlement_channel.actual_liquidity - attempt.amount
                # remove in_flight amount
                settlement_channel.in_flight -= attempt.amount
                # increase channel balance in the other direction by amount
                if return_settlement_channel:
                    return_settlement_channel.actual_liquidity = return_settlement_channel.actual_liquidity \
                                                                 + attempt.amount
            else:
                raise Exception("""Channel liquidity on Channel {} is lower than payment amount.
                    \nPayment cannot settle.""".format(channel.short_channel_id))
        return 0
