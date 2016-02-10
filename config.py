"""Parses configuration file and sets project wide constants."""

__author__ = 'foxcarlos-TeamCreed', 'tobin'

import os
from os.path import join, isfile
from ConfigParser import ConfigParser
from urlparse import urlparse

from utils.platform_independent import data_path, options_tmp_path,\
    pid_path
form utils.string import str_to_bool

PROTOCOL_VERSION = 13
CONFIG_FILE = join(os.getcwd(), 'ob.cfg')
MAINNET_PORT = 18467
TESTNET_PORT = 28467

# FIXME probably a better way to do this. This curretly checks two levels deep
for i in range(2):
    if not isfile(CONFIG_FILE):
        paths = CONFIG_FILE.rsplit('/', 2)
        CONFIG_FILE = join(paths[0], paths[2])

DEFAULTS = {
    'data_folder': None,
    'ksize': '20',
    'alpha': '3',
    'transaction_fee': '10000',
    'libbitcoin_server': 'tcp://libbitcoin1.openbazaar.org:9091',
    'libbitcoin_server_testnet': 'tcp://libbitcoin2.openbazaar.org:9091',
    'resolver': 'http://resolver.onename.com/',
    'loglevel': 'info',
    'testnet': 'True',
    'daemon': 'False',
    'network_port': '0',
    'websocket_port': '18466',
    'restapi_port': '18469',
    'heartbeat_port': '18470',
    'allowip' : '127.0.0.1',
    'pidfile' : None,

    # Authentication
    'ssl': 'False',
    'ssl_cert': None,
    'ssl_key': None,
    'username': None,
    'password': None,
    #seeds
    'seed': 'seed.openbazaar.org:8080,5b44be5c18ced1bc9400fe5e79c8ab90204f06bebacc04dd9c70a95eaca6e117',
}

def _is_well_formed_seed_string(string):
    """Parse string url:port,key."""
    if ',' in string:
        url, key = string.split(',')
        parsed = urlparse(url)
        if _validate_url(parsed.geturl()):
            if _validate_key(key):
                return True

    return False


def _validate_url(url):
    # TODO (How tight should the configuration requirements for a url be?)
    return True


def _validate_key(key):
    # TODO (is this done elsewhere in the project?)
    return True


def _is_seed_tuple(tup):
    if isinstance(tup, tuple):
        return 'seed' in tup[0]

    return False


def _tuple_from_seed_string(string):
    """Accepts well formed seed string, returns tuple (url:port, key)."""
    return tuple(string.split(','))


def _is_well_formed_data_path(path):
    """Path is well formed if absolute and it exists."""
    if path:
        if os.path.isabs(path):
            if os.path.exists(path):
                return True

    return False


cfg = ConfigParser(DEFAULTS)

if isfile(CONFIG_FILE):
    cfg.read(CONFIG_FILE)
else:
    print 'Warning: configuration file not found: (%s), using default values' % CONFIG_FILE

options = options_tmp_path()
if isfile(options):
    cfg.read(options)

DATA_FOLDER = ''
config_data_path = cfg.get('CONSTANTS', 'DATA_FOLDER')
if _is_well_formed_data_path(config_data_path):
    DATA_FOLDER = join(config_data_path, '')
else:
    DATA_FOLDER = data_path()

KSIZE = int(cfg.get('CONSTANTS', 'KSIZE'))
ALPHA = int(cfg.get('CONSTANTS', 'ALPHA'))
TRANSACTION_FEE = int(cfg.get('CONSTANTS', 'TRANSACTION_FEE'))
LIBBITCOIN_SERVER = cfg.get('CONSTANTS', 'LIBBITCOIN_SERVER')
LIBBITCOIN_SERVER_TESTNET = cfg.get('CONSTANTS', 'LIBBITCOIN_SERVER_TESTNET')
RESOLVER = cfg.get('CONSTANTS', 'RESOLVER')
LOGLEVEL = cfg.get('CONSTANTS', 'LOGLEVEL')
TESTNET = str_to_bool(cfg.get('CONSTANTS', 'TESTNET'))
DAEMON = str_to_bool(cfg.get('CONSTANTS', 'DAEMON'))
ALLOWIP = cfg.get('CONSTANTS', 'ALLOWIP')

user_defined_pidfile = cfg.get('CONSTANTS', 'PIDFILE')
PIDFILE = ''
if user_defined_pidfile:
    PIDFILE = user_defined_pidfile
else:
    PIDFILE = pid_path()
    
NETWORK_PORT = 0
user_defined_network_port = int(cfg.get('CONSTANTS', 'NETWORK_PORT'))
if user_defined_network_port:
    NETWORK_PORT = user_defined_network_port
elif TESTNET:
    NETWORK_PORT = TESTNET_PORT
else:
    NETWORK_PORT = MAINNET_PORT

WEBSOCKET_PORT = int(cfg.get('CONSTANTS', 'WEBSOCKET_PORT'))
RESTAPI_PORT = int(cfg.get('CONSTANTS', 'RESTAPI_PORT'))
HEARTBEAT_PORT = int(cfg.get('CONSTANTS', 'HEARTBEAT_PORT'))
SSL = str_to_bool(cfg.get('AUTHENTICATION', 'SSL'))
SSL_CERT = cfg.get('AUTHENTICATION', 'SSL_CERT')
SSL_KEY = cfg.get('AUTHENTICATION', 'SSL_KEY')
USERNAME = cfg.get('AUTHENTICATION', 'USERNAME')
PASSWORD = cfg.get('AUTHENTICATION', 'PASSWORD')

SEEDS = []

items = cfg.items('SEEDS')  # this also includes items in DEFAULTS
for item in items:
    if _is_seed_tuple(item):
        seed_string = item[1]
        if _is_well_formed_seed_string(seed_string):
            new_seed = _tuple_from_seed_string(seed_string)
            if new_seed not in SEEDS:
                SEEDS.append(new_seed)
        else:
            print 'Warning: please check your configuration file: %s' % seed_string


def get_value(section, name):
    config = ConfigParser()
    if isfile(CONFIG_FILE):
        config.read(CONFIG_FILE)
        return config.get(section, name)


if __name__ == '__main__':

    def test_is_well_formed_seed_string():
        well_formed = 'seed.openbazaar.org:8080,5b44be5c18ced1bc9400fe5e79c8ab90204f06bebacc04dd9c70a95eaca6e117'
        # test ill-formed url's (build fails with pylint error if we use long/descriptive names
        # key too short
        # bad_1 = 'seed.openbazaar.org:8080,5b44be5c18ced1bc9400fe5e79'
        # no port number
        # bad_2 = 'seed.openbazaar.org,5b44be5c18ced1bc9400fe5e79c8ab90204f06bebacc04dd9c70a95eaca6e117'
        # no host name in url
        # bad_3 = 'openbazaar.org:8080,5b44be5c18ced1bc9400fe5e79c8ab90204f06bebacc04dd9c70a95eaca6e117'

        assert _is_well_formed_seed_string(well_formed)
        # assert not _is_well_formed_seed_string(b1)
        # assert not _is_well_formed_seed_string(b2)
        # assert not _is_well_formed_seed_string(b3)

    def test_is_seed_tuple():
        good = ('seed.openbazaar.org:8080', '5b44be5c18ced1bc9400fe5e79c8ab90204f06bebacc04dd9c70a95eaca6e117')
        bad_not_tuple = 'seed.openbazaar.org:8080,5b44be5c18ced1bc9400fe5e79c8ab90204f06bebacc04dd9c70a95eaca6e117'
        bad_not_seed_tuple = ('aoioai', 'aoioai')
        assert _is_seed_tuple(good)
        assert not _is_seed_tuple(bad_not_tuple)
        assert not _is_seed_tuple(bad_not_seed_tuple)


    test_is_well_formed_seed_string()
    test_is_seed_tuple()
