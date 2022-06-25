import networkx as nx
import json
from .Channel import Channel, ChannelFields


class ChannelGraph:
    """
    Represents the public information about the Lightning Network that we see from Gossip and the 
    Bitcoin Blockchain. 

    The channels of the Channel Graph are directed and identified uniquely by a triple consisting of
    (source_node_id, destination_node_id, short_channel_id). This allows the ChannelGraph to also 
    contain parallel channels.
    """

    def _get_channel_json(self, filename: str, fmt: str = "cln"):
        """
        extracts the dictionary from the file that contains lightning-cli listchannels json string
        """
        with open(filename) as f:
            channel_graph_json = json.load(f)

        if fmt == "cln":
            return channel_graph_json["channels"]
        elif fmt == "lnd":
            return lnd2cln_json(channel_graph_json)
        else:
            raise(ValueError("Invalid format. Must be one of ['cln', 'lnd']"))

    def __init__(self, channel_graph_json_file: str, fmt: str = "cln"):
        """
        Importing the channel_graph from core lightning listchannels command the file can be received by 
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

    # Maps LND keys to CLN keys
    LND_CLN_POLICY_MAP = {
        "time_lock_delta": ChannelFields.CLTV,
        "min_htlc": ChannelFields.HTLC_MINIMUM_MSAT,
        "fee_base_msat": ChannelFields.BASE_FEE_MSAT,
        "fee_rate_milli_msat": ChannelFields.FEE_RATE,
        "disabled": ChannelFields.ACTIVE,
        "max_htlc_msat": ChannelFields.HTLC_MAXIMUM_MSAT,
        "last_update": ChannelFields.LAST_UPDATE,
    }

    def _add_direction(src, dest, lnd_channel, cln_channel):
        cln_channel[ChannelFields.SRC] = lnd_channel[src + "_pub"]
        cln_channel[ChannelFields.DEST] = lnd_channel[dest + "_pub"]

        src_policy = lnd_channel[src + "_policy"]
        for key in src_policy:
            val = int(src_policy[key]) if key != "disabled" else src_policy[key]
            cln_channel[LND_CLN_POLICY_MAP[key]] = val

    node_features = {node["pub_key"]: node["features"] for node in channel_graph_json["nodes"]}
    channels_list = channel_graph_json["edges"]
    cln_channel_json = []
    for lnd_channel in channels_list:
        # Common fields for both direction
        cln_channel = {
            ChannelFields.SHORT_CHANNEL_ID: bolt_short_channel_id(int(lnd_channel["channel_id"])),
            ChannelFields.CAP: int(lnd_channel["capacity"]),
            ChannelFields.ANNOUNCED: True,
            "amount_msat": int(lnd_channel["capacity"]) * 1000,

            # Not supporting flags
            "channel_flags": None,
            "message_flags": None
        }

        # Create channels in the direction(s) in which policies are defined
        for (src, dest) in {"node1": "node2", "node2": "node1"}.items():
            if lnd_channel[src + "_policy"]:
                _add_direction(src, dest, lnd_channel, cln_channel)
                features = node_features[lnd_channel[src + "_pub"]]
                cln_channel[ChannelFields.FEATURES] = to_feature_hex(features)
                cln_channel_json.append(cln_channel)

    return cln_channel_json

def bolt_short_channel_id(lnd_channel_id: int):
    """
    Convert from LND short channel id to BOLT short channel id.
    Ref: https://bitcoin.stackexchange.com/a/79427
    """

    block = lnd_channel_id >> 40
    tx = lnd_channel_id >> 16 & 0xFFFFFF
    output = lnd_channel_id & 0xFFFF
    return "x".join(map(str, [block, tx, output]))

def to_feature_hex(features: dict):
    d = 0
    for feature_bit in features.keys():
        # Ignore non-bolt feature bits
        if (b := int(feature_bit)) <= 49:
            d |= (1 << b)

    return f'0{d:x}'