"""Main OpenBazaard process"""
__author__ = 'chris', 'tobin'

import argparse
import requests
import sys

from daemon import OpenBazaard
from utils.platform_independent import options_tmp_path
from config import RESTAPI_PORT

# violates SPOT [Kernighan and Pike 99]
CONSTANTS = ['data_folder', 'ksize', 'alpha', 'transaction_fee',
             'libbitcoin_server', 'libbitcoin_server_testnet',
             'resolver', 'loglevel', 'testnet', 'daemon', 'network_port',
             'websocket_port', 'restapi_port', 'allowip', 'pidfile']
AUTHENTICATION = ['ssl', 'ssl_cert', 'ssl_key', 'username', 'password']


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

        _write_args_to_file(args)
        _print_splash()

        self.daemon.start()

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


def _print_splash():
    # pylint: disable=anomalous-backslash-in-string
    OKBLUE = '\033[94m'
    ENDC = '\033[0m'
    print "________             " + OKBLUE + "         __________" + ENDC
    print "\_____  \ ______   ____   ____" + OKBLUE + \
        "\______   \_____  _____________  _____ _______" + ENDC
    print " /   |   \\\____ \_/ __ \ /    \\" + OKBLUE +\
        "|    |  _/\__  \ \___   /\__  \ \__  \\\_  __ \ " + ENDC
    print "/    |    \  |_> >  ___/|   |  \    " + OKBLUE \
        + "|   \ / __ \_/    /  / __ \_/ __ \|  | \/" + ENDC
    print "\_______  /   __/ \___  >___|  /" + OKBLUE + "______  /(____  /_____ \(____  (____  /__|" + ENDC
    print "        \/|__|        \/     \/  " + OKBLUE + "     \/      \/      \/     \/     \/" + ENDC
    print
    print "OpenBazaar Server v0.1 starting..."


def _write_args_to_file(args):
    """
    Write command line options to file.

    File is temporary and in format accepted by ConfigParser
    """
    path = options_tmp_path()
    f = open(path, 'w+')
    print >>f, '[CONSTANTS]'
    for arg in vars(args):
        if getattr(args, arg):
               _write_to_file_with_predicate(args, arg, f, _is_constant)
    print >>f, '[AUTHENTICATION]'
    for arg in vars(args):
        if getattr(args, arg):
               _write_to_file_with_predicate(args, arg, f, _is_authentication)
               
    f.close()

def _write_to_file_with_predicate(args, arg, ofile, predicate):
    """Writes arg to ofile if predicate is true."""
    if predicate(arg):
                config_string = arg + ' = ' + str(getattr(args, arg))
                print >>ofile, config_string

def _is_constant(string):
    return string in CONSTANTS

def _is_authentication(string):
    return string in AUTHENTICATION


def _config_string_from_arg(args, arg):
    """Get string in correct config file format."""
    config_string = arg + ' = ' + str(getattr(args, arg))
    return config_string


if __name__ == "__main__":
    Parser()
