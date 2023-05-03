"""
SyncSimulatedPaymentSession.py
====================================
The core module of the pickhardt payment project.
An example payment is executed and statistics are run.
"""
from .Payment import Payment
from .UncertaintyNetwork import UncertaintyNetwork
from .OracleLightningNetwork import OracleLightningNetwork
from .DijkstraOverPayment import DijkstraOverPayment
#from .RedundantOverPayment import RedundantOverPayment

import logging
import sys

session_logger = logging.getLogger()
session_logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_handler.setFormatter(formatter)
file_handler = logging.FileHandler('pickhardt_pay.log', mode='w')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
session_logger.addHandler(file_handler)
session_logger.addHandler(stdout_handler)

DEFAULT_BASE_THRESHOLD = 0


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

    def pickhardt_pay(self, src, dest, amt=1, mu=1, base=DEFAULT_BASE_THRESHOLD, redundant_over_payment=False):
        """
        Conducts one payment with the pickhardt payment methodology.

        conduct one experiment! might need to call oracle.reset_uncertainty_network() first
        I could not put it here as some experiments require sharing of liquidity information

        sub_payment.initiate() starts the first round with calling the solver to get paths. For each path the attempt is
        registered as planned and the amount is registered in the uncertainty network as in_flight (better name can be
        determined). On the Attempts of this first round send_onion() is called and with this the attempts are then
        tested against the OracleNetwork. Every failed attempt from send_onion is then updated as
        AttemptStatus.FAILED and the in_flight amounts are removed from the UncertaintyNetwork.
        For every successful  call of send_onion the amount is registered in the OracleNetwork as inflight and the
        AttemptStatus is set to AttemptStatus.INFLIGHT. The amounts have been allocated in the UncertaintyNetwork
        already, so no change is necessary here.
        If onions failed, the next round is started for the remaining amount.

        After the total amount has been allocated on the OracleNetwork, Payment.finalize() is called. This then
        reflects the arrival of all payments at the receiver, who then passes the preimage to unlock the
        HTLCs/inflight amounts. For all Attempts of the Payment with AttemptStatus.INFLIGHT the balances of the nodes
        are updated in the OracleNetwork on both channels (a refactoring of the OracleNetwork can still be
        considered) and also on the Uncertainty Network. The AttemptStatus is consequently set to SETTLED.

        """
        session_logger.info('*** new pickhardt payment ***')

        # Initialise Payment
        payment = None
        if redundant_over_payment is True:
            session_logger.info(
                "using redundant overpayments and max expected value flows")
            payment = DijkstraOverPayment(
                self.uncertainty_network, self.oracle_network, src, dest, amt, mu, base)
        else:
            payment = Payment(self.uncertainty_network,
                              self.oracle_network, src, dest, amt, mu, base)

        # This is the main payment loop. It is currently blocking and synchronous but may be
        # implemented in a concurrent way. Also, we stop after 10 rounds which is pretty arbitrary
        # a better stop criteria would be if we compute infeasible flows or if the probabilities
        # are too low or residual amounts decrease to slowly
        # TODO add 'expected value' to break condition for loop
        while payment.residual_amount > 0 and payment.pickhardt_payment_rounds <= 15:
            if redundant_over_payment is False:
                sub_payment = Payment(self.uncertainty_network, self.oracle_network, payment.sender, payment.receiver,
                                      payment.residual_amount, mu, base)
            else:
                sub_payment = DijkstraOverPayment(self.uncertainty_network, self.oracle_network, payment.sender, payment.receiver,
                                                  payment.residual_amount, mu, base)

            # transfer to a min cost flow problem and run the solver. Attempts for payment are generated.
            sub_payment.initiate()

            # Try to send amounts in attempts and registers if success or not
            # update our information regarding the in_flights in the UncertaintyNetwork and OracleNetwork
            sub_payment.attempt_payments()

            # run some simple statistics and depict them
            sub_payment.evaluate_attempts(payment)

            # add attempts of sub_payment to payment
            payment.register_sub_payment(sub_payment)

        # When residual amount is 0 then settle payment.
        if payment.residual_amount <= 10:
            # TODO: potentially we wish to aboard and not execute
            payment.execute()
        else:
            session_logger.info("Payment failed!")
            session_logger.info("residual amount: %s sats",
                                payment.residual_amount)

        # Final Stats
        payment.get_summary()
