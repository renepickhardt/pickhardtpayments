class Payment:
    """
    Payment stores the information about an amount of sats to be delivered from source to destination.

    When sending an amount of sats from sender to receiver, a payment is usually split up and sent across
    several paths, to increase the probability of being successfully delivered.
    The PaymentClass holds all necessary information about a payment.
    It also holds information that helps to calculate performance statistics about the payment.

    :param int _total_amount: The total amount of sats to be delivered from source address to destination address.
    :param str _sender: sender address for the payment.
    :param str _receiver: receiver address for the payment.
    :param list _attempts: returns a list of Attempts
    :param list _successful_attempts: returns a list of successful Attempts
    :param bool _successful: returns True if the total_amount of the payment could be delivered successfully.
    """

    def __init__(self):
        self._attempts = []
        self._successful_attempts = []

    @property
    def total_amount(self):
        return self._total_amount

    @property
    def src(self):
        return self._sender

    @property
    def dest(self):
        return self._receiver

    @property
    def attempts(self):
        return self._attempts

    @property
    def successful_attempts(self):
        return self._successful_attempts

    @property
    def successful(self):
        return self._successful
