"""
===========================
SyncPaymentSession
===========================

a child of SyncSimulatedPaymentSession, that overloads some functions when needed for the Channel Depletion Simulation
"""

import logging
import time

from SyncSimulatedPaymentSession import SyncSimulatedPaymentSession, MCFSolverError
from pickhardtpayments.Attempt import AttemptStatus
from pickhardtpayments.Payment import Payment
from UncertaintyNetwork import UncertaintyNetwork
from OracleLightningNetwork import OracleLightningNetwork

DEFAULT_BASE_THRESHOLD = 0


class SyncPaymentSession(SyncSimulatedPaymentSession):
    """
    A PaymentSession is used to create the min cost flow problem from the UncertaintyNetwork

    This happens by adding several parallel arcs coming from the piece wise linearization of the
    UncertaintyChannel to the min_cost_flow object.

    The main API call ist `pickhardt_pay` which invokes a sequential loop to conduct trial and error
    attempts. The loop could easily send out all onions concurrently but this does not make sense
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

    # noinspection DuplicatedCode
    def pickhardt_pay(self, src, dest, amt, mu=1, base=0):
        """
        conduct one experiment! might need to call oracle.reset_uncertainty_network() first
        I could not put it here as some experiments require sharing of liquidity information

        """

        # TODO rework pay method to not only onionsend but pay; make sure that OracleLightningNetwork is updated
        #  correspondingly

        # Setup
        entropy_start = self._uncertainty_network.entropy()
        cnt = 0
        total_fees = 0
        total_number_failed_paths = 0

        # Initialise Payment
        payment = Payment(src, dest, amt)

        # This is the main payment loop. It is currently blocking and synchronous but may be
        # implemented in a concurrent way. Also, we stop after 10 rounds which is pretty arbitrary
        # a better stop criteria would be if we compute infeasible flows or if the probabilities
        # are too low or residual amounts decrease to slowly
        while amt > 0 and cnt < 10:
            logging.debug("Round number: %s", cnt + 1)
            logging.debug("Try to deliver %s satoshi:", amt)

            sub_payment = Payment(payment.sender, payment.receiver, amt)
            cnt += 1
            # transfer to a min cost flow problem and run the solver
            # paths is the lists of channels, runtime the time it took to calculate all candidates in this round
            try:
                paths, runtime = self._generate_candidate_paths(payment.sender, payment.receiver, amt, mu, base)
            except MCFSolverError as error:
                logging.error(error)
                return -1
                # break
            else:

                sub_payment.add_attempts(paths)

                # compute some statistics about candidate paths
                self._estimate_payment_statistics(sub_payment.attempts)
                # make attempts, try to send onion and register if success o r not
                # update our information about the UncertaintyNetwork
                self._attempt_payments(sub_payment.attempts)

                # run some simple statistics and depict them
                amt, paid_fees, num_paths, number_failed_paths = self._evaluate_attempts(
                    sub_payment.attempts)

                logging.debug("Runtime of flow computation: {:4.2f} sec ".format(runtime))
                logging.debug("- - - - - - - - - - - - - - - - - - -")
                total_number_failed_paths += number_failed_paths
                total_fees += paid_fees

                # add attempts of sub_payment to payment
                payment.add_attempts(sub_payment.attempts)

        # When residual amount is 0 / enough successful onions have been found, then settle payment. Else drop onions.
        if amt == 0:
            for onion in payment.filter_attempts(AttemptStatus.ARRIVED):
                try:
                    self._oracle.settle_payment(onion.path, onion.amount)
                    onion.status = AttemptStatus.SETTLED
                except Exception as e:
                    print(e)
                    return -1
            payment.successful = True

        payment.end_time = time.time()

        entropy_end = self._uncertainty_network.entropy()
        logging.info("SUMMARY of THIS Payment from Payment set in Simulation:")
        logging.info("=======================================================")
        if payment.successful:
            logging.debug("Payment was successful.")
        else:
            logging.debug("Payment failed.")
        logging.info("Rounds of mcf-computations: \t%s", cnt)
        logging.info("Number of attempts made:\t\t%s", len(payment.attempts))
        logging.info("Number of failed attempts: \t%s", len(payment.filter_attempts(AttemptStatus.FAILED)))
        if payment.attempts:
            logging.info("Failure rate: {:4.2f}% ".format(
                len(payment.filter_attempts(AttemptStatus.FAILED)) * 100. / len(payment.attempts)))
        logging.debug("total Payment lifetime (including inefficient memory management): {:4.3f} sec".format(
            payment.end_time - payment.start_time))
        logging.debug("Learnt entropy: {:5.2f} bits".format(entropy_start - entropy_end))
        logging.debug("fee for settlement of delivery: {:8.3f} sat --> {} ppm".format(
            payment.settlement_fees / 1000, int(payment.settlement_fees * 1000 / payment.total_amount)))
        logging.debug("used mu: \t%s", mu)
        return 1
