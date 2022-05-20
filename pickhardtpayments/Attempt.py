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

    When sending an amount of sats from sender to receiver, a payment is usually split up and sent across
    several paths, to increase the probability of being successfully delivered. Each of this path is referred to as an
    Attempt.
    An Attempt consists of a list of Channels (class:Channel) and the amount in sats to be sent through this path.

    :param path: a list of UncertaintyChannel objects from sender to receiver
    :type path: list[UncertaintyChannel]
    :param amount: the amount to be transferred from source to destination
    :type amount: int
    """

    def __init__(self, path: list[Channel], amount: int = 0):
        """Constructor method
        """
        self._paths = None
        self._routing_fee = -1
        self._probability = -1
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
        """Returns the path of the attempt.

        :return: the list of UncertaintyChannels that the path consists of
        :rtype: list[UncertaintyChannel]
        """
        return self._path

    @path.setter
    def path(self, attempts: list):
        """Sets the path that was set up for a certain amount

        :param attempts: a List of Channels from UncertaintyGraph that an amount was attempted to be routed through
        :type attempts: list[UncertaintyChannel]
        """
        if not isinstance(attempts, list):
            raise ValueError("path needs to be a collection of Channels")
        for attempt in attempts:
            if not isinstance(attempt, Channel):
                raise ValueError("path needs to be a collection of Channels")
        self._paths = attempts

    @property
    def amount(self):
        """Returns the amount of the attempt.

        :return: the amount that was tried to send in this Attempt
        :rtype: int
        """
        return self._amount

    @property
    def status(self):
        """Returns the status of the attempt.

        :return: returns the state of the attempt
        :rtype: SettlementStatus
        """
        return self._status

    @status.setter
    def status(self, value: SettlementStatus):
        """Sets the status of the attempt.

        A flag to describe if the path failed, succeeded or was used for settlement (see enum SettlementStatus)

        :param value: Current state of the Attempt
        :type value: SettlementStatus
        """
        self._status = value

    @property
    def routing_fee(self):
        """Returns the accrued routing fee in msat requested for this path.

        :return: accrued routing fees for this attempt in msat
        :rtype: int
        """
        return self._routing_fee

    @routing_fee.setter
    def routing_fee(self, value: int):
        """Sets the accrued routing fee in msat requested for this path

        :param value: accrued routing fees for this attempt in msat
        :type value: int
        """
        self._routing_fee = value

    @property
    def probability(self):
        """Returns estimated success probability before the attempt

        :return: estimated success probability before the attempt
        :rtype: float
        """
        return self._probability

    @probability.setter
    def probability(self, value: int):
        """Sets the estimated success probability before the attempt

        :param value: estimated success probability before the attempt
        :type value: float
        """
        self._probability = value
