import random
import sys

sys.path.append(r'../pickhardtpayments')
from pickhardtpayments.ChannelGraph import ChannelGraph
from pickhardtpayments.UncertaintyNetwork import UncertaintyNetwork
from pickhardtpayments.OracleLightningNetwork import OracleLightningNetwork
from pickhardtpayments.SyncSimulatedPaymentSession import SyncSimulatedPaymentSession
from pickhardtpayments.SyncPaymentSession import SyncPaymentSession

# we first need to import the chanenl graph from c-lightning jsondump
# you can get your own data set via:
# $: lightning-cli listchannels > listchannels20220412.json
# alternatively you can go to https://ln.rene-pickhardt.de to find a data dump
channel_graph = ChannelGraph("listchannels20220412.json")

uncertainty_network = UncertaintyNetwork(channel_graph)
oracle_lightning_network = OracleLightningNetwork(channel_graph)
# we create ourselves a payment session which in this case operates by sending out payments
# sequentially
sim_session = SyncPaymentSession(oracle_lightning_network,
                                 uncertainty_network,
                                 prune_network=False)

# we need to make sure we forget all learnt information on the Uncertainty Network
sim_session.forget_information()

# we run the simulation of pickhardt payments and track all the results

# TODO randomize payment amount
tested_amount = 10_000_000  # 10 million sats


# sampling two nodes from ChannelGraph
try:
    # casting channel_graph to list to avoid deprecation warning for python 3.9
    sampled_nodes = random.sample(list(channel_graph.network.nodes), 2)
    # TODO how to decide on number of runs?
    for n in range(10):
        # TODO rework pay method to not only onionsend but pay
        sim_session.pickhardt_pay(sampled_nodes[0], sampled_nodes[1], tested_amount, mu=0, base=0)
        # TODO update OracleLightningNetwork to reflect payment (make sure back channel is also updated)
        # TODO decide on method to save

except ValueError:
    print("graph has less than two nodes")
    exit()







