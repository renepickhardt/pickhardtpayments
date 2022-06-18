from enum import Enum

from Channel import Channel


class AttemptStatus(Enum):
    PLANNED = 1
    INFLIGHT = 2
    ARRIVED = 4
    FAILED = 8
    SETTLED = 16


class Attempt:
    """
    An Attempt describes a path (a list of channels) of an amount from sender to receiver.

    When sending an amount of sats from sender to receiver, a payment is usually split up and sent across
    several paths, to increase the probability of being successfully delivered. Each of these paths is referred to as an
    Attempt.
    An Attempt consists of a list of Channels (class:Channel) and the amount in sats to be sent through this path.

    :param path: a list of Channel objects from sender to receiver
    :type path: list[Channel]
    :param amount: the amount to be transferred from source to destination
    :type amount: int
    """

    def __init__(self, path: list[Channel], amount: int = 0):
        """Constructor method
        """
        self._routing_fee = None
        self._probability = None
        self._status = AttemptStatus.PLANNED

        if amount >= 0:
            self._amount = amount
        else:
            raise ValueError("amount for payment attempts needs to be positive")

        i = 1
        valid_path = True
        while i < len(path):
            valid_path = valid_path and (path[i - 1].dest == path[i].src)
            i += 1
        if valid_path:
            self._path = path

    def __str__(self):
        description = "Path with {} channels to deliver {} sats and status {}.".format(len(self._path),
                                                                                       self._amount, self._status.name)
        if self._routing_fee and self._routing_fee > 0:
            description += "\nsuccess probability of {:6.2f}% , fee of {:8.3f} sat and a ppm of {:5} ".format(
                self._probability * 100, self._routing_fee/1000, int(self._routing_fee * 1000 / self._amount))
        return description

    @property
    def path(self) -> list[Channel]:
        """Returns the path of the attempt.

        :return: the list of Channels that the path consists of
        :rtype: list[Channel]
        """
        return self._path

    @property
    def amount(self) -> int:
        """Returns the amount of the attempt.

        :return: the amount that was tried to send in this Attempt
        :rtype: int
        """
        return self._amount

    @property
    def status(self) -> AttemptStatus:
        """Returns the status of the attempt.

        :return: returns the state of the attempt
        :rtype: AttemptStatus
        """
        return self._status

    @status.setter
    def status(self, value: AttemptStatus):
        """Sets the status of the attempt.

        A flag to describe if the path failed, succeeded or was used for settlement (see enum SettlementStatus)

        :param value: Current state of the Attempt
        :type value: AttemptStatus
        """
        self._status = value

    @property
    def routing_fee(self) -> int:
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
    def probability(self) -> float:
        """Returns estimated success probability before the attempt

        :return: estimated success probability before the attempt
        :rtype: float
        """
        return self._probability

    @probability.setter
    def probability(self, value: int):
        """Sets the estimated success probability of the attempt.

        This is calculated as product of the channels' success probabilities as determined in the UncertaintyGraph.

        :param value: estimated success probability of the attempt
        :type value: float
        """
        self._probability = value
