"""
WARNING!!! very experimental work in progress! Only use with caution and wait for the proper release

The DijkstraOverPayment class aims to find Dijkstra paths in a pragmatic way for redundant overpayments. 
In particular it is a proof of concept to generate an MPP-Split in an ad hoc way that seems to be more 
resonable than existing splitters which either do devide an conquorer or split to a certain amount or split
to a predefined number of parts. 
This splitter finds low cost paths and greedly allocates as many sats as long as the reliability stays abvove a threshold

The main ideas are the following: 

## With respect to the cost function for candidate selection:

We use dijkstra to compute candidate paths as shortest paths with respect to our cost function

1.) Use a cost function for a unit that is the combination of linearized routing and linearized uncertainty cost
2.) smooth the routing cost (currently lapalace smoothing with +100 exact value needs to be found
3.) cost = (ppm + 100) * 1/capacity
4.) after a path is planned increase cost of each edge with a multiplier

## with respect to allocation of funds to paths

The cost function favors paths with low routing costs thus the only question is how many sats to allocate? 
The following idea shall be used for motivation: 

* We want each path to have a success probability of at least x%
* Thus let `l` be the length of the planned path and `c` be the capacity of the smallest channel.
* Then `s = (c+1-a)/(c+1)` is the success probability for the allocated amount `a` 
* We require `s >= x ** (1/l)` which means the path has a probability of at least `x`
* For now we ignore prior knowledge and believe (Thus one reason for this to be WIP)
* knowing `s` at equality we solve for `a` --> a = (c+1) - s*(c+1) = (c+1)*(1-s)
* we allocate `a` sats to the candidate path

## Number of generated / planned candidate paths

* for each path we compute it's expected value of delivered sats as its actual success probability mutitplied by the allocated sats
* As the expected value is linear we generate paths until the sum of the EVs is larger than our target total EV
* the target total EV is the amount we wish to deliver (e.g. given by an invoice) multiplied with a reliability factor (>= 1.0)


## known short commings:
* subset of generated paths does not add to payment amount
* base fee is ignored
* learnt knowledge is ignored
* magic numbers are hard coded and not configureable (requires refactoring of the lib)
* output / api fits more to MCF approach
* handeling of edge cases
* assumes uniform distribution (which is actually easily fixable)

"""
from .Payment import Payment
from .Attempt import Attempt, AttemptStatus
from .UncertaintyNetwork import UncertaintyNetwork
from .OracleLightningNetwork import OracleLightningNetwork
from math import log2 as log

import time
from typing import List
import networkx as nx

import logging
from logging import Logger
import sys

# logger = logging.getLogger(__name__)
logger: Logger = logging.getLogger()
# formatter = logging.Formatter('%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
# stdout_handler.setFormatter(formatter)
file_handler = logging.FileHandler('redundant_pickhardt_pay.log', mode='a')
file_handler.setLevel(logging.DEBUG)
# file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class DijkstraOverPayment(Payment):

    def __init__(self, uncertainty_network: UncertaintyNetwork, oracle_network: OracleLightningNetwork, sender,
                 receiver, total_amount: int, mu: int, base: int):
        """Constructor method
        """
        self._successful = False
        self._ppm = None
        self._start_time = time.time()
        self._end_time = None
        self._sender = sender
        self._receiver = receiver
        self._total_amount = total_amount
        self._residual_amount = total_amount
        self._attempts = list()
        self._uncertainty_network = uncertainty_network
        self._oracle_network = oracle_network
        self._prepare_integer_indices_for_nodes()
        self._mu = mu
        self._base = base
        self._pickhardt_payment_rounds = 0
        self._uncertainty_network_entropy = self._uncertainty_network.entropy()

    def _make_flow_network(self, f=1):
        self._residual_network = nx.MultiDiGraph()
        for s, d, channel in self._uncertainty_network.network.edges(data="channel"):
            c = channel.conditional_capacity

            if f < channel.capacity + 1:
                self._residual_network.add_edge(
                    s, d, cost=(channel.ppm+100)/(channel.conditional_capacity), key=channel.short_channel_id, channel=channel)

    def _next_hop(self, path):
        """
        generator to iterate through edges indexed by node id of paths

        The path is a list of node ids. Each call returns a tuple src, dest of an edge in the path
        """
        for i in range(1, len(path)):
            src = path[i - 1]
            dest = path[i]
            yield src, dest

    def _make_channel_path(self, path: List[str]) -> object:
        """
        network x returns a path as a list of node_ids. However, we need a list of `UncertaintyChannels`
        Since the graph has parallel edges it is quite some work to get the actual channels that the
        min cost flow solver produced
        """
        channel_path = []
        for src, dest in self._next_hop(path):
            w = 2 ** 63
            c = None
            flow = 0
            for sid in self._residual_network[src][dest].keys():
                if self._residual_network[src][dest][sid]["cost"] < w:
                    w = self._residual_network[src][dest][sid]["cost"]
                    c = self._residual_network[src][dest][sid]["channel"]
            channel_path.append(c)
        return channel_path

    def _generate_candidate_paths(self):
        logger.debug("Amount to send: {}".format(self._total_amount))
        # FIXME: remove magic number
        reliability_buffer = 1.3
        # FIXME: remove magic number
        min_probability = 0.8
        # First we prepare the min cost flow by getting arcs from the uncertainty network
        self._make_flow_network()
        self._start_time = time.time()
        logger.debug("run the dijkstra overpayer...")
        ev = 0
        cnt = 0
        total_amount = 0
        attempts = []
        while True:
            path = nx.shortest_path(
                self._residual_network, self._sender, self._receiver, weight="cost")
            channel_path = self._make_channel_path(path)

            min_conditional_capacity = min(
                chan.conditional_capacity for chan in channel_path)
            p = min_probability**(1.0/len(path))
            amt = int(min_conditional_capacity - p * min_conditional_capacity)
            total_amount += amt
            channel_path = self._make_channel_path(path)

            for channel in channel_path:
                # FIXME: remove magic number
                self._residual_network[channel.src][channel.dest][channel.short_channel_id]["cost"] *= 1.2

            attempt = Attempt(channel_path, amt)
            attempts.append(attempt)

            p = attempt.probability
            ev += int(p*amt)
            logger.info("Path #{:2} with {:2} hops and min conditional capacity of {:10} sats alloc: {:10} sats".format(
                cnt+1, len(path), min_conditional_capacity, int(amt)))

            cnt += 1
            if ev > self.total_amount * reliability_buffer:
                break

        print("to sent {} sats we sent {} onions with a total liquidity of {} and expect to deliver: {:5.3f}".format(
            self.total_amount, cnt, total_amount, ev))
        print("This is an overpayment of {:4.2f}\n\n".format(total_amount/ev))

        self._end_time = time.time()
        self.register_candidate_paths(attempts)
        return self._end_time - self._start_time

    def get_summary(self):
        logger.info("SUMMARY:")
        logger.info("========")
        settled = sum(a.amount for a in self.filter_attempts(
            AttemptStatus.SETTLED))
        failed = sum(a.amount for a in self.filter_attempts(
            AttemptStatus.FAILED))
        logger.info(
            "Rounds of MCF-computations:\t{:3}".format(self.pickhardt_payment_rounds))
        logger.info("Settled {} sats and failed {} sats. fraction of settled liquidity {:4.2f}%".format(
            settled, failed, (100.0*settled)/(settled+failed)))
        # logger.info(
        #    "Rounds of MEVF-computations:\t{:3}".format(self.pickhardt_payment_rounds))
        logger.info("Number of attempts made:\t\t{:3}".format(
            len(self.attempts)))
        logger.info("Number of failed attempts:\t{:3}".format(
            len(list(self.filter_attempts(AttemptStatus.FAILED)))))
        logger.info("Failure rate: {:4.2f}% ".format(
            len(list(self.filter_attempts(AttemptStatus.FAILED))) * 100. / len(self.attempts)))
        logger.info("total Payment lifetime (including inefficient memory management): {:4.3f} sec".format(
            self.life_time))
        logger.info("Learnt entropy: {:5.2f} bits".format(
            self.uncertainty_network_entropy_delta))
        logger.info("fee for settlement of delivery: {:8.3f} sat --> {} ppm".format(
            self.settlement_fees / 1000, int(self.settlement_fees * 1000 / self.total_amount)))
        logger.info("used mu: %s", self._mu)
        logger.info("Payment was successful: %s", self.successful)
