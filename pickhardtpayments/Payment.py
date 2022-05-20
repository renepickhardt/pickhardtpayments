import logging
import time
from typing import List

import Attempt

class Payment:
    """
    Payment stores the information about an amount of sats to be delivered from source to destination.

    When sending an amount of sats from sender to receiver, a payment is usually split up and sent across
    several paths, to increase the probability of being successfully delivered.
    The PaymentClass holds all necessary information about a payment.
    It also holds information that helps to calculate performance statistics about the payment.

    :param int _total_amount: The total amount of sats to be delivered from source address to destination address.
    :param float _fee: fee in sats for successful delivery and settlement of payment
    :param float _ppm: fee in ppm for successful delivery and settlement of payment
    :param str _sender: sender address for the payment.
    :param str _receiver: receiver address for the payment.
    :param list _attempts: returns a list of Attempts
    :param bool _successful: returns True if the total_amount of the payment could be delivered successfully.
    :param float _start: time when payment was initiated
    :param float _end: time when payment was finished, either by being aborted or by successful settlement
    """

    def __init__(self, sender, receiver, amount: int = 1):
        self._ppm = None
        self._fee = None
        self._end = None
        self._sender = sender
        self._receiver = receiver
        self._total_amount = amount
        self._attempts = list()
        self._start = time.time()

    def __str__(self):
        return "Payment with {} attempts to deliver {} sats from {} to {}".format(len(self._attempts),
                                                                                  self._total_amount,
                                                                                  self._sender[-8:],
                                                                                  self._receiver[-8:])

    @property
    def src(self):
        return self._sender

    @property
    def dest(self):
        return self._receiver

    @property
    def total_amount(self):
        return self._total_amount

    # can later be set at successful settlement or failure
    @property
    def end(self):
        return self._end

    @property
    def attempts(self):
        return self._attempts

    def add_attempt(self, attempt: Attempt):
        self._attempts.append(attempt)

    @property
    def fee(self):
        return self._fee

    @property
    def ppm(self):
        return self._ppm

    @property
    def inflight_attempts(self):
        inflight_attempts = []
        try:
            for attempt in self._attempts:
                if attempt.status == Attempt.SettlementStatus.INFLIGHT:
                    inflight_attempts.append(attempt)
            return inflight_attempts
        except ValueError:
            logging.warning("ValueError in Payment.inflight_attempts")

        return inflight_attempts

    @property
    def failed_attempts(self):
        failed_attempts = []
        try:
            for attempt in self._attempts:
                if attempt.status == Attempt.SettlementStatus.FAILED:
                    failed_attempts.append(attempt)
            return failed_attempts
        except ValueError:
            return []

    @property
    def successful(self):
        return self._successful

    @property
    def sender(self):
        return self._sender

    @property
    def receiver(self):
        return self._receiver
