import time
from typing import List

from ortools.graph import pywrapgraph
import networkx as nx

from .UncertaintyNetwork import UncertaintyNetwork
from .OracleLightningNetwork import OracleLightningNetwork
from .Attempt import Attempt, AttemptStatus


class Payment:
    """
    Payment stores the information about an amount of sats to be delivered from source to destination.

    When sending an amount of sats from sender to receiver, a payment is usually split up and sent across
    several paths, to increase the probability of being successfully delivered.
    The PaymentClass holds all necessary information about a payment.
    It also holds information that helps to calculate performance statistics about the payment.

    :param sender: sender address for the payment
    :type sender: class:`str`
    :param receiver: receiver address for the payment
    :type receiver: class:`str`
    :param total_amount: The total amount of sats to be delivered from source address to destination address.
    :type total_amount: class:`int`
    """

    def __init__(self, uncertainty_network: UncertaintyNetwork, oracle_network: OracleLightningNetwork, sender,
                 receiver, total_amount: int = 1):
        """Constructor method
        """
        self._successful = False
        self._ppm = None
        self._fee = None
        self._start_time = time.time()
        self._end_time = None
        self._sender = sender
        self._receiver = receiver
        self._total_amount = total_amount
        self._attempts = list()
        self._uncertainty_network = uncertainty_network
        self._oracle_network = oracle_network
        self._prepare_integer_indices_for_nodes()

    def __str__(self):
        return "Payment with {} attempts to deliver {} sats from {} to {}".format(len(self._attempts),
                                                                                  self._total_amount,
                                                                                  self._sender[-8:],
                                                                                  self._receiver[-8:])

    @property
    def sender(self) -> str:
        """Returns the address of the sender of the payment.

        :return: sender address for the payment
        :rtype: str
        """
        return self._sender

    @property
    def receiver(self) -> str:
        """Returns the address of the receiver of the payment.

        :return: receiver address for the payment
        :rtype: str
        """
        return self._receiver

    @property
    def total_amount(self) -> int:
        """Returns the amount to be sent with this payment.

        :return: The total amount of sats to be delivered from source address to destination address.
        :rtype: int
        """
        return self._total_amount

    @property
    def start_time(self) -> float:
        """Returns the time when Payment object was instantiated.

        :return: time in seconds from epoch to instantiation of Payment object.
        :rtype: float
        """
        return self._start_time

    @property
    def end_time(self) -> float:
        """Time when payment was finished, either by being aborted or by successful settlement

        Returns the time when all Attempts in Payment did settle or fail.

        :return: time in seconds from epoch to successful payment or failure of payment.
        :rtype: float
        """
        return self._end_time

    @end_time.setter
    def end_time(self, timestamp):
        """Set time when payment was finished, either by being aborted or by successful settlement

        Sets end_time time in seconds from epoch. Should be called when the Payment failed or when Payment
        settled successfully.

        :param timestamp: time in seconds from epoch
        :type timestamp: float
        """
        self._end_time = timestamp

    @property
    def attempts(self) -> List[Attempt]:
        """Returns all onions that were built and are associated with this Payment.

        :return: A list of Attempts of this payment.
        :rtype: list[Attempt]
        """
        return self._attempts

    def add_attempts(self, attempts: List[Attempt]):
        """Adds Attempts (onions) that have been made to settle the Payment to the Payment object.

        :param attempts: a list of attempts that belong to this Payment
        :type: list[Attempt]
        """
        self._attempts.extend(attempts)

    @property
    def settlement_fees(self) -> float:
        """Returns the fees that accrued for this payment. It's the sum of the routing fees of all settled onions.

        :return: fee in sats for successful attempts of Payment
        :rtype: float
        """
        settlement_fees = 0
        for attempt in self.filter_attempts(AttemptStatus.SETTLED):
            settlement_fees += attempt.routing_fee
        return settlement_fees

    @property
    def arrived_fees(self) -> float:
        """Returns the fees for all Attempts/onions for this payment, that arrived but have not yet been settled.

        It's the sum of the routing fees of all arrived attempts.

        :return: fee in sats for arrived attempts of Payment
        :rtype: float
        """
        planned_fees = 0
        for attempt in self.filter_attempts(AttemptStatus.ARRIVED):
            planned_fees += attempt.routing_fee
        return planned_fees

    @property
    def ppm(self) -> float:
        """Returns the fees that accrued for this payment. It's the sum of the routing fees of all settled onions.

        :return: fee in ppm for successful delivery and settlement of payment
        :rtype: float
        """
        return self._fee * 1000 / self.total_amount

    def filter_attempts(self, flag: AttemptStatus) -> List[Attempt]:
        """Returns all onions with the given state.

        :param flag: the state of the attempts that should be filtered for
        :type: Attempt.AttemptStatus

        :return: A list of successful Attempts of this Payment, which could be settled.
        :rtype: list[Attempt]
        """
        for attempt in self._attempts:
            if attempt.status.value == flag.value:
                yield attempt

    @property
    def successful(self) -> bool:
        """Returns True if the total_amount of the payment could be delivered successfully.

        :return: True if Payment settled successfully, else False.
        :rtype: bool
        """
        return self._successful

    @successful.setter
    def successful(self, value):
        """Sets flag if all inflight attempts of the payment could settle successfully.

        :param value: True if Payment settled successfully, else False.
        :type: bool
        """
        self._successful = value

    def _prepare_integer_indices_for_nodes(self):
        """
        necessary for the OR-lib by google and the min cost flow solver

        let's initialize the look-up tables for node_ids to integers from [0,...,#number of nodes]
        this is necessary because of the API of the Google Operations Research min cost flow solver
        """
        self._mcf_id = {}
        self._node_key = {}
        for k, node_id in enumerate(self._uncertainty_network.network.nodes()):
            self._mcf_id[node_id] = k
            self._node_key[k] = node_id

    def generate_candidate_paths(self, mu: int, base: int):
        """
        computes the optimal payment split to deliver `amt` from `src` to `dest` and updates our belief about the
        liquidity

        This is one step within the payment loop.

        Returns the residual amount of the `amt` that could ne be delivered and the paid fees
        (on a per channel base not including fees for downstream fees) for the delivered amount

        the function also prints some results on statistics about the paths of the flow to stdout.
        """
        # initialisation of List of Attempts for this round.
        attempts_in_round = List[Attempt]

        # First we prepare the min cost flow by getting arcs from the uncertainty network
        self._prepare_mcf_solver(mu, base)
        self._start_time = time.time()
        # print("solving mcf...")
        status = self._min_cost_flow.Solve()

        if status != self._min_cost_flow.OPTIMAL:
            print('There was an issue with the min cost flow input.')
            print(f'Status: {status}')
            exit(1)

        attempts_in_round = self._dissect_flow_to_paths(self._sender, self._receiver)
        self._end_time = time.time()
        self.add_attempts(attempts_in_round)
        return 0

    def _prepare_mcf_solver(self, mu: int, base_fee: int):
        """
        computes the uncertainty network given our prior belief and prepares the min cost flow solver

        This function can define a value for mu to control how heavily we combine the uncertainty cost and fees Also
        the function supports only taking channels into account that don't charge a base_fee higher or equal to `base`

        returns the instantiated min_cost_flow object from the Google OR-lib that contains the piecewise linearized
        problem
        """
        self._min_cost_flow = pywrapgraph.SimpleMinCostFlow()
        self._arc_to_channel = {}

        for s, d, channel in self._uncertainty_network.network.edges(data="channel"):
            # ignore channels with too large base fee
            if channel.base_fee > base_fee:
                continue
            # FIXME: Remove Magic Number for pruning
            # Prune channels away that have too low success probability! This is a huge runtime boost
            # However the pruning would be much better to work on quantiles of normalized cost
            # So as soon as we have better Scaling, Centralization and feature engineering we can
            # probably have a more focused pruning
            if self._uncertainty_network.prune and channel.success_probability(250_000) < 0.9:
                continue
            cnt = 0
            # QUANTIZATION):
            for capacity, cost in channel.get_piecewise_linearized_costs(mu=mu):
                index = self._min_cost_flow.AddArcWithCapacityAndUnitCost(self._mcf_id[s],
                                                                          self._mcf_id[d],
                                                                          capacity,
                                                                          cost)
                self._arc_to_channel[index] = (s, d, channel, 0)
                if self._uncertainty_network.prune and cnt > 1:
                    break
                cnt += 1

        # Add node supply to 0 for all nodes
        for i in self._uncertainty_network.network.nodes():
            self._min_cost_flow.SetNodeSupply(self._mcf_id[i], 0)

        # add amount to sending node
        self._min_cost_flow.SetNodeSupply(
            self._mcf_id[self._sender], int(self._total_amount))  # /QUANTIZATION))

        # add -amount to recipient nods
        self._min_cost_flow.SetNodeSupply(
            self._mcf_id[self._receiver], -int(self._total_amount))  # /QUANTIZATION))

    def _make_channel_path(self, G: nx.MultiDiGraph, path: List[str]) -> object:
        """
        network x returns a path as a list of node_ids. However, we need a list of `UncertaintyChannels`
        Since the graph has parallel edges it is quite some work to get the actual channels that the
        min cost flow solver produced
        """
        channel_path = []
        bottleneck = 2 ** 63
        for src, dest in self._next_hop(path):
            w = 2 ** 63
            c = None
            flow = 0
            for sid in G[src][dest].keys():
                if G[src][dest][sid]["weight"] < w:
                    w = G[src][dest][sid]["weight"]
                    c = G[src][dest][sid]["channel"]
                    flow = G[src][dest][sid]["flow"]
            channel_path.append(c)

            if flow < bottleneck:
                bottleneck = flow

        return channel_path, bottleneck

    def _dissect_flow_to_paths(self, s, d):
        """
        A standard algorithm to dissect a flow into several paths.


        FIXME: Note that this dissection while accurate is probably not optimal in practice.
        As noted in our Probabilistic payment delivery paper the payment process is a bernoulli trial
        and I assume it makes sense to dissect the flow into paths of similar likelihood to make most
        progress but this is a mere conjecture at this point. I expect quite a bit of research will be
        necessary to resolve this issue.
        """
        # first collect all linearized edges which are assigned a non-zero flow put them into a networkx graph
        G = nx.MultiDiGraph()
        for i in range(self._min_cost_flow.NumArcs()):
            flow = self._min_cost_flow.Flow(i)  # *QUANTIZATION
            if flow == 0:
                continue

            src, dest, channel, _ = self._arc_to_channel[i]
            if G.has_edge(src, dest):
                if channel.short_channel_id in G[src][dest]:
                    G[src][dest][channel.short_channel_id]["flow"] += flow
            else:
                # FIXME: cost is not reflecting exactly the piecewise linearization
                # Probably not such a big issue as we just dissect flow
                G.add_edge(src, dest, key=channel.short_channel_id, flow=flow,
                           channel=channel, weight=channel.combined_linearized_unit_cost())
        used_flow = 1
        attempts = []

        # allocate flow to shortest / cheapest paths from src to dest as long as this is possible
        # decrease flow along those edges. This is a standard mechanism to dissect a flow into paths
        while used_flow > 0:
            try:
                path = nx.shortest_path(G, s, d)
            except:
                break
            channel_path, used_flow = self._make_channel_path(G, path)
            attempts.append(Attempt(channel_path, used_flow))

            # reduce the flow from the selected path
            for pos, hop in enumerate(self._next_hop(path)):
                src, dest = hop
                channel = channel_path[pos]
                G[src][dest][channel.short_channel_id]["flow"] -= used_flow
                if G[src][dest][channel.short_channel_id]["flow"] == 0:
                    G.remove_edge(src, dest, key=channel.short_channel_id)
        return attempts

    def _next_hop(self, path):
        """
        generator to iterate through edges indexed by node id of paths

        The path is a list of node ids. Each call returns a tuple src, dest of an edge in the path
        """
        for i in range(1, len(path)):
            src = path[i - 1]
            dest = path[i]
            yield src, dest
