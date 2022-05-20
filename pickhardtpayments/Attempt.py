from enum import Enum

from pickhardtpayments import Channel


class SettlementStatus(Enum):
    PLANNED = 1
    INFLIGHT = 2
    ARRIVED = 3
    FAILED = 4
    SETTLED = 5


class Attempt:
    """
    An Attempt describes a path (a set of channels) of an amount from sender to receiver.

    :param list _path: a list of UncertaintyChannel objects from sender to receiver
    :param int _amount: the amount to be transferred from source to destination
    :param int _routing_fee: the routing fee in msat
    :param float _probability: estimated success probability before the attempt
    :param float _start: time of sending out the onion
    :param float _end: time of getting back the onion
    :param SettlementStatus _status: the flag to describe if the path failed, succeeded or was used for settlement
    """

    def __init__(self, path: list, amount: int = 0):
        self._paths = None
        self._routing_fee = None
        self._probability = None
        if not isinstance(path, list):
            raise ValueError("path needs to be a collection of Channels")
        for channel in path:
            if not isinstance(channel, Channel):
                raise ValueError("path needs to be a collection of Channels")
            self._path = path
        self._status = SettlementStatus.PLANNED
        self._amount = amount

    def __str__(self):
        return "Path with {} channels to deliver {} sats and status {}.".format(len(self._path),
                                                                                self._amount, self._status.name)

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, attempts: list):
        if not isinstance(attempts, list):
            raise ValueError("path needs to be a collection of Channels")
        for attempt in attempts:
            if not isinstance(attempt, Channel):
                raise ValueError("path needs to be a collection of Channels")
        self._paths = attempts

    @property
    def amount(self):
        return self._amount

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value: SettlementStatus):
        self._status = value

    @property
    def routing_fee(self):
        return self._routing_fee

    @routing_fee.setter
    def routing_fee(self, value: int):
        self._routing_fee = value

    @property
    def probability(self):
        return self._probability

    @probability.setter
    def probability(self, value: int):
        self._probability = value
