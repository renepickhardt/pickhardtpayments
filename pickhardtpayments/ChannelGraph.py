import networkx as nx
import json
from .Channel import Channel


class ChannelGraph():
    """
    Represents the public information about the Lightning Network that we see from Gossip and the 
    Bitcoin Blockchain. 

    The channels of the Channel Graph are directed and identified uniquely by a triple consisting of
    (source_node_id, destination_node_id, short_channel_id). This allows the ChannelGraph to also 
    contain parallel channels.
    """

    def _get_channel_json(self, filename: str):
        """
        extracts the dictionary from the file that contains lightnig-cli listchannels json string
        """
        f = open(filename)
        return json.load(f)["channels"]

    def __init__(self, lightning_cli_listchannels_json_file: str):
        """
        Importing the channel_graph from core lightning listchannels command the file can be received by 
        #$ lightning-cli listchannels > listchannels.json

        """

        self._channel_graph = nx.MultiDiGraph()
        channels = self._get_channel_json(lightning_cli_listchannels_json_file)
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
