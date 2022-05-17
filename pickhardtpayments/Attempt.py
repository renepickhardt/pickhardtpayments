class Attempt:
    """
    An Attempt describes a path (a set of channels) of an amount from sender to receiver.

    :param list _path: a list of UncertaintyChannel objects from sender to receiver
    :param int _amount: the amount to be transferred from source to destination
    :param int _routing_fee: the rounting fee in msat
    :param float _probability: the success probability from
    :param int _runtime: the number of milliseconds for the path to be found
    :param boolean _success: the flag to describe if the path succeeded (True) or failed (False) for the amount in flight
    """
