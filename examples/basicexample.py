from pickhardtpayments.ChannelGraph import ChannelGraph
from pickhardtpayments.UncertaintyNetwork import UncertaintyNetwork
from pickhardtpayments.OracleLightningNetwork import OracleLightningNetwork
from pickhardtpayments.SyncSimulatedPaymentSession import SyncSimulatedPaymentSession


#we first need to import the channel graph from core lightning jsondump
#you can get your own data set via:
# $: lightning-cli listchannels > listchannels20220412.json
# alternatively you can go to https://ln.rene-pickhardt.de to find a data dump
channel_graph = ChannelGraph("listchannels20220412.json")

uncertainty_network = UncertaintyNetwork(channel_graph)
oracle_lightning_network = OracleLightningNetwork(channel_graph)
#we create a payment session which in this case operates by sending out the onions
#sequentially 
payment_session = SyncSimulatedPaymentSession(oracle_lightning_network, 
                                 uncertainty_network,
                                 prune_network=False)

#we need to make sure we forget all learnt information on the Uncertainty Nework
payment_session.forget_information()

#we run the simulation of pickhardt payments and track all the results

#Rene Pickhardt's public node key
RENE = "03efccf2c383d7bf340da9a3f02e2c23104a0e4fe8ac1a880c8e2dc92fbdacd9df"
#Carsten Otto's public node key
C_OTTO = "027ce055380348d7812d2ae7745701c9f93e70c1adeb2657f053f91df4f2843c71"
tested_amount = 10_000_000 #10 million sats

payment_session.pickhardt_pay(RENE, C_OTTO, tested_amount, mu=0, base=0)
