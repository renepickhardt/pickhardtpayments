import logging

from Attempt import Attempt
from .ChannelGraph import ChannelGraph
from .UncertaintyChannel import UncertaintyChannel
from .OracleLightningNetwork import OracleLightningNetwork

import networkx as nx

DEFAULT_BASE_THRESHOLD = 0


class UncertaintyNetwork(ChannelGraph):
    """
    The UncertaintyNetwork is the main data structure to store our belief about the
    Liquidity in the channels of the ChannelGraph.

    Most of its functionality comes from the UncertaintyChannel. Most notably the ability
    to assign a linearized integer uncertainty unit cost to its channels and do this even
    piecewise.

    Paths cannot be probed against the UncertaintyNetwork as it lacks an Oracle
    """

    def __init__(self, channel_graph: ChannelGraph, base_threshold: int = DEFAULT_BASE_THRESHOLD,
                 prune_network: bool = True):
        self._channel_graph = nx.MultiDiGraph()
        for src, dest, keys, channel in channel_graph.network.edges(data="channel", keys=True):
            uncertainty_channel = UncertaintyChannel(channel)
            if channel.base_fee <= base_threshold:
                self._channel_graph.add_edge(uncertainty_channel.src,
                                             uncertainty_channel.dest,
                                             key=uncertainty_channel.short_channel_id,
                                             channel=uncertainty_channel)

        self._prune = prune_network

    @property
    def network(self):
        return self._channel_graph

    @property
    def prune(self):
        return self._prune

    @prune.setter
    def prune(self, value: bool):
        self._prune = value

    def entropy(self):
        """
        computes to total uncertainty in the network summing the entropy of all channels
        """
        return sum(channel.entropy() for src, dest, channel in self.network.edges(data="channel"))

    def reset_uncertainty_network(self):
        """
        resets our belief about the liquidity & inflight information of all channels on the UncertaintyNetwork
        """
        for src, dest, channel in self.network.edges(data="channel"):
            channel.forget_information()

    def activate_network_wide_uncertainty_reduction(self, n, oracle: OracleLightningNetwork):
        """
        With the help of an `OracleLightningNetwork` probes all channels `n` times to reduce uncertainty.

        While one can do this on mainnet by probing we can do this very quickly in simulation
        at virtually no cost. Thus, this API call needs to be taken with caution when using a different
        oracle. 
        """
        for src, dest, channel in self.network.edges(data="channel"):
            channel.learn_n_bits(oracle, n)

    # FIXME: refactor to new code base. The following call will break!
    def activate_foaf_uncertainty_reduction(self, src, dest):
        ego_network = set()
        foaf_network = set()

        out_set = set()
        edges = self.__channel_graph.out_edges(self.__node_key_to_id[src])
        for edge in edges:
            ego_network.add("{}x{}".format(edge[0], edge[1]))
            out_set.add(edge[1])

        for node in out_set:
            edges = self.__channel_graph.out_edges(node)
            for edge in edges:
                foaf_network.add("{}x{}".format(edge[0], edge[1]))

        in_set = set()
        edges = self.__channel_graph.in_edges(self.__node_key_to_id[dest])
        for edge in edges:
            ego_network.add("{}x{}".format(edge[0], edge[1]))
            in_set.add(edge[0])

        for node in in_set:
            edges = self.__channel_graph.out_edges(node)
            for edge in edges:
                foaf_network.add("{}x{}".format(edge[0], edge[1]))

        # print(len(ego_network))
        for k, arc in self.__arcs.items():
            # print(k)
            vals = k.split("x")
            key = "{}x{}".format(vals[0], vals[1])
            if key in ego_network:
                l = arc.get_actual_liquidity()
                arc.update_knowledge(l - 1)
                arc.update_knowledge(l + 1)
                # print(key,arc.entropy())

            if key in foaf_network:
                arc.learn_n_bits(2)
                l = arc.get_actual_liquidity()
                arc.update_knowledge(l - 1)
                arc.update_knowledge(l + 1)
                # print(key, arc.entropy())
        print("channels with full knowledge: ", len(ego_network))
        print("channels with 2 Bits of less entropy: ", len(foaf_network))

    def settle_attempt(self, attempt: Attempt):
        """
        receives a payment attempt and adjusts the balances of the UncertaintyChannels and its reverse channels
        along the path.
        """
        for channel in attempt.path:
            return_channel = self.get_channel(channel.dest,
                                              channel.src,
                                              channel.short_channel_id)

            if channel.min_liquidity < attempt.amount:
                raise ValueError
            channel.min_liquidity = max(0, channel.min_liquidity - attempt.amount)
            if return_channel:
                return_channel.min_liquidity = min(max(return_channel.min_liquidity, attempt.amount), return_channel.capacity)

            channel.max_liquidity = max(channel.max_liquidity - attempt.amount, channel.min_liquidity)
            if return_channel:
                return_channel.max_liquidity = min(return_channel.max_liquidity + attempt.amount,
                                               return_channel.capacity)

        return 0
