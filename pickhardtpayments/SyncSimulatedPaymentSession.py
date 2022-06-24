"""
SyncSimulatedPaymentSession.py
====================================
The core module of the pickhardt payment project.
An example payment is executed and statistics are run.
"""

import logging
import sys
from typing import List
import traceback

from .Attempt import Attempt, AttemptStatus
from .Payment import Payment
from .UncertaintyNetwork import UncertaintyNetwork
from .OracleLightningNetwork import OracleLightningNetwork

import time

DEFAULT_BASE_THRESHOLD = 0


def set_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
    logger = logging.getLogger()
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    file_handler = logging.FileHandler('pickhardt_pay.log', mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)
    # logger.basicConfig(handlers=[file_handler, stdout_handler])


class SyncSimulatedPaymentSession:
    """
    A PaymentSession is used to create the min cost flow problem from the UncertaintyNetwork

    This happens by adding several parallel arcs coming from the piece wise linearization of the
    UncertaintyChannel to the min_cost_flow object.

    The main API call is `pickhardt_pay` which invokes a sequential loop to conduct trial and error
    attempts. The loop could easily send out all onions concurrently but this does not make sense
    against the simulated OracleLightningNetwork.
    """

    def __init__(self,
                 oracle_network: OracleLightningNetwork,
                 uncertainty_network: UncertaintyNetwork,
                 prune_network: bool = True):
        self._oracle_network = oracle_network
        self._uncertainty_network = uncertainty_network
        self._uncertainty_network.prune = prune_network

    @property
    def uncertainty_network(self) -> UncertaintyNetwork:
        return self._uncertainty_network

    @property
    def oracle_network(self) -> OracleLightningNetwork:
        return self._oracle_network

    def _attempt_payments(self, attempts: List[Attempt]):
        """
        we attempt all planned payments and test the success against the oracle in particular this
        method changes - depending on the outcome of each payment - our belief about the uncertainty
        in the UncertaintyNetwork.
        successful onions are collected to be transacted on the OracleNetwork if complete payment can be delivered
        """
        # test actual payment attempts
        for attempt in attempts:
            success, erring_channel = self._oracle_network.send_onion(
                attempt.path, attempt.amount)
            if success:
                # TODO: let this happen in Payment class? Or in Attempt class - with status change as settlement
                attempt.status = AttemptStatus.ARRIVED
                # handling amounts on path happens in Attempt Class.
                self._uncertainty_network.allocate_amount_on_path(
                    attempt.path, attempt.amount)

                # unnecessary, because information is in attempt (Status INFLIGHT)
                # settled_onions.append(payments[key])
            else:
                attempt.status = AttemptStatus.FAILED

    def _evaluate_attempts(self, payment: Payment):
        """
        helper function to collect statistics about attempts and print them

        returns the `residual` amount that could not have been delivered and some statistics
        """
        total_fees = 0
        paid_fees = 0
        residual_amt = 0
        expected_sats_to_deliver = 0
        amt = 0
        arrived_attempts = []
        failed_attempts = []
        logging.debug("Statistics about {} candidate onion(s):".format(len(payment.attempts)))

        if len(list(payment.filter_attempts(AttemptStatus.ARRIVED))) > 0:
            logging.debug("successful attempts:")
            logging.debug("--------------------")
            for arrived_attempt in payment.filter_attempts(AttemptStatus.ARRIVED):
                amt += arrived_attempt.amount
                total_fees += arrived_attempt.routing_fee / 1000.
                expected_sats_to_deliver += arrived_attempt.probability * arrived_attempt.amount
                logging.debug(" p = {:6.2f}% amt: {:9} sats  hops: {} ppm: {:5}".format(
                    arrived_attempt.probability * 100, arrived_attempt.amount, len(arrived_attempt.path),
                    int(arrived_attempt.routing_fee * 1000 / arrived_attempt.amount)))
                paid_fees += arrived_attempt.routing_fee
        if len(list(payment.filter_attempts(AttemptStatus.FAILED))) > 0:
            logging.debug("failed attempts:")
            logging.debug("----------------")
            for failed_attempt in payment.filter_attempts(AttemptStatus.FAILED):
                amt += failed_attempt.amount
                total_fees += failed_attempt.routing_fee / 1000.
                expected_sats_to_deliver += failed_attempt.probability * failed_attempt.amount
                logging.debug(" p = {:6.2f}% amt: {:9} sats  hops: {} ppm: {:5}".format(
                    failed_attempt.probability * 100, failed_attempt.amount, len(failed_attempt.path),
                    int(failed_attempt.routing_fee * 1000 / failed_attempt.amount)))
                residual_amt += failed_attempt.amount

        logging.debug("Attempt Summary:")
        logging.debug("________________")
        logging.debug("Tried to deliver \t{:10} sats".format(amt))
        if amt != 0:
            fraction = expected_sats_to_deliver * 100. / amt
            logging.debug("expected to deliver {:10} sats \t({:4.2f}%)".format(
                int(expected_sats_to_deliver), fraction))
            fraction = (amt - residual_amt) * 100. / (amt)
            logging.debug("actually delivered {:10} sats \t({:4.2f}%)".format(
                amt - residual_amt, fraction))
        logging.debug("deviation: \t\t{:4.2f}".format(
            (amt - residual_amt) / (expected_sats_to_deliver + 1)))
        logging.debug("planned_fee: {:8.3f} sat".format(total_fees))
        logging.debug("paid fees: {:8.3f} sat".format(paid_fees))
        return residual_amt, paid_fees, len(payment.attempts), len(failed_attempts)

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
            n, self._oracle_network)

    def pickhardt_pay(self, src, dest, amt, mu=1, base=DEFAULT_BASE_THRESHOLD):
        """
        conduct one experiment! might need to call oracle.reset_uncertainty_network() first
        I could not put it here as some experiments require sharing of liquidity information

        """

        set_logger()
        logging.info('*** new pickhardt payment ***')

        # Setup
        entropy_start = self._uncertainty_network.entropy()
        cnt = 0
        total_fees = 0
        total_number_failed_paths = 0

        # Initialise Payment
        payment = Payment(self.uncertainty_network, self.oracle_network, src, dest, amt)

        # This is the main payment loop. It is currently blocking and synchronous but may be
        # implemented in a concurrent way. Also, we stop after 10 rounds which is pretty arbitrary
        # a better stop criteria would be if we compute infeasible flows or if the probabilities
        # are too low or residual amounts decrease to slowly
        while amt > 0 and cnt < 10:
            logging.debug("")
            logging.debug(f"Starting round number {cnt + 1}")
            logging.debug(f"Try to deliver {amt} satoshi:")

            sub_payment = Payment(self.uncertainty_network, self.oracle_network, payment.sender, payment.receiver, amt)
            # transfer to a min cost flow problem and run the solver
            # paths is the lists of channels, runtime the time it took to calculate all candidates in this round
            runtime = sub_payment.generate_candidate_paths(mu, base)

            # make attempts, try to send onion and register if success or not
            # update our information about the UncertaintyNetwork
            self._attempt_payments(sub_payment.attempts)

            # run some simple statistics and depict them
            amt, paid_fees, num_paths, number_failed_paths = self._evaluate_attempts(
                sub_payment)

            logging.debug("Runtime of flow computation: {:4.2f} sec".format(runtime))

            total_number_failed_paths += number_failed_paths
            total_fees += paid_fees
            cnt += 1

            # add attempts of sub_payment to payment
            payment.add_attempts(sub_payment.attempts)

        # When residual amount is 0 / enough successful onions have been found, then settle payment. Else drop onions.
        if amt == 0:
            for onion in payment.filter_attempts(AttemptStatus.ARRIVED):
                try:
                    self._oracle_network.settle_payment(onion.path, onion.amount)
                    onion.status = AttemptStatus.SETTLED
                except Exception as e:
                    print(e)
                    return -1
            payment.successful = True
        payment.end_time = time.time()

        entropy_end = self._uncertainty_network.entropy()
        logging.info("SUMMARY:")
        logging.info("========")
        logging.info("Rounds of mcf-computations:\t%s", cnt)
        logging.info("Number of attempts made:\t%s", len(payment.attempts))
        logging.info("Number of failed attempts:\t%s", len(list(payment.filter_attempts(AttemptStatus.FAILED))))
        logging.info("Failure rate: {:4.2f}% ".format(
            len(list(payment.filter_attempts(AttemptStatus.FAILED))) * 100. / len(payment.attempts)))
        logging.info("total Payment lifetime (including inefficient memory management): {:4.3f} sec".format(
            payment.end_time - payment.start_time))
        logging.info("Learnt entropy: {:5.2f} bits".format(entropy_start - entropy_end))
        logging.info("fee for settlement of delivery: {:8.3f} sat --> {} ppm".format(
            payment.settlement_fees / 1000, int(payment.settlement_fees * 1000 / payment.total_amount)))
        logging.info("used mu: %s", mu)
        logging.info("Payment was successful: %s", payment.successful)
