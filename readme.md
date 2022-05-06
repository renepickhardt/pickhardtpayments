# Pickhardt Payments Package

The `pickhardtpayments` package is a collection of classes and interfaces that help you to test and implement your dialect of [Pickhardt Payments](https://ln.rene-pickhardt.de#PickhardtPayments) into your on Lightning Application.

## What are Pickhardt Payments?

Pickhardt Payments are the method of deliverying satoshis from on Lightning network Node to another by using [probabilistic payment delivery](https://arxiv.org/abs/2103.08576) in a round based `payment loop` that updeates our `belief` of the remote `liquidity` in the `Uncertainty Network` and generates [optimally reliable and cheap payment flows](https://arxiv.org/abs/2107.05322) in every round by solving a [piece wise linearized min integer cost flow problem](https://github.com/renepickhardt/mpp-splitter/blob/pickhardt-payments-simulation-dev/Minimal%20Linearized%20min%20cost%20flow%20example%20for%20MPP.ipynb) with a seperable cost function.

As of now the two main features of the cost function are the `linearized_uncertainty_unit_cost` (effectively proportional to `1/channel_capacity`) and the `linearized_routing_unit_cost` (effectivly just the `ppm`).

## Depenencies

For simplicity the library currently uses a min cost flow solver from google's `ortools` and internally it stores all graphs and networks in `networkx`.
I do not recommend writing critical in production or enterprise software on top of `networkx` as the library is rather slow and has a huge overhead of handling memory.

The dependencies can be found at:

* https://github.com/networkx
* https://github.com/google/or-tools

## build and install

Onestep install is via pip by typing `pip install pickhardtpayments` to your command line

If you want to build and install the library yourself you can do:

```
git clone https://github.com/renepickhardt/pickhardtpayments.git
cd pickhardtpayments
python -m build
pip install -e .
```

## Example Code

This is a very stripped down example that shows how to run the library.
Have a look at the example folder to find a longer version and more examples for the future

```
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
                                 prune_network=False)

#we need to make sure we forget all learnt information on the Uncertainty Nework
payment_session.forget_information()

#we run the simulation of pickhardt payments and track all the results

#Rene Pickhardt's public node key
RENE = "03efccf2c383d7bf340da9a3f02e2c23104a0e4fe8ac1a880c8e2dc92fbdacd9df"
#Carsten Otto's public node key
C_OTTO = "027ce055380348d7812d2ae7745701c9f93e70c1adeb2657f053f91df4f2843c71"
tested_amount = 10_000_000 #10 million sats

payment_session.pickhardt_pay(RENE,C_OTTO, tested_amount,mu=0,base=0)
```

## Acknowledgements & Funding
This work is funded via various sources including [NTNU](https://www.ntnu.no/) & [BitMEX](https://blog.bitmex.com/bitmex-2021-open-source-developer-grants/) as well as many generous donors via https://donate.ln.rene-pickhardt.de or https://www.patreon.com/renepickhardt Feel free to go to my website at https://ln.rene-pickhardt.de to learn how I have been contributing to the open source community and why it is important to have independent open source contributors. In case you also wish to support me I will be very grateful
