import random
import json

#prefix='cost_scaling'
prefix='augmenting_path'
#prefix='ortools'
random.seed(64)

from pickhardtpayments.ChannelGraph import ChannelGraph
from pickhardtpayments.UncertaintyNetwork import UncertaintyNetwork
from pickhardtpayments.OracleLightningNetwork import OracleLightningNetwork
from pickhardtpayments.SyncSimulatedPaymentSession import SyncSimulatedPaymentSession


#we first need to import the chanenl graph from c-lightning jsondump
#you can get your own data set via:
# $: lightning-cli listchannels > listchannels20220412.json
# alternatively you can go to https://ln.rene-pickhardt.de to find a data dump
channel_graph = ChannelGraph("listchannels20220412.json")

uncertainty_network = UncertaintyNetwork(channel_graph)
oracle_lightning_network = OracleLightningNetwork(channel_graph)
#we create ourselves a payment session which in this case operates by sending out the onions
#sequentially 
payment_session = SyncSimulatedPaymentSession(oracle_lightning_network, 
                                 uncertainty_network,
                                 mu = 0,
                                 base = 0,
                                 prune_network=False)

#we need to make sure we forget all learnt information on the Uncertainty Nework

net = uncertainty_network._channel_graph
nodes = net.nodes()
funds = {}
for n in nodes:
    funds[n] = 0

for a,b,d in net.edges(data=True):
    cap = d['channel'].capacity
    funds[a] += cap

# exit(0)

def random_node_pairs(n_pairs,amt):
    list_of_pairs = []
    for i in range(n_pairs):
        while(True):
            a,b = random.sample(nodes,2)
            if min(funds[a],funds[b])>=amt:
                if oracle_lightning_network.theoretical_maximum_payable_amount(a,b,base_fee=0)>=amt:
                    list_of_pairs.append((a,b))
                    break
    return list_of_pairs

#we run the simulation of pickhardt payments and track all the results

n_pairs = 10
amount_list = [ 2**i for i in range(24,25)] 
stat = {}

for a in amount_list:
    stat[a] = { 'time_mcf': [], 'time_total': [], 'nfails': 0 , 'nsuccess': 0 }

# random_node_pairs(n_pairs)

with open(prefix+'.log','w') as flog:
    for amt in amount_list:
        for (A,B) in random_node_pairs(n_pairs,amt):
            print("trying a payment of",amt,"sats from",A,"to",B)
            print("trying a payment of",amt,"sats from",A,"to",B, file=flog)
            payment_session.forget_information()
            try:
                time_mcf,time_total = payment_session.pickhardt_pay(A,B, amt,log_out=flog)
                stat[amt]['time_mcf'].append( time_mcf )
                stat[amt]['time_total'].append( time_total )
                stat[amt]['nsuccess'] += 1
            except:
                stat[amt]['nfails'] +=1
                continue
    
with open(prefix+'.json','w') as f:
    json.dump(stat,f)
