from .UncertaintyNetwork import UncertaintyNetwork
from .OracleLightningNetwork import OracleLightningNetwork

from ortools.graph import pywrapgraph


from typing import List
import time
import networkx as nx


DEFAULT_BASE_THRESHOLD = 0


class SyncSimulatedPaymentSession():
    """
    A PaymentSesssion is used to create the min cost flow problem from the UncertaintyNetwork

    This happens by adding several parallel arcs coming from the piece wise linearization of the
    UncertaintyChannel to the min_cost_flow object. 

    The main API call is `pickhardt_pay` which invokes a sequential loop to conduct trial and error
    attempts. The loop could easily send out all onions concurrently but this does not make sense 
    against the simulated OracleLightningNetwork. 
    """

    def __init__(self,
                 oracle: OracleLightningNetwork,
                 uncertainty_network: UncertaintyNetwork,
                 prune_network: bool = True):
        self._oracle = oracle
        self._uncertainty_network = uncertainty_network
        self._prune_network = prune_network
        self._prepare_integer_indices_for_nodes()

    def _prepare_integer_indices_for_nodes(self):
        """
        necessary for the OR-lib by google and the min cost flow solver


        let's initialize the look up tables for node_ids to integers from [0,...,#number of nodes]
        this is necessary because of the API of the Google Operations Research min cost flow solver
        """
        self._mcf_id = {}
        self._node_key = {}
        for k, node_id in enumerate(self._uncertainty_network.network.nodes()):
            self._mcf_id[node_id] = k
            self._node_key[k] = node_id

    def _prepare_mcf_solver(self, src, dest, amt: int = 1, mu: int = 100_000_000, base_fee: int = DEFAULT_BASE_THRESHOLD):
        """
        computes the uncertainty network given our prior belief and prepares the min cost flow solver

        This function can define a value for \mu to control how heavily we combine the uncertainty cost and fees
        Also the function supports only taking channels into account that don't charge a base_fee higher or equal to `base`

        returns the instantiated min_cost_flow object from the google OR-lib that contains the piecewise linearized problem
        """
        self._min_cost_flow = pywrapgraph.SimpleMinCostFlow()
        self._arc_to_channel = {}

        for s, d, channel in self._uncertainty_network.network.edges(data="channel"):
            # ignore channels with too large base fee
            if channel.base_fee > base_fee:
                continue
            # FIXME: Remove Magic Number for pruning
            # Prune channels away thay have too low success probability! This is a huge runtime boost
            # However the pruning would be much better to work on quantiles of normalized cost
            # So as soon as we have better Scaling, Centralization and feature engineering we can
            # probably have a more focused pruning
            if self._prune_network and channel.success_probability(250_000) < 0.9:
                continue
            cnt = 0
            # QUANTIZATION):
            for capacity, cost in channel.get_piecewise_linearized_costs(mu=mu):
                index = self._min_cost_flow.AddArcWithCapacityAndUnitCost(self._mcf_id[s],
                                                                          self._mcf_id[d],
                                                                          capacity,
                                                                          cost)
                self._arc_to_channel[index] = (s, d, channel, 0)
                if self._prune_network and cnt > 1:
                    break
                cnt += 1

        # Add node supply to 0 for all nodes
        for i in self._uncertainty_network.network.nodes():
            self._min_cost_flow.SetNodeSupply(self._mcf_id[i], 0)

        # add amount to sending node
        self._min_cost_flow.SetNodeSupply(
            self._mcf_id[src], int(amt))  # /QUANTIZATION))

        # add -amount to recipient nods
        self._min_cost_flow.SetNodeSupply(
            self._mcf_id[dest], -int(amt))  # /QUANTIZATION))

    def _next_hop(self, path):
        """
        generator to iterate through edges indexed by node id of paths

        The path is a list of node ids. Each call returns a tuple src, dest of an edge in the path    
        """
        for i in range(1, len(path)):
            src = path[i-1]
            dest = path[i]
            yield (src, dest)

    def _make_channel_path(self, G: nx.MultiDiGraph, path: List[str]):
        """
        network x returns a path as a list of node_ids. However we need a list of `UncertaintyChannels`
        Since the graph has parallel edges it is quite some work to get the actual channels that the 
        min cost flow solver produced
        """
        channel_path = []
        bottleneck = 2**63
        for src, dest in self._next_hop(path):
            w = 2**63
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

    def _disect_flow_to_paths(self, s, d):
        """
        A standard algorithm to disect a flow into several paths.

        FIXME: Note that this dissection while accurate is probably not optimal in practice. 
        As noted in our Probabilistic payment delivery paper the payment process is a bernoulli trial 
        and I assume it makes sense to dissect the flow into paths of similar likelihood to make most
        progress but this is a mere conjecture at this point. I expect quite a bit of research will be
        necessary to resolve this issue.
        """
        total_flow = {}

        # first collect all linearized edges which are assigned a non zero flow put them into a networkx graph
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
                # Probably not such a big issue as we just disect flow
                G.add_edge(src, dest, key=channel.short_channel_id, flow=flow,
                           channel=channel, weight=channel.combined_linearized_unit_cost())
        used_flow = 1
        channel_paths = []

        # allocate flow to shortest / cheapest paths from src to dest as long as this is possible
        # decrease flow along those edges. This is a standard mechanism to disect a flow int paths
        while used_flow > 0:
            path = None
            try:
                path = nx.shortest_path(G, s, d)
            except:
                break
            channel_path, used_flow = self._make_channel_path(G, path)
            channel_paths.append((channel_path, used_flow))

            # reduce the flow from the selected path
            for pos, hop in enumerate(self._next_hop(path)):
                src, dest = hop
                channel = channel_path[pos]
                G[src][dest][channel.short_channel_id]["flow"] -= used_flow
                if G[src][dest][channel.short_channel_id]["flow"] == 0:
                    G.remove_edge(src, dest, key=channel.short_channel_id)
        return channel_paths

    def _generate_candidate_paths(self, src, dest, amt, mu: int = 100_000_000, base: int = DEFAULT_BASE_THRESHOLD):
        """
        computes the optimal payment split to deliver `amt` from `src` to `dest` and updates our belief about the liquidity

        This is one step within the payment loop.

        Returns the residual amount of the `amt` that could ne be delivered and the paid fees
        (on a per channel base not including fees for downstream fees) for the delivered amount

        the function also prints some results an statistics about the paths of the flow to stdout.
        """

        # First we prepare the min cost flow by getting arcs from the uncertainty network
        self._prepare_mcf_solver(src, dest, amt, mu, base)

        start = time.time()
        #print("solving mcf...")
        status = self._min_cost_flow.Solve()

        if status != self._min_cost_flow.OPTIMAL:
            print('There was an issue with the min cost flow input.')
            print(f'Status: {status}')
            exit(1)

        paths = self._disect_flow_to_paths(src, dest)
        end = time.time()
        return paths, end-start

    def _estimate_payment_statistics(self, paths):
        """
        estimates the success probability of paths and computes fees (without paying downstream fees)

        @returns the statistics in the `payments` dictionary
        """
        # FIXME: Decide if an `Payments` or `Attempt` class shall be used
        payments = {}
        # compute fees and probabilities of candidate paths for evaluation
        for i, onion in enumerate(paths):
            path, amount = onion
            fee, probability = self._uncertainty_network.get_features_of_candidate_path(
                path, amount)
            payments[i] = {
                "routing_fee": fee, "probability": probability, "path": path, "amount": amount}

            # to correctly compute conditional probabilities of non disjoint paths in the same set of paths
            self._uncertainty_network.allocate_amount_on_path(path, amount)

        # remove allocated amounts for all planned onions before doing actual attempts
        for key, attempt in payments.items():
            self._uncertainty_network.allocate_amount_on_path(
                attempt["path"], -attempt["amount"])

        return payments

    def _attempt_payments(self, payments):
        """
        we attempt all planned payments and test the success against the oracle in particular this
        method changes - depending on the outcome of each payment - our belief about the uncertainty
        in the UncertaintyNetwork
        """
        # test actual payment attempts
        for key, attempt in payments.items():
            success, erring_channel = self._oracle.send_onion(
                attempt["path"], attempt["amount"])
            payments[key]["success"] = success
            payments[key]["erring_channel"] = erring_channel
            if success:
                self._uncertainty_network.allocate_amount_on_path(
                    attempt["path"], attempt["amount"])

    def _evaluate_attempts(self, payments):
        """
        helper function to collect statistics about attempts and print them

        returns the `residual` amount that could not have been delivered and some statistics
        """
        total_fees = 0
        paid_fees = 0
        residual_amt = 0
        number_failed_paths = 0
        expected_sats_to_deliver = 0
        amt = 0
        print("\nStatistics about {} candidate onions:\n".format(len(payments)))

        has_failed_attempt = False
        print("successful attempts:")
        print("--------------------")
        for attempt in payments.values():
            success = attempt["success"]
            if success == False:
                has_failed_attempt = True
                continue
            fee = attempt["routing_fee"] / 1000.
            probability = attempt["probability"]
            path = attempt["path"]
            amount = attempt["amount"]
            amt += amount
            total_fees += fee
            expected_sats_to_deliver += probability * amount
            print(" p = {:6.2f}% amt: {:9} sats  hops: {} ppm: {:5}".format(
                probability*100, amount, len(path), int(fee*1000_000/amount)))
            paid_fees += fee

        if has_failed_attempt:
            print("\nfailed attempts:")
            print("----------------")
            for attempt in payments.values():
                success = attempt["success"]
                if success:
                    continue
                fee = attempt["routing_fee"] / 1000.
                probability = attempt["probability"]
                path = attempt["path"]
                amount = attempt["amount"]
                amt += amount
                total_fees += fee
                expected_sats_to_deliver += probability * amount
                print(" p = {:6.2f}% amt: {:9} sats  hops: {} ppm: {:5} ".format(
                    probability*100, amount, len(path), int(fee*1000_000/amount)))
                number_failed_paths += 1
                residual_amt += amount

        print("\nAttempt Summary:")
        print("=================")
        print("\nTried to deliver {:10} sats".format(amt))
        fraction = expected_sats_to_deliver*100./amt
        print("expected to deliver {:10} sats \t({:4.2f}%)".format(
            int(expected_sats_to_deliver), fraction))
        fraction = (amt-residual_amt)*100./(amt)
        print("actually deliverd {:10} sats \t({:4.2f}%)".format(
            amt-residual_amt, fraction))
        print("deviation: {:4.2f}".format(
            (amt-residual_amt)/(expected_sats_to_deliver+1)))
        print("planned_fee: {:8.3f} sat".format(total_fees))
        print("paid fees: {:8.3f} sat".format(paid_fees))
        return residual_amt, paid_fees, len(payments), number_failed_paths

    def forget_information(self):
        """
        forgets all the information in the UncertaintyNetwork that is a member of the PaymentSession
        """
        self._uncertainty_network.reset_uncertainty_network()

    def activate_network_wide_uncertainty_reduction(self, n):
        """
        Pipes API call to the UncertaintyNetwork
        """
        self._uncertainty_network.activate_network_wide_uncertainty_reduction(
            n, self._oracle)

    def pickhardt_pay(self, src, dest, amt, mu=1, base=0):
        """
        conduct one experiment! might need to call oracle.reset_uncertainty_network() first
        I could not put it here as some experiments require sharing of liqudity information

        """
        entropy_start = self._uncertainty_network.entropy()
        start = time.time()
        full_amt = amt
        cnt = 0
        total_fees = 0
        number_number_of_onions = 0
        total_number_failed_paths = 0

        # This is the main payment loop. It is currently blocking and synchronous but may be
        # implemented in a concurrent way. Also we stop after 10 rounds which is pretty arbitrary
        # a better stop criteria would be if we compute infeasable flows or if the probabilities
        # are to low or residual amounts decrease to slowly
        while amt > 0 and cnt < 10:
            print("Round number: ", cnt+1)
            print("Try to deliver", amt, "satoshi:")

            # transfer to a min cost flow problem and rund the solver
            paths, runtime = self._generate_candidate_paths(
                src, dest, amt, mu, base)

            # compute some statistics about candidate paths
            payments = self._estimate_payment_statistics(paths)

            # matke attempts and update our information about the UncertaintyNetwork
            self._attempt_payments(payments)

            # run some simple statistics and depict them
            amt, paid_fees, num_paths, number_failed_paths = self._evaluate_attempts(
                payments)
            print("Runtime of flow computation: {:4.2f} sec ".format(runtime))
            print("\n================================================================\n")

            number_number_of_onions += num_paths
            total_number_failed_paths += number_failed_paths
            total_fees += paid_fees
            cnt += 1
        end = time.time()
        entropy_end = self._uncertainty_network.entropy()
        print("SUMMARY:")
        print("========")
        print("Rounds of mcf-computations: ", cnt)
        print("Number of onions sent: ", number_number_of_onions)
        print("Number of failed onions: ", total_number_failed_paths)
        print("Failure rate: {:4.2f}% ".format(
            total_number_failed_paths*100./number_number_of_onions))
        print("total runtime (including inefficient memory managment): {:4.3f} sec".format(
            end-start))
        print("Learnt entropy: {:5.2f} bits".format(entropy_start-entropy_end))
        print("Fees for successfull delivery: {:8.3f} sat --> {} ppm".format(
            total_fees, int(total_fees*1000*1000/full_amt)))
        print("used mu:", mu)
