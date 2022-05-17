import networkx as nx
import json
from .Channel import Channel


class ChannelGraph():
    """
    Represents the public information about the Lightning Network that we see from Gossip and the 
    Bitcoin Blockchain. 

    The channels of the Channel Graph are directed and identiried uniquly by a triple consisting of
    (source_node_id, destination_node_id, short_channel_id). This allows the ChannelGraph to also 
    contain parallel channels.
    """

    def _get_channel_json(self, filename: str, fmt: str = "cln"):
        """
        extracts the dictionary from the file that contains lightnig-cli listchannels json string
        """
        with open(filename) as f:
            channel_graph_json = json.load(f)

        if fmt == "cln":
            return channel_graph_json["channels"]
        elif fmt == "lnd":
            return lnd2cln_json(channel_graph_json["edges"])
        else:
            raise(ValueError("Invalid format. Must be one of ['cln', 'lnd']"))

    def __init__(self, channel_graph_json_file: str, fmt: str = "cln"):
        """
        Importing the channel_graph from c-lightning listchannels command the file can be received by 
        #$ lightning-cli listchannels > listchannels.json

        """

        self._channel_graph = nx.MultiDiGraph()
        channels = self._get_channel_json(channel_graph_json_file, fmt)
        for channel in channels:
            channel = Channel(channel)
            self._channel_graph.add_edge(
                channel.src, channel.dest, key=channel.short_channel_id, channel=channel)

    @property
    def network(self):
        return self._channel_graph

    def get_channel(self, src: str, dest: str, short_channel_id: str):
        """
        returns a specific channel object identified by source, destination and short_channel_id
        from the ChannelGraph
        """
        if self.network.has_edge(src, dest):
            if short_channel_id in self.network[src][dest]:
                return self.network[src][dest][short_channel_id]["channel"]


def lnd2cln_json(channel_graph_json):
    """
    Converts the channel graph json from the LND format to the c-lightning format
    """

    LND_CLN_POLICY_MAP = {
        "time_lock_delta": "delay",
        "min_htlc": "htlc_minimum_msat",
        "fee_base_msat": "base_fee_millisatoshi",
        "fee_rate_milli_msat": "fee_per_millionth",
        "disabled": "active",
        "max_htlc_msat": "htlc_maximum_msat",
        "last_update": "last_update",
    }

    def _add_direction(src, dest, lnd_channel, cln_channel):
        cln_channel["source"] = lnd_channel[src + "_pub"]
        cln_channel["destination"] = lnd_channel[dest + "_pub"]

        src_policy = lnd_channel[src + "_policy"]
        for key in src_policy:
            if key == "disabled":
                cln_channel["active"] = src_policy[key]
            cln_channel[LND_CLN_POLICY_MAP[key]] = int(src_policy[key])

    cln_channel_json = []
    for lnd_channel in channel_graph_json:
        # Common fields for both direction
        cln_channel = {
            "short_channel_id": lnd2cln_channel_id(int(lnd_channel["channel_id"])),
            "satoshis": int(lnd_channel["capacity"]),
            "amount_msat": int(lnd_channel["capacity"]) * 1000,
            "public": None, # Info not available in lnd describegraph?

            # TODO: map features and flags
            "features": '',
            "channel_flags": None,
            "message_flags": None
        }

        # Create channels in the direction(s) in which policies are defined
        if lnd_channel["node1_policy"]:
            _add_direction("node1", "node2", lnd_channel, cln_channel)
            cln_channel_json.append(cln_channel)

        if lnd_channel["node2_policy"]:
            _add_direction("node2", "node1", lnd_channel, cln_channel)
            cln_channel_json.append(cln_channel)

    return cln_channel_json

def lnd2cln_channel_id(lnd_channel_id: int):
    """
    Convert from lnd short channel id to cln short channel id
    """

    # https://bitcoin.stackexchange.com/a/79427
    block = lnd_channel_id >> 40
    tx = lnd_channel_id >> 16 & 0xFFFFFF
    output = lnd_channel_id & 0xFFFF
    return "x".join(map(str, [block, tx, output]))
