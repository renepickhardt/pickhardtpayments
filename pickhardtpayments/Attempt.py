from enum import Enum

from Channel import Channel
from pickhardtpayments import UncertaintyChannel


class AttemptStatus(Enum):
    PLANNED = 1
    INFLIGHT = 2
    ARRIVED = 4
    FAILED = 8
    SETTLED = 16


class Attempt:
    """
    An Attempt describes a path (a list of channels) of an amount from sender to receiver.

    # TODO Describe life cycle of an Attempt

    When sending an amount of sats from sender to receiver, a payment is usually split up and sent across
    several paths, to increase the probability of being successfully delivered. Each of these paths is referred to as an
    Attempt.
    An Attempt consists of a list of Channels (class:Channel) and the amount in sats to be sent through this path.
    When an Attempt is instantiated, the given amount is allocated to the inflight amount in the channels of the
    path and the AttemptStatus is set to PLANNED.

    :param path: a list of Channel objects from sender to receiver
    :type path: list[Channel]
    :param amount: the amount to be transferred from source to destination
    :type amount: int
    """

    def __init__(self, path: list[UncertaintyChannel], amount: int = 0):
        """Constructor method
        """
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

        channel: UncertaintyChannel
        self._routing_fee = 0
        self._probability = 1
        for channel in path:
            self._routing_fee += channel.routing_cost_msat(amount)
            self._probability *= channel.success_probability(amount)
            # When Attempt is created, all amounts are set inflight. Needs to be updated with AttemptStatus change!
            # This is to correctly compute conditional probabilities of non-disjoint paths in the same set of paths
            # channel.in_flight(amount)
            channel.allocate_amount(amount)
        self._status = AttemptStatus.PLANNED

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
        if not self._status == value:
            # remove allocated amounts when Attempt status changes from PLANNED
            if self._status == AttemptStatus.PLANNED and not value == AttemptStatus.INFLIGHT:
                for channel in self._path:
                    channel.allocate_amount(-self._amount)

            if self._status == AttemptStatus.INFLIGHT and value == AttemptStatus.ARRIVED:
                # TODO write amount from inflight to min_liquidity/max_liquidity
                # for channel in self._path:
                #    channel.allocate_amount(-self._amount)
                pass

            self._status = value

    @property
    def routing_fee(self) -> int:
        """Returns the accrued routing fee in msat requested for this path.

        :return: accrued routing fees for this attempt in msat
        :rtype: int
        """
        return self._routing_fee

    @property
    def probability(self) -> float:
        """Returns estimated success probability before the attempt

        :return: estimated success probability before the attempt
        :rtype: float
        """
        return self._probability
