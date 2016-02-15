import os
from os.path import join, isfile
from ConfigParser import ConfigParser
from urlparse import urlparse

from utils.platform_independent import data_path, options_tmp_path,\
    pid_path
form utils.string import str_to_bool


PROTOCOL_VERSION = 13

MAINNET_PORT = 18467
TESTNET_PORT = 28467

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
}


class Parser(object):
    def __init__(self):
        self.daemon = OpenBazaard()
        parser = argparse.ArgumentParser(
            description='OpenBazaar-Server v0.1.0',
            usage='''
    python openbazaard.py <command> [<args>]
    python openbazaard.py <command> --help

commands:
    start            start the OpenBazaar server
    stop             shutdown the server and disconnect
    restart          restart the server
            ''')
        parser.add_argument('command', help='Execute the given command')
        args = parser.parse_args(sys.argv[1:2])
        if not hasattr(self, args.command):
            parser.print_help()
            exit(1)
        getattr(self, args.command)()

    def start(self):
        parser = argparse.ArgumentParser(
            description="Start the OpenBazaar server",
            usage="python openbazaard.py start [<args>]"
        )
        parser.add_argument('-d', '--daemon', action='store_true',
                            help="run the server in the background as a daemon")
        parser.add_argument('-t', '--testnet', action='store_true',
                            help="use the test network")
        parser.add_argument('-s', '--ssl', action='store_true',
                            help="use ssl on api connections. you must set the path to your "
                                 "certificate and private key in the config file.")
        parser.add_argument('-l', '--loglevel',
                            help="set the logging level [debug, info, warning, error, critical]")
        parser.add_argument('-p', '--network_port',
                            help="set the network port")
        parser.add_argument('-r', '--restapi_port',
                            help="set the rest api port")
        parser.add_argument('-w', '--websocket_port',
                            help="set the websocket api port")
        parser.add_argument('-b', '--heartbeat_port',
                            help="set the heartbeat port")
        parser.add_argument('-a', '--allowip',
                            help="only allow api connections from this ip")
        parser.add_argument('--pidfile',
                            help="name of the pid file")
        args = parser.parse_args(sys.argv[2:])
        options = _dict_from_args(args)
        _store_config_with_options(options)
        exit(1)
#        self.daemon.start()

    def stop(self):
        # pylint: disable=W0612
        parser = argparse.ArgumentParser(
            description="Shutdown the server and disconnect",
            usage='''usage:
    python openbazaard.py stop''')
        parser.parse_args(sys.argv[2:])
        print "OpenBazaar server stopping..."
        try:
            request = 'http://localhost:' + RESTAPI_PORT + '/api/v1/shutdown'
            requests.get(request)
        except Exception:
            self.daemon.stop()

    def restart(self):
        # pylint: disable=W0612
        parser = argparse.ArgumentParser(
            description="Restart the server",
            usage='''usage:
    python openbazaard.py restart''')
        parser.parse_args(sys.argv[2:])
        print "Restarting OpenBazaar server..."
        self.daemon.restart()


def _dict_from_args(args):
    """Return dictionary of option:value for set options."""
    options = {}
    for arg in vars(args):
        if getattr(args, arg):
            options[arg] = str(getattr(args, arg))

    return options


def _store_config_with_options(options):
    """Store current configuration to database."""
    cfg = _cfg_with_options(options)
    outf = instance_config_path()
    cfg.write(outf)


def _cfg_with_options(options):
    """Parse config file hierarchy and options."""
    cfg = _initialise_cfg()
    cfg = _parse_config_files(cfg)
    cfg = _set_cfg_options(cfg, options)
    

def _initialise_cfg():
    cfg = ConfigParser(DEFAULTS)
    cfg.add_section('CONSTANTS')
    cfg.add_section('AUTHENTICATION')

    return cfg
    

def _parse_config_files(cfg):
    """Parse config file hierarchy."""
    config_files = ordered_config_files()

    for f in config_files:
        if isfile(f):
            cfg.read(f)

    return cfg


def _set_cfg_options(cfg, options):
    """Allow command line options to override config."""
    auth = ['ssl', 'ssl_cert', 'ssl_key', 'username', 'password']
    
    for key, value in options.iteritems():
        section = 'CONSTANTS'
        if key in auth:
            section = 'AUTHENTICATION'
        try:
            cfg.set(section, key, value)
