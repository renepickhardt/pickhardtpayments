import time
# from logging import Logger
from typing import List
from ortools.graph import pywrapgraph
import networkx as nx
from .UncertaintyNetwork import UncertaintyNetwork
from .OracleLightningNetwork import OracleLightningNetwork
from .Attempt import Attempt, AttemptStatus

import logging
import sys

logger = logging.getLogger()
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
file_handler = logging.FileHandler('pickhardt_pay.log', mode='a')
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)


class MCFSolverError(Exception):
    """Throws errors when the Min Cost Flow Solver does not return an appropriate result"""
    pass


class Payment:
    """
    Payment stores the information about an amount of sats to be delivered from source to destination.

    When sending an amount of sats from sender to receiver, a payment is usually split up and sent across
    several paths, to increase the probability of being successfully delivered.
    The PaymentClass holds all necessary information about a payment.
    It also holds information that helps to calculate performance statistics about the payment.
    """

    def __init__(self, uncertainty_network: UncertaintyNetwork, oracle_network: OracleLightningNetwork, sender,
                 receiver, total_amount: int, mu: int, base: int):
        """Constructor method
        Builds an instance of Payment

        :param uncertainty_network: the UncertaintyNetwork containing the belief about the Lightning Network
        :type uncertainty_network: UncertaintyNetwork
        :param oracle_network: the OracleNetwork that represents the current state of the Lightning Network
        :type oracle_network: OracleLightningNetwork
        :param sender: sender address for the payment
        :type sender: class:`str`
        :param receiver: receiver address for the payment
        :type receiver: class:`str`
        :param total_amount: The total amount of sats to be delivered from source address to destination address.
        :type total_amount: class:`int`
        :param mu:
        :type mu: int
        :param base:
        :type base: int
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
    def residual_amount(self) -> int:
        """Returns the amount that still needs to be allocated. The total amount of the payment consists of the amounts
        that could be allocated to paths and would successfully be sent in the attempts, and the residual amount.

        :return: The residual amount of sats that needs to be allocated for the payment to deliver the complete amount.
        :rtype: int
        """
        return self._residual_amount

    @property
    def life_time(self) -> float:
        """Time period from when payment was created until the payment finished, either by being aborted or by
        successful settlement

        :return: time in seconds from creation of the payment to successful payment or failure of payment.
        :rtype: float
        """
        if self._end_time and self._start_time:
            return self._end_time - self._start_time
        else:
            return time.time() - self._start_time

    @property
    def attempts(self) -> List[Attempt]:
        """Returns all Attempts that were built and are associated with this Payment.
        These attempts hold the Uncertainty Channels for the path to send a (partial) amount of the payment.

        :return: A list of Attempts of this payment.
        :rtype: list[Attempt]
        """
        return self._attempts

    @property
    def oracle_network(self) -> OracleLightningNetwork:
        """Returns the Oracle Network where in_flight amounts for the (partial) Payment need to be allocated.

        :return: The OracleLightningNetwork that the Payment is created for
        :rtype: OracleLightningNetwork
        """
        return self._oracle_network

    @property
    def uncertainty_network(self) -> UncertaintyNetwork:
        """Returns the UncertaintyNetwork that the (partial) Payment is associated with and built on.

        :return: The UncertaintyNetwork that the Payment is related to
        :rtype: UncertaintyNetwork
        """
        return self._uncertainty_network

    def register_sub_payment(self, sub_payment):
        """Adds Attempts (onions) that have been made to settle the Payment to the Payment object.

        :param sub_payment: a list of attempts that belong to this Payment
        :type: list[Attempt]
        """
        self._attempts.extend(sub_payment.attempts)
        self._residual_amount = sub_payment.residual_amount
        logger.debug("remaining amount: {:>10,}".format(self.residual_amount))

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

    def filter_fees(self, flag: AttemptStatus) -> float:
        """Returns the fees for all Attempts/onions for this payment, that arrived but have not yet been settled.

        It's the sum of the routing fees of all attempts with the status `flag`.

        :param flag: the key that should be used to filter the AttemptStatus of the Attempts
        :type: AttemptStatus
        :return: fee in sats for arrived attempts of Payment
        :rtype: float
        """
        fees = 0
        for attempt in self.filter_attempts(flag):
            fees += attempt.routing_fee
        return fees / 1000

    @property
    def total_fees(self) -> float:
        """Returns the fees for all Attempts/onions for this payment.

        It's the sum of the routing fees of all attempts.

        :return: fee in sats for all attempts of Payment
        :rtype: float
        """
        total_fees = 0
        for attempt in self.attempts:
            total_fees += attempt.routing_fee
        return total_fees / 1000

    @property
    def ppm(self) -> float:
        """Returns the sum of the routing fees of all settled onions in relation to the total amount.

        :return: fee in ppm for successful delivery and settlement of payment
        :rtype: float
        """
        return self.settlement_fees * 1000 / self.total_amount

    @property
    def pickhardt_payment_rounds(self) -> int:
        """Returns the number of rounds needed for this payment.

        :return: The number of rounds needed for this payment.
        :rtype: int
        """
        return self._pickhardt_payment_rounds

    @property
    def uncertainty_network_entropy_delta(self) -> int:
        """Returns the change in entropy of the UncertaintyNetwork as a learning from this payment.

        :return: Change in entropy of the UncertaintyNetwork
        :rtype: int
        """
        return self._uncertainty_network_entropy - self._uncertainty_network.entropy()

    def increment_pickhardt_payment_rounds(self):
        """Increments the number of rounds needed for this payment by 1.
        """
        self._pickhardt_payment_rounds += 1

    def filter_attempts(self, flag: AttemptStatus) -> List[Attempt]:
        """Returns all onions with the given state.

        :param flag: the state of the attempts that should be filtered for
        :type: Attempt.AttemptStatus

        :return: A list of Attempts with status `flag` of this Payment.
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
        """Sets the flag if all inflight attempts of the payment could settle successfully.

        :param value: True if Payment settled successfully, else False.
        :type: bool
        """
        self._successful = value

    def initiate(self):
        """Starts the first step of the processing of a payment.
        The function calls the solver so that the paths for the Payment are established.
        """
        logger.debug("+++++ new payment round +++++")
        logger.debug("Trying to deliver {:,} satoshi from {} to {}:".format(self._total_amount, self.sender[:4],
                                                                            self.receiver[:4]))
        self._generate_candidate_paths()

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

    def _generate_candidate_paths(self) -> float:
        """
        computes the optimal payment split to deliver `amt` from `src` to `dest` and updates our belief about the
        liquidity. This payment split is represented in the Attempts created.
        These Attempts are added to this Payment instance.
        IMPORTANT: Allocates inflight amounts on Uncertainty Channels. This needs to be the case, so that the
        calculation of the following paths respects previous tries.

        This is one step within the payment loop.

        :return: the time elapsed between calling the solver and appending the attempts to the payment.
        :rtype: bool
        """
        # First we prepare the min cost flow by getting arcs from the uncertainty network
        self._start_time = time.time()
        self._prepare_mcf_solver(self._mu, self._base)
        logger.debug("solving mcf...")
        status = self._min_cost_flow.Solve()

        status_description = {
            0: "NOT_SOLVED",
            1: "OPTIMAL",
            2: "FEASIBLE",
            3: "INFEASIBLE",
            4: "UNBALANCED",
            5: "BAD_RESULT",
            6: "BAD_COST_RANGE"
        }
        if status != self._min_cost_flow.OPTIMAL:
            logger.debug('Error trying to deliver %s sats from %s to %s.', self._total_amount,
                         self._sender, self._receiver)
            raise MCFSolverError(f'MinCostFlowBase returns {status_description[status]} '
                                 f'(in Payment(), '
                                 f'_min_cost_flow.Solve().)')

        candidate_paths_in_round = self._dissect_flow_to_paths(self._sender, self._receiver)

        for count, attempt in enumerate(candidate_paths_in_round):
            logger.debug("path no. {} for {:,} sats".format(count, attempt.amount))
            for channel in attempt.path:
                logger.debug("(02) {}-{} Uncertainty Range:\t\t[{:>10,} ; {:>10,}]\t\tinflight {:>10,};\t"
                             "cond_cap: {:>10,}".format(channel.src[:4],
                                                        channel.dest[:4],
                                                        channel.min_liquidity,
                                                        channel.max_liquidity,
                                                        channel.in_flight,
                                                        channel.conditional_capacity))

        self.attempts.extend(candidate_paths_in_round)

        self._end_time = time.time()
        return self._end_time - self._start_time

    def _prepare_mcf_solver(self, mu: int, base_fee: int):
        """
        computes the uncertainty network given our prior belief and prepares the min cost flow solver

        This function can define a value for mu to control how heavily we combine the uncertainty cost and fees Also
        the function supports only taking channels into account that don't charge a base_fee higher or equal to `base`

        returns the instantiated min_cost_flow object from the Google OR-lib that contains the piecewise linearized
        problem

        :param mu: controls the balance between uncertainty cost and fees in the solver
        :type: int
        :param base_fee: eliminates all channels with a base fee lower than `base_fee`
        :type: int
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

    def _dissect_flow_to_paths(self, s, d) -> List[Attempt]:
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
            if G.has_edge(src, dest) and (channel.short_channel_id in G[src][dest]):
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
            except Exception as e:
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

    def attempt_payments(self):
        """
        We try all planned payments by testing the OracleNetwork. 'send_onion' returns the success status and if it's
        positive it will have placed inflight amounts in the OracleNetwork as well as the UncertaintyNetwork.
        That in this step the inflights are placed on the channels is important to update the knowledge about the
        UncertaintyChannel ranges appropriately. (Inflights are later removed when the payment is settled)

        Knowledge about the payment attempts is updated in the Uncertainty Channels.

        Each successful attempt reduces the outstanding amount (residual_amount) of the payment.
        """
        for attempt in self.filter_attempts(AttemptStatus.PLANNED):
            # TODO: add callback, eventloop. or with future, spawning threads.

            # probe channel in Oracle Network
            success_of_probe, erring_channel = self._oracle_network.send_onion(attempt)
            logger.debug(f"Payment attempts successful? {success_of_probe} for {attempt}")

            # TODO: learn: adjust knowledge about channels
            for uncertainty_channel in iter(attempt.path):
                return_channel = self.uncertainty_network.get_channel(uncertainty_channel.dest,
                                                                      uncertainty_channel.src,
                                                                      uncertainty_channel.short_channel_id)

                if not return_channel:
                    logger.debug(f"back channel missing for {uncertainty_channel.short_channel_id}")

                if uncertainty_channel == erring_channel:
                    uncertainty_channel.update_knowledge(attempt.amount, return_channel, False)
                    break
                uncertainty_channel.update_knowledge(attempt.amount, return_channel, True)

            # when successful, place amount as additional in_flight on UncertaintyChannels along path
            if success_of_probe:
                self._residual_amount -= attempt.amount

            if not success_of_probe:
                logger.debug("failed sending {:,} through {}-{}".format(attempt.amount + erring_channel.in_flight,
                                                                        erring_channel.src[0:4],
                                                                        erring_channel.dest[0:4]))
                err_ch = self.oracle_network.get_channel(erring_channel.src, erring_channel.dest,
                                                         erring_channel.short_channel_id)
                logger.debug("which has {:,.0f} sats liquidity with capacity {:,} and {:,} sats in_flight".format(
                    err_ch.actual_liquidity, err_ch.capacity, err_ch.in_flight))

            for ch in iter(attempt.path):
                liquidity = self.oracle_network.get_channel(ch.src, ch.dest, ch.short_channel_id).actual_liquidity
                logger.debug(
                    "(03) {}-{} Channel\t\tEst: [{:>10,} ; {:>11,}]\tliqui {:>11,}\ti_f {:>10,};"
                    "\tcond_cap: {:>10,}".format(
                        ch.src[:4],
                        ch.dest[:4],
                        ch.min_liquidity,
                        ch.max_liquidity,
                        liquidity,
                        ch.in_flight,
                        ch.conditional_capacity))

                return_channel = self.uncertainty_network.get_channel(ch.dest, ch.src, ch.short_channel_id)
                return_liquidity = self.oracle_network.get_channel(ch.dest, ch.src,
                                                                   ch.short_channel_id).actual_liquidity
                if return_channel:
                    logger.debug("(03) {}-{} Ret Channel\tEst: [{:>10,} ; {:>11,}]\tliqui {:>11,}\ti_f "
                                 "{:>10,};\tcond_cap: {:>10,}".format(return_channel.src[:4],
                                                                      return_channel.dest[:4],
                                                                      return_channel.min_liquidity,
                                                                      return_channel.max_liquidity,
                                                                      return_liquidity,
                                                                      return_channel.in_flight,
                                                                      return_channel.conditional_capacity))
        return 0

    def evaluate_attempts(self):
        """
        Helper function to collect statistics about attempts and sends info about the attempts to the logfile

        """
        residual_amt = 0
        expected_sats_to_deliver = 0
        amt = 0
        logger.debug("Statistics about {} candidate onion(s):".format(len(self.attempts)))

        for i, inflight_attempt in enumerate(self.filter_attempts(AttemptStatus.INFLIGHT)):
            if i == 0:
                logger.debug("successful attempts (in_flight):")
                logger.debug("--------------------------------")
            amt += inflight_attempt.amount
            expected_sats_to_deliver += inflight_attempt.probability * inflight_attempt.amount
            logger.debug(" p = {:6.2f}% amt: {:9} sats  hops: {} ppm: {:5}".format(
                inflight_attempt.probability * 100, inflight_attempt.amount, len(inflight_attempt.path),
                int(inflight_attempt.routing_fee * 1000 / inflight_attempt.amount)))

        for i, planned_attempt in enumerate(self.filter_attempts(AttemptStatus.PLANNED)):
            if i == 0:
                logger.debug("planned attempts:")
                logger.debug("----------------")
            amt += planned_attempt.amount
            expected_sats_to_deliver += planned_attempt.probability * planned_attempt.amount
            logger.debug(" p = {:6.2f}% amt: {:9} sats  hops: {} ppm: {:5}".format(
                planned_attempt.probability * 100, planned_attempt.amount, len(planned_attempt.path),
                int(planned_attempt.routing_fee * 1000 / planned_attempt.amount)))
            residual_amt += planned_attempt.amount

        for i, failed_attempt in enumerate(self.filter_attempts(AttemptStatus.FAILED)):
            if i == 0:
                logger.debug("failed attempts:")
                logger.debug("----------------")
            amt += failed_attempt.amount
            expected_sats_to_deliver += failed_attempt.probability * failed_attempt.amount
            logger.debug(" p = {:6.2f}% amt: {:9} sats  hops: {} ppm: {:5}".format(
                failed_attempt.probability * 100, failed_attempt.amount, len(failed_attempt.path),
                int(failed_attempt.routing_fee * 1000 / failed_attempt.amount)))
            residual_amt += failed_attempt.amount

        logger.debug("Attempt Summary:")
        logger.debug("================")
        logger.debug("Tried to deliver \t{:10} sats".format(amt))
        if amt != 0:
            fraction = expected_sats_to_deliver * 100. / amt
            logger.debug("expected to deliver \t{:10} sats \t({:4.2f}%)".format(
                int(expected_sats_to_deliver), fraction))
            fraction = (amt - residual_amt) * 100. / amt
            logger.debug("actually delivered \t{:10} sats \t({:4.2f}%)".format(
                amt - residual_amt, fraction))
        logger.debug("deviation: \t\t{:4.2f}".format(
            (amt - residual_amt) / (expected_sats_to_deliver + 1)))
        logger.debug("planned fee: \t\t{:8.0f} sat".format(self.total_fees / 1000))
        logger.debug("fees for in_flights:\t{:8.0f} sat".format(self.filter_fees(AttemptStatus.INFLIGHT) / 1000))
        if self._end_time:
            logger.debug("Runtime of flow computation: {:4.2f} sec".format(self._end_time - self._start_time))

    def execute(self) -> int:
        """
        Executes the Payment.
        This is the last step in the payment loop. The current in_flight attempts are settled. To achieve this,
        settle_attempt() is called on the Oracle Network as well as on the Uncertainty Network to settle the attempt.
        The in_flights are removed in OracleNetworks and UncertaintyNetwork for this Attempt and the channel balances
        - or the belief about the channel balances - are adjusted.

        """
        logger.info("Executing Payment...")
        logger.debug("settling {} Attempts:".format(len(list(self.filter_attempts(AttemptStatus.INFLIGHT)))))
        for attempt in self.filter_attempts(AttemptStatus.INFLIGHT):
            for channel in attempt.path:
                logger.debug("(04) {}-{} Uncertainty Range:\t\t[{:>10,} ; {:>10,}]\t\tinflight {:>10,};"
                             "\tcond_cap: {:>10,}".format(channel.src[:4],
                                                          channel.dest[:4],
                                                          channel.min_liquidity,
                                                          channel.max_liquidity,
                                                          channel.in_flight,
                                                          channel.conditional_capacity))
                return_channel = self.uncertainty_network.get_channel(channel.dest, channel.src,
                                                                      channel.short_channel_id)
                if return_channel:
                    logger.debug("(05) {}-{} Uncertainty Range:\t\t[{:>10,} ; {:>10,}]\t\tinflight {:>10,};"
                                 "\tcond_cap: {:>10,}".format(return_channel.src[:4],
                                                              return_channel.dest[:4],
                                                              return_channel.min_liquidity,
                                                              return_channel.max_liquidity,
                                                              return_channel.in_flight,
                                                              return_channel.conditional_capacity))

            try:
                logger.debug("settling OracleNetwork...")
                self._oracle_network.settle_attempt(attempt)  # updates in_flights and liquidity in both paths
                logger.debug("settled. settling UncertaintyNetwork...")
                self._uncertainty_network.settle_attempt(attempt)  # removes along path
                attempt.status = AttemptStatus.SETTLED
                logger.debug("settled. Status changed to settled")

                oracle_channel = self.oracle_network.get_channel(channel.src, channel.dest, channel.short_channel_id)
                if not ((oracle_channel.actual_liquidity <= channel.max_liquidity) and
                        (oracle_channel.actual_liquidity >= channel.min_liquidity)):
                    raise ValueError("post settlement liquidity in settlement channel not in range. \n"
                                     "min is {:,}, liqui is {:,} max is {:,}".format(channel.min_liquidity,
                                                                                     oracle_channel.actual_liquidity,
                                                                                     channel.max_liquidity))

                logger.debug("settled. Status changed to settled")

            except Exception as e:
                logger.error("An error occurred when executing payment!")
                logger.error(e)
                self._end_time = time.time()
                return -1

        self.successful = True
        self._end_time = time.time()
        logger.debug("payment executed!")
        for channel in attempt.path:
            logger.debug("(06) {}-{} Uncertainty Range:\t\t[{:>10,} ; {:>10,}]\t\tinflight {:>10,};"
                         "\tcond_cap: {:>10,}".format(channel.src[:4],
                                                      channel.dest[:4],
                                                      channel.min_liquidity,
                                                      channel.max_liquidity,
                                                      channel.in_flight,
                                                      channel.conditional_capacity))
            return_channel = self.uncertainty_network.get_channel(channel.dest, channel.src,
                                                                  channel.short_channel_id)
            if return_channel:
                logger.debug("(07) {}-{} Uncertainty Range:\t\t[{:>10,} ; {:>10,}]\t\tinflight {:>10,};"
                             "\tcond_cap: {:>10,}".format(return_channel.src[:4],
                                                          return_channel.dest[:4],
                                                          return_channel.min_liquidity,
                                                          return_channel.max_liquidity,
                                                          return_channel.in_flight,
                                                          return_channel.conditional_capacity))
        return 0

    def get_summary(self):
        """
        This prints a summary of the payment with statistical information to the logfile.
        """
        logger.info("SUMMARY:")
        logger.info("========")
        logger.info("Payment amount:\t{:>8,}".format(self.total_amount))
        logger.info("Rounds of mcf-computations:\t{:3}".format(self.pickhardt_payment_rounds))
        logger.info("Number of attempts made:\t\t{:3}".format(len(self.attempts)))
        logger.info("Number of failed attempts:\t{:3}".format(len(list(self.filter_attempts(AttemptStatus.FAILED)))))
        if len(self.attempts) > 0:
            logger.info("Failure rate: {:4.2f}% ".format(
                len(list(self.filter_attempts(AttemptStatus.FAILED))) * 100. / len(self.attempts)))
        logger.info("total Payment lifetime (including inefficient memory management): {:4.3f} sec".format(
            self.life_time))
        logger.info("Learnt entropy: {:5.2f} bits".format(self.uncertainty_network_entropy_delta))
        logger.info("fee for settlement of delivery: {:8.3f} sat --> {} ppm".format(
            self.settlement_fees / 1000, int(self.settlement_fees * 1000 / self.total_amount)))
        logger.info("used mu: %s", self._mu)
        logger.info("Payment was successful: %s", self.successful)
        logger.debug("")
