import logging

from Attempt import AttemptStatus
from Channel import Channel
from OracleLightningNetwork import OracleLightningNetwork
from math import log2 as log

DEFAULT_MU = 1
DEFAULT_N = 5


class UncertaintyChannel(Channel):
    """
    The channel class contains basic information of a channel that will be used to create the
    UncertaintyNetwork.

    Since we optimize for reliability via a probability estimate for liquidity that is based
    on the capacity of the channel, the class contains the `capacity` as seen in the funding tx output.

    As we also optimize for fees and want to be able to compute the fees of a flow ,the class
    contains information for the fee rate (`ppm`) and the base_fee (`base`).

    Most importantly the class stores our belief about the liquidity information of a channel.
    This is done by reducing the uncertainty interval from [0,`capacity`] to 
    [`min_liquidity`, `max_liquidity`].
    Additionally, we need to know how many sats we currently have allocated via outstanding onions
    to the channel which is stored in `in_flight`.

    The most important API call is the `get_piecewise_linearized_costs` function that computes the
    piecewise linearized cost for a channel rising from uncertainty as well as routing fees.
    """

    TOTAL_NUMBER_OF_SATS = 21_000_000 * 100_000_000
    MAX_CHANNEL_SIZE = 15_000_000_000  # 150 BTC

    def __init__(self, channel: Channel):
        super().__init__(channel.cln_jsn)
        self._short_channel_id = channel.short_channel_id
        self._in_flight = None
        self._min_liquidity = None
        self._max_liquidity = None
        self.forget_information()

    def __str__(self):
        return "Size: {} with {:4.2f} bits of Entropy. Uncertainty Interval: [{},{}] inflight: {}".format(
            self.capacity,
            self.entropy(),
            self.min_liquidity,
            self.max_liquidity,
            self._in_flight)

    @property
    def max_liquidity(self):
        return self._max_liquidity

    # FIXME: store timestamps when using setters so that we know when we learnt our belief
    @max_liquidity.setter
    def max_liquidity(self, value: int):
        self._max_liquidity = value

    @property
    def min_liquidity(self):
        return self._min_liquidity

    # FIXME: store timestamps when using setters so that we know when we learnt our belief
    @min_liquidity.setter
    def min_liquidity(self, value: int):
        self._min_liquidity = value

    @property
    def in_flight(self):
        """
        The amount currently allocated for potential payments through this channel. This resembles the concept of an
        HTLC.

        :return: in_flight amount on the UncertaintyChannel
        """
        return self._in_flight

    # FIXME: store timestamps when using setters so that we know when we learnt our belief
    @in_flight.setter
    def in_flight(self, value: int):
        self._in_flight = value

    @property
    def conditional_capacity(self, respect_inflight=True):
        """
        Conditional Capacity is the capacity in the channel after we applied our knowledge about minimum liquidity
        and maximum liquidity.
        This is done by reducing the uncertainty interval from [0,`capacity`] to [`min_liquidity`, `max_liquidity`].

        :param respect_inflight: are in_flight amounts considered when calculating the conditional capacity?
        """
        # FIXME: make sure if respect_inflight=True is needed for linearized cost
        if not respect_inflight:
            return self.max_liquidity - self.min_liquidity

        min_liquidity = max(self.min_liquidity, self.in_flight)
        return max(self.max_liquidity - min_liquidity, 0)

    def allocate_inflights(self, amt: int):
        """
        assign or remove amount that is assigned to be `in_flight`.
        """
        self.in_flight += amt
        if self.in_flight < 0:
            raise Exception(
                "Can't remove in flight HTLC of amt {} current inflight: {}".format(-amt, self._in_flight - amt))

    # FIXME: store timestamps when using setters so that we know when we learnt our belief
    def forget_information(self):
        """
        resets the information that we believe to have about the channel. 
        """
        self.min_liquidity = 0
        self.max_liquidity = self.capacity
        # FIXME: Is there a case where we want to keep inflight information but reset information?
        self._in_flight = 0

    def entropy(self):
        """
        returns the uncertainty that we have about the channel

        this respects our belief about the channel's liquidity and thus is just the log
        of the conditional capacity.

        FIXME: This respects inflight information? I assume it shouldn't.
        """
        return log(self.conditional_capacity + 1)

    def success_probability(self, amt: int = None):
        """
        returns the estimated success probability for a payment based on our belief about the channel using a
        uniform distribution.

        While this is the core of the theory it is only used for evaluation and not for the
        actual min cost flow computation as we linearize this to an integer unit cost

        In particular the conditional probability P(X>=a | min_liquidity < X < max_liquidity)
        is computed based on our belief also respecting how many satoshis we have currently 
        outstanding and allocated. Thus it is possible that testing for the `amt=0` that the success probability
        is zero and in particular not `1`.

        It also accounts for the number of satoshis we have already outstanding but have not received information about

        FIXME: Potentially test other prior distributions like mixedmodels where most funds are on one side of the channel
        """
        if amt is None:
            amt = 0
        tested_liquidity = amt + self.in_flight
        if tested_liquidity <= self.min_liquidity:
            return 1.0
        elif tested_liquidity >= self.max_liquidity:
            return 0.
        else:
            conditional_amount = tested_liquidity - self.min_liquidity
            # TODO: can't use self.condition_capacity as that respects inflight htlcs
            conditional_capacity = self.max_liquidity - self.min_liquidity
            if conditional_amount >= conditional_capacity:
                return 0.
            return float(conditional_capacity + 1 - conditional_amount) / (conditional_capacity + 1)

    def uncertainty_cost(self, amt: int):
        """
        Returns the uncertainty cost associated to sending the amount `amt` respecting our current belief
        about the channel's liquidity and the in_flight HTLC's that we have allocated and outstanding.
        """
        return -log(self.success_probability(amt))

    def linearized_uncertainty_cost(self, amt: int):
        """
        the linearized uncertainty cost is just amt/(capacity+1). Using this is most likely not what
        one wants as this tends to saturate channels. The API is included to explain the theory.

        Warning: This API does not respect our belief about the channels liquidity or allocated in_flight HTLCs
        """
        # TODO: Maybe change to `return amt*self.linlinearized_integer_uncertainty_unit_cost()`
        return float(amt) / (self.capacity + 1)

    def linearized_integer_uncertainty_unit_cost(self, use_conditional_capacity=True):
        """
        estimates the linearized integer uncertainty cost

        FIXME: Instead of using the maximum capacity on the network it just assumes 150BTC to be max
        """
        # FIXME: interesting! Quantization does not change unit cost as it cancels itself
        # FIXME: use max satoshis available and control for quantization (makes mu depend on quantization....)
        if use_conditional_capacity:
            # FIXME: better choice of magic number but TOTAL_NUMBER_OF_SATS breaks solver
            return int(self.MAX_CHANNEL_SIZE / max(self.conditional_capacity, 1))
            # return int(self.TOTAL_NUMBER_OF_SATS/self.capacity)
        else:
            return int(self.MAX_CHANNEL_SIZE / self.capacity)
            # return int(self.TOTAL_NUMBER_OF_SATS/self.conditional_capacity)

    def routing_cost_msat(self, amt: int):
        """
        Routing cost a routing node will earn to forward a payment along this channel in msats
        """
        return int(self.ppm * amt / 1000) + self.base_fee

    def linearized_routing_cost_msat(self, amt: int):
        """
        Linearizing the routing cost by ignoring the base fee.

        Note that one can still include channels with small base fees to the computation the base 
        will just be excluded in the computation and has to be paid later anyway. If as developers
        we go down this road this will allow routing node operators to game us with the base fee
        thus it seems reasonable in routing computations to just ignore channels that charge a base fee.

        There are other ways of achieving this by overestimating the fee as ZmnSCPxj suggested at:
        https://lists.linuxfoundation.org/pipermail/lightning-dev/2021-August/003206.html
        """
        return int(self.ppm * amt / 1000.)

    def linearized_integer_routing_unit_cost(self):
        "Note that the ppm is natively an integer and can just be taken as a unit cost for the solver"
        return int(self.ppm)

    # FIXME: better default mu
    def combined_linearized_unit_cost(self, mu: int = DEFAULT_MU):
        """
        Builds the weighted sum between our two unit costs.

        Not being used in the code. Just here to describe the theory.
        """
        return self.linearized_integer_uncertainty_unit_cost() + mu * self.linearized_integer_routing_unit_cost()

    def get_piecewise_linearized_costs(self, number_of_pieces: int = DEFAULT_N, mu: int = DEFAULT_MU):
        """

        """
        # FIXME: compute smarter linearization eg: http://www.iaeng.org/publication/WCECS2008/WCECS2008_pp1191-1194.pdf
        pieces = [] * number_of_pieces

        # using certainly available liquidity costs us nothing but fees
        if int(self.min_liquidity - self.in_flight) > 0:
            uncertainty_unit_cost = 0  # is zero as we have no uncertainty in this case!
            pieces.append((int(self.min_liquidity - self.in_flight),
                           uncertainty_unit_cost + mu * self.linearized_integer_routing_unit_cost()))
            number_of_pieces -= 1

        # FIXME: include the in_flight stuff
        if int(self.conditional_capacity) > 0 and number_of_pieces > 0:
            arc_capacity = int(self.conditional_capacity / number_of_pieces)
            uncertainty_unit_cost = self.linearized_integer_uncertainty_unit_cost()
            for i in range(number_of_pieces):
                pieces.append((arc_capacity, (i + 1) * uncertainty_unit_cost +
                               mu * self.linearized_integer_routing_unit_cost()))
        return pieces

    """
    #FIXME: interestingly the following feature engineering does not work at all
    
    TODO: Look at more standard Univariate Transformations on Numerical Data techniques as described at 
    https://www.kaggle.com/code/milankalkenings/comprehensive-tutorial-feature-engineering/notebook
    
    def get_piecewise_linearized_costs(self,number_of_pieces : int = DEFAULT_N,
                                       mu : int = DEFAULT_MU,
                                       quantization : int = DEFAULT_QUANTIZATION):
        #FIXME: compute smarter linearization eg: http://www.iaeng.org/publication/WCECS2008/WCECS2008_pp1191-1194.pdf
        pieces = []*number_of_pieces

        #using certainly available liquidity costs us nothing but fees
        if int((self.min_liquidity-self.in_flight)/quantization) > 0:
            uncertainty_unit_cost = 0 #is zero as we have no uncertainty in this case!
            pieces.append((int((self.min_liquidity-self.in_flight)/quantization),uncertintay_unit_cost + mu * self.linearized_integer_routing_unit_cost()))
            number_of_pieces-=1

        # FIXME: include the in_flight stuff
        if int(self.conditional_capacity/quantization) > 0 and number_of_pieces > 0:
            capacity = int(self.conditional_capacity/(number_of_pieces*quantization))
            uncertainty_unit_cost = self.linearized_integer_uncertainty_unit_cost()
            for i in range(number_of_pieces):
                a = (i+1)*uncertainty_unit_cost+1
                b = self.linearized_integer_routing_unit_cost()+1
                pieces.append((capacity, int(a*b/(a+mu*b)) ))
        return pieces
    """

    def update_knowledge(self, amount: int, return_channel, probing_successful: bool):
        """
        Updates our knowledge about the channel after probing with 'send_onion'.

        'send_onion' already placed the amount as inflight on the UncertaintyChannel. Because we currently don't konw
        if the payment will be settled successfully, we can only incorporate current knowledge. Any change because of
        settlement will have to be considered at another location.

        What can we learn from a successfully sent onion?
        * If we knew that there was a minimum liquidity greater than the in_flights on the channel, than this is fine.
          Nothing done.
        * If there was no knowledge about the minimum liquidity, then we now know that it is at least the in_flights.
        * We learnt nothing about the maximum liquidity in this channel.
        * Regarding the return channel: We now know that the confirmed inflight amount of this channel cannot be in
          the return channel. Thus, maximum liquidity needs to be lower than capacity minus in_flight amount.

        What can we learn from a failing onion?
        * In the channel, the maximum liquidity needs to be lower than the in_flights.
          We have no further information about the minimum amount that can be sent.
        * If this amount fails, then we know that at least this amount of liquidity is in the return channel.


        # This API works only if we have an Oracle that allows to ask the actual liquidity of a channel
        # In mainnet Lightning our oracle will not work on a per_channel level. This will change the data
        # flow. Here for simplicity of the simulation we make use of the Oracle on a per channel level

        :param amount: The amount that went through when probing the channel, usually in_flight amount plus attempt amount!
        :type: int
        :param return_channel: The UncertaintyChannel in the return direction, needed to adjust knowledge there.
        :type: UncertaintyChannel
        :param probing_successful: Could the amount be sent?
        :type: bool
        """
        if probing_successful:
            self.min_liquidity = max(self.min_liquidity, self.in_flight)
            if return_channel:
                return_channel.max_liquidity = min(return_channel.max_liquidity,
                                                   return_channel.capacity - self.min_liquidity)
            else:
                logging.debug(f"no return channel in UncertaintyNetwork for {self.short_channel_id}")
        elif not probing_successful:
            self.max_liquidity = min(self.max_liquidity, self.in_flight + amount - 1)
            if return_channel:
                return_channel.min_liquidity = max(return_channel.min_liquidity,
                                                   return_channel.capacity - self.max_liquidity)
            else:
                logging.debug(f"no return channel in UncertaintyNetwork for {self.short_channel_id}")
        else:
            logging.error("error in update knowledge - wrong status")

        if self.min_liquidity > self.max_liquidity:
            print("self min = max, {}, in {}-{}".format(self.min_liquidity, self.src[:4], self.dest[:4]))
            logging.error("self min = max, {}, in {}-{}".format(self.min_liquidity, self.src[:4], self.dest[:4]))
            exit(-10)
        if return_channel and return_channel.min_liquidity > return_channel.max_liquidity:
            print("return min = max, {}, in {}-{}".format(return_channel.min_liquidity, return_channel.src[:4],
                                                          return_channel.dest[:4]))
            logging.error("return min = max, {}, in {}-{}".format(return_channel.min_liquidity, return_channel.src[:4],
                                                                  return_channel.dest[:4]))
            exit(-20)

    # needed for BOLT14 test experiment
    def learn_n_bits(self, oracle: OracleLightningNetwork, n: int = 1):
        """
        conducts n probes of channel via binary search starting from our belief

        This of course only learns `n` bits if we use a uniform success probability as a prior
        thus this method will not work if a different prior success probability is assumed 
        """
        if n <= 0:
            return
        amt = self.min_liquidity + \
              int((self.max_liquidity - self.min_liquidity) / 2)
        oracle_channel = oracle.get_channel(
            self.src, self.dest, self.short_channel_id)
        success_of_probing = oracle_channel.can_forward(amt)
        self.update_knowledge(amt, success_of_probing)
        self.learn_n_bits(oracle, n - 1)
