import json
from json import JSONEncoder
import logging
import random
import sys

sys.path.append(r'../pickhardtpayments')
from pickhardtpayments.ChannelGraph import ChannelGraph
from pickhardtpayments.UncertaintyNetwork import UncertaintyNetwork
from pickhardtpayments.OracleLightningNetwork import OracleLightningNetwork
from pickhardtpayments.SyncPaymentSession import SyncPaymentSession
from Payment import Payment


def set_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s.%(msecs)03d | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.INFO)
    stdout_handler.setFormatter(formatter)
    file_handler = logging.FileHandler('pickhardt_pay.log', mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stdout_handler)


# subclass JSONEncoder
class PaymentEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__


set_logger()
logging.info('*** new payment simulation ***')

# *** Setup ***
# + Definition of network that serves as OracleLightningNetwork
# channel_graph = ChannelGraph("examples/channels.sample.json")
channel_graph = ChannelGraph("listchannels20220412.json")
uncertainty_network = UncertaintyNetwork(channel_graph)
oracle_lightning_network = OracleLightningNetwork(channel_graph)

nodes = {}

# + Definition of number of payments to be sent
number_of_payments = 10  # TODO how to decide on number of runs?

# + Definition of distribution of payment amounts
mean_payment_amount = 100_000


def payment_amount(amount=10_000_000) -> int:
    # TODO randomize payment amount if needed
    return amount


# + Definition of Strategies that the sending nodes act upon
def assign_strategy_to_nodes(node):
    """
    This method serves as a filter before choosing the path finding algorithm in '_generate_candidate_paths'.
    Currently, the only path finding algorithm used in the simulation is min_cost_flow.
    But the development goal is to have a switch as to how the paths for the onion are selected.
    This creates a state machine that allows to switch strategies.
    """
    # nodes is the set of nodes
    # node is the key
    # value is a tuple, consisting of current strategy ID and the number of rounds that the strategy has been used
    # a threshold can advance the strategy after a number of times the strategy has been called
    number_of_strategies = 2
    number_of_turns_before_strategy_rotation = 5
    if node not in nodes:
        nodes[node][0] = 0
        nodes[node][1] = 1
    else:
        logging.info('node found, strategy is %s', nodes[node][0])
        if nodes[node][1] % number_of_turns_before_strategy_rotation:
            nodes[node][1] += 1
        else:
            nodes[node][0] = (nodes[node][0] + 1) % number_of_strategies  # assuming two possible strategies
            nodes[node][1] = 0


def create_payment_set(_uncertainty_network, _number_of_payments, amount) -> list[Payment]:
    if (len(_uncertainty_network.network.nodes())) < 3:
        logging.warning("graph has less than two nodes")
        exit(-1)
    _payments = []
    while len(_payments) < _number_of_payments:
        # casting _channel_graph to list to avoid deprecation warning for python 3.9
        _random_nodes = random.sample(list(_uncertainty_network.network.nodes), 2)
        # additional check for existence; doing it here avoids the check in each round, improving runtime
        src_exists = _random_nodes[0] in _uncertainty_network.network.nodes()
        dest_exists = _random_nodes[1] in _uncertainty_network.network.nodes()
        if src_exists and dest_exists:
            p = Payment(_random_nodes[0], _random_nodes[1], payment_amount(amount))
            _payments.append(p)
    # write payments to file
    json_file = open("payments.json", "w")
    json.dump(_payments, json_file, indent=4, cls=PaymentEncoder)
    json_file.close()
    return _payments


# + Creation of a collection of N payments (src, rcv, amount)
# payment_set = create_payment_set(uncertainty_network, number_of_payments, mean_payment_amount)
# logging.debug("Payments:\n%s", json.dumps(payment_set, indent=4, cls=PaymentEncoder))

with open("payments.json") as jsonFile:
    payment_set = json.load(jsonFile)
    jsonFile.close()

logging.info("A total of {} payments.".format(len(payment_set)))

c = 0
for payment in payment_set:
    # create new payment session
    sim_session = SyncPaymentSession(oracle_lightning_network, uncertainty_network, prune_network=False)
    # we need to make sure we forget all learnt information on the Uncertainty Network
    sim_session.forget_information()  # TODO decide how often and when to forget information
    c += 1
    logging.info("*********** Payment {} ***********".format(c))
    logging.debug(f"now sending {payment['_total_amount']} sats from {payment['_sender']} to {payment['_receiver']}")

    sim_session.pickhardt_pay(payment['_sender'], payment['_receiver'], payment['_total_amount'], mu=0, base=0)

exit(0)

# we run the simulation of all pickhardt payments and track all the results
# for payment in payment_set:
# TODO register OracleLightningNetwork pre simulation
# TODO rework pay method to not only onionsend but pay


# TODO update OracleLightningNetwork to reflect payment (make sure back channel is also updated)
# TODO decide on method to save
# TODO register OracleLightningNetwork post simulation (and create diff OLN?)

logging.debug("""
SETUP
+ Definition of network that serves as OracleLightningNetwork
+ Definition of Strategies that the sending nodes act upon
+ Definition of number of runs
+ Definition of distribution of payment amounts
+ Creation of a collection of N payments (src, rcv, amount)

BEHAVIOUR
+ define strategy for routing: how many tries before calling it a failure (no route)
+ define when settlement failed, what to do next - retry or record failure

METRICS
+ what do we record when (and why)
""")
