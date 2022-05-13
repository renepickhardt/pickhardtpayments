from .SyncSimulatedPaymentSession import SyncSimulatedPaymentSession
from .UncertaintyNetwork import UncertaintyNetwork
from .OracleLightningNetwork import OracleLightningNetwork

from ortools.graph import pywrapgraph

from typing import List
import time
import networkx as nx

DEFAULT_BASE_THRESHOLD = 0


class SyncPaymentSession(SyncSimulatedPaymentSession):
    """
    A PaymentSesssion is used to create the min cost flow problem from the UncertaintyNetwork

    This happens by adding several parallel arcs coming from the piece wise linearization of the
    UncertaintyChannel to the min_cost_flow object.

    The main API call ist `pickhardt_pay` which invokes a sequential loop to conduct trial and error
    attmpts. The loop could easily send out all onions concurrently but this does not make sense
    against the simulated OracleLightningNetwork.
    """

    def __init__(self,
                 oracle: OracleLightningNetwork,
                 uncertainty_network: UncertaintyNetwork,
                 prune_network: bool = True):
        SyncSimulatedPaymentSession.__init__(self,
                                             oracle,
                                             uncertainty_network,
                                             prune_network)

    def pickhardt_pay(self, src, dest, amt, mu=1, base=0):
        """
        conduct one experiment! might need to call oracle.reset_uncertainty_network() first
        I could not put it here as some experiments require sharing of liqudity information

        """
        print("this method 'pickhardt_pay' in 'SyncPaymentSession' overloads original pickhardt_pay and will not only send onions but sendpay")
        # TODO rework pay method to not only onionsend but pay; make sure that OracleLightningNetwork is updated correspondingly

        return
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
            print("Round number: ", cnt + 1)
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
            total_number_failed_paths * 100. / number_number_of_onions))
        print("total runtime (including inefficient memory managment): {:4.3f} sec".format(
            end - start))
        print("Learnt entropy: {:5.2f} bits".format(entropy_start - entropy_end))
        print("Fees for successfull delivery: {:8.3f} sat --> {} ppm".format(
            total_fees, int(total_fees * 1000 * 1000 / full_amt)))
        print("used mu:", mu)
