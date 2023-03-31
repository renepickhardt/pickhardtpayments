from enum import Enum
from Channel import Channel
from typing import List


class AttemptStatus(Enum):
    PLANNED = 1
    INFLIGHT = 2
    ARRIVED = 4
    FAILED = 8
    SETTLED = 16


class Attempt:
    """
    When sending an amount of sats from sender to receiver, a payment is usually split up and sent across
    several paths, to increase the probability of being successfully delivered. Each of these paths is referred to as an
    Attempt. Attempts thus belong to Payments.
    Central elements of an Attempt are the list of UncertaintyChannels and amount in sats to be sent along this path.

    When an Attempt is instantiated, the given amount is allocated to the in_flight amount in the channels of the
    path in the UncertaintyNetwork and the AttemptStatus is set to PLANNED.

    Each attempt is then probed with send_onion on the oracle network to find out, if the amount can be sent
    successfully from sender to receiver.
    If successful, the AttemptStatus is set to INFLIGHT. The in_flight amounts remain on the UncertaintyNetwork. Nothing
    is done by the Attempt instance.
    If successful, the AttemptStatus is set to FAILED. Then the in_flight amounts are removed from the channels on
    the UncertaintyNetwork.
    """

    def __init__(self, path: List[Channel], amount: int = 0):
        """Constructor method
        Builds an instance of Attempt.

        At initialisation the List of UncertaintyChannels is checked that they build a consecutive path.
        The routing fee that the attempt accrues is calculated.
        The success probability of the attempt is calculated.

        The payment amount of this Attempt is placed as in_flight amount on the Uncertainty Network.
        The Status of this Attempt is set to PLANNED.

        :param path: a list of Channel objects from sender to receiver
        :type path: list[Channel]
        :param amount: the amount to be transferred from source to destination
        :type amount: int
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
            self._path: List[Channel] = path

        self._routing_fee = 0
        self._probability = 1
        for channel in path:
            self._routing_fee += channel.routing_cost_msat(amount)
            self._probability *= channel.success_probability(amount)  # TODO: change to log sum
        self._status = AttemptStatus.PLANNED

    def __str__(self):
        description = "Attempt with {} channels to deliver {:>10,} sats and status {}. ".format(len(self._path),
                                                                                          self._amount,
                                                                                          self._status.name)
        if self._routing_fee and self._routing_fee > 0:
            description += "Success probability of {:6.2f}% , fee of {:8.3f} sat and a ppm of {:5} ".format(
                self._probability * 100, self._routing_fee / 1000, int(self._routing_fee * 1000 / self._amount))
        return description

    @property
    def path(self) -> List[Channel]:
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
            if self._status == AttemptStatus.PLANNED and value == AttemptStatus.INFLIGHT:
                pass

            if self._status == AttemptStatus.INFLIGHT and value == AttemptStatus.ARRIVED:
                pass

            if self._status == AttemptStatus.INFLIGHT and value == AttemptStatus.SETTLED:
                pass

            if self._status == AttemptStatus.PLANNED and value == AttemptStatus.FAILED:
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
