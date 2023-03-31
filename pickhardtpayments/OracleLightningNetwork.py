import logging
import random

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


            if self._network.has_edge(dest, src):
                if short_channel_id in self._network[dest][src]:
                    # channel does not yet exist in Oracle Network but back channel has been created previously
                    # If channel in opposite direction already has been created with liquidity information
                    # match the channel
                    capacity = channel.capacity
                    opposite_channel = self._network[dest][src][short_channel_id]["channel"]
                    opposite_liquidity = opposite_channel.actual_liquidity
                    oracle_channel = OracleChannel(channel, capacity - opposite_liquidity)

            if oracle_channel is None:
                # channel does not yet exist in Oracle Network, no back channel has been created yet
                random.seed(12345678)
                liquidity = random.randint(0, channel.capacity)
                oracle_channel = OracleChannel(channel, liquidity)
                # oracle_channel = OracleChannel(channel)


            self._network.add_edge(oracle_channel.src,
                                   oracle_channel.dest,
                                   key=short_channel_id,
                                   channel=oracle_channel)

        # self.remove_channels_with_no_return_channels()


    @property
    def network(self):
        return self._network

    def allocate_amount_as_inflight_on_path(self, attempt: Attempt):
        """
        allocates `amt` as in_flights to all channels of the path
        """
        for uncertainty_channel in attempt.path:
            oracle_channel = self.get_channel(uncertainty_channel.src, uncertainty_channel.dest,
                                              uncertainty_channel.short_channel_id)
            oracle_channel.in_flight += attempt.amount

    def send_onion(self, attempt: Attempt):
        """
        Probes the oracle network if the amount of satoshis for this attempt can be sent through the given path in
        the attempt.
        If successful, then inflight amounts are placed on the respective oracle channels as well as uncertainty
        channels, and the Attempt is set to INFLIGHT.
        If not successful, then the status of the Attempt is set to FAILED and the failing channel is returned

        :param attempt: the attempt that is probed
        :type: Attempt

        :return: did sending the onion succeed?
        :rtype: Boolean
        :return: if sending the onion failed, at which channel did it fail
        :rtype: UncertaintyChannel or None
        """
        for uncertainty_channel in attempt.path:
            oracle_channel = self.get_channel(uncertainty_channel.src, uncertainty_channel.dest,
                                              uncertainty_channel.short_channel_id)
            # probing for current amount in addition to current in_flights in oracle network
            success_of_probe = oracle_channel.can_forward(oracle_channel.in_flight + attempt.amount)
            if success_of_probe:
                # replicate HTLCs on the OracleChannels and place inflights in Uncertainty Network
                logging.debug("allocating {:,} on channel".format(attempt.amount))
                oracle_channel.in_flight += attempt.amount
                uncertainty_channel.allocate_inflights(attempt.amount)
            if not success_of_probe:
                logging.debug("{:,} sats failed on channel {}-{} with actual liquidity of {:,} sats (cap: {:,})".
                             format((oracle_channel.in_flight + attempt.amount), oracle_channel.src[0:4],
                                    oracle_channel.dest[0:4], oracle_channel.actual_liquidity, oracle_channel.capacity))
                attempt.status = AttemptStatus.FAILED
                logging.debug(f"Attempt status: {attempt}")
                return False, uncertainty_channel

        # setting AttemptStatus from PLANNED to INFLIGHT does not change in_flight amounts
        attempt.status = AttemptStatus.INFLIGHT
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

    def settle_attempt(self, attempt: Attempt):
        """
        receives a payment attempt and adjusts the balances of the OracleChannels and its reverse channels
        along the path.

        settle_attempt should only be called after all send_onions for a payment terminated successfully!
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

    def remove_channels_with_no_return_channels(self):
        ebunch = []
        for edge in self.network.edges:
            return_edge = self.get_channel(edge[1], edge[0], edge[2])
            if not return_edge:
                ebunch.append((edge[0], edge[1], edge[2]))
        print("edges before:", len(self.network.edges))
        self.network.remove_edges_from(ebunch)
        print("edges after:", len(self.network.edges))
        if len(ebunch) == 0:
            logging.info("channel graph only had channels in both directions.")
        else:
            logging.info(f"channel graph had {len(ebunch)} unannounced channels.")
        return self