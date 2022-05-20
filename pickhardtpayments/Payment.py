import logging
import time

import Attempt


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

    def __init__(self, sender, receiver, total_amount: int = 1):
        """Constructor method
        """
        self._successful = False
        self._ppm = -1
        self._fee = -1
        self._end_time = -1
        self._sender = sender
        self._receiver = receiver
        self._total_amount = total_amount
        self._attempts = list()
        self._start_time = time.time()

    def __str__(self):
        return "Payment with {} attempts to deliver {} sats from {} to {}".format(len(self._attempts),
                                                                                  self._total_amount,
                                                                                  self._sender[-8:],
                                                                                  self._receiver[-8:])

    @property
    def sender(self):
        """Returns the address of the sender of the payment.

        :return: sender address for the payment
        :rtype: str
        """
        return self._sender

    @property
    def receiver(self):
        """Returns the address of the receiver of the payment.

        :return: receiver address for the payment
        :rtype: str
        """
        return self._receiver

    @property
    def total_amount(self):
        """Returns the amount to be sent with this payment.

        :return: The total amount of sats to be delivered from source address to destination address.
        :rtype: int
        """
        return self._total_amount

    @property
    def start_time(self):
        """Returns the time when Payment object was instantiated.

        :return: time in seconds from epoch to instantiation of Payment object.
        :rtype: float
        """
        return self._start_time

    @property
    def end_time(self):
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
    def attempts(self):
        """Returns all onions that were built and are associated with this Payment.

        :return: A list of Attempts of this payment.
        :rtype: list[Attempt]
        """
        return self._attempts

    def add_attempts(self, attempts: list[Attempt]):
        """Adds Attempts (onions) that have been made to settle the Payment to the Payment object.

        :param attempts: a list of attempts that belong to this Payment
        :type: list[Attempt]
        """
        self._attempts.extend(attempts)

    @property
    def fee(self):
        """Returns the fees that accrued for this payment. It's the sum of the routing fees of all settled onions.

        :return: fee in sats for successful attempts of Payment
        :rtype: float
        """
        fee = 0
        for attempt in self.settled_attempts:
            fee += attempt.routing_fee
        return fee

    @property
    def ppm(self):
        """Returns the fees that accrued for this payment. It's the sum of the routing fees of all settled onions.

        :return: fee in ppm for successful delivery and settlement of payment
        :rtype: float
        """
        return self.fee * 1000 / self.total_amount

    @property
    def inflight_attempts(self):
        """Returns all onions that can successfully be routed.

        :return: A list of successful Attempts of this Payment, which could be settled.
        :rtype: list[Attempt]
        """
        inflight_attempts = []
        try:
            for attempt in self._attempts:
                if attempt.status == Attempt.SettlementStatus.INFLIGHT:
                    inflight_attempts.append(attempt)
            return inflight_attempts
        except ValueError:
            logging.warning("ValueError in Payment.inflight_attempts")
        return []

    @property
    def failed_attempts(self):
        """Returns all onions that failed, where no delivery of the (partial) amount was possible.

        :return: A list of failed Attempts of this Payment, Attempts that could be not settled.
        :rtype: list[Attempt]
        """
        failed_attempts = []
        try:
            for attempt in self._attempts:
                if attempt.status == Attempt.SettlementStatus.FAILED:
                    failed_attempts.append(attempt)
            return failed_attempts
        except ValueError:
            logging.warning("ValueError in Payment.failed_attempts")
            return []

    @property
    def settled_attempts(self):
        """Returns all onions that were successfully routed and then settled.

        :return: A list of Attempts of this Payment, which were successfully settled.
        :rtype: list[Attempt]
        """
        settled_attempts = []
        try:
            for attempt in self._attempts:
                if attempt.status == Attempt.SettlementStatus.SETTLED:
                    settled_attempts.append(attempt)
            return settled_attempts
        except ValueError:
            logging.warning("ValueError in Payment.settled_attempts")
            return []

    @property
    def successful(self):
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
