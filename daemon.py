__author__ = 'chris'
import sys
import os
import time
import atexit
import socket
import stun
from signal import SIGTERM

from obelisk.client import LibbitcoinClient
from protos.objects import FULL_CONE, RESTRICTED, SYMMETRIC
from twisted.internet import reactor, task
from twisted.python import log, logfile
from txws import WebSocketFactory

from api.ws import WSFactory
from api.restapi import RestAPI
from db.datastore import Database
from dht.network import Server
from dht.node import Node
from dht.storage import PersistentStorage, ForgetfulStorage
from keys.keychain import KeyChain
from log import Logger, FileLogObserver
from market import network
from market.listeners import MessageListenerImpl, BroadcastListenerImpl, NotificationListenerImpl
from market.contracts import check_unfunded_for_payment
from market.profile import Profile
from net.sslcontext import ChainedOpenSSLContextFactory
from net.upnp import PortMapper
from net.utils import looping_retry
from net.wireprotocol import OpenBazaarProtocol
from utils.platform_independent import pid_path
from config import DATA_FOLDER, KSIZE, ALPHA, LIBBITCOIN_SERVER,\
    LIBBITCOIN_SERVER_TESTNET, SSL_KEY, SSL_CERT, SEEDS, TESTNET,\
    LOGLEVEL, NETWORK_PORT, ALLOWIP, SSL, RESTAPI_PORT, WEBSOCKET_PORT,\
    HEARTBEAT_PORT, DAEMON, PIDFILE


def run(*args):

    _print_splash()
    def start_server(keys, first_startup=False):
        # logging
        logFile = logfile.LogFile.fromFullPath(DATA_FOLDER + "debug.log", rotateLength=15000000, maxRotatedFiles=1)
        log.addObserver(FileLogObserver(logFile, level=LOGLEVEL).emit)
        log.addObserver(FileLogObserver(level=LOGLEVEL).emit)
        logger = Logger(system="OpenBazaard")

        # NAT traversal
        p = PortMapper()
        p.add_port_mapping(NETWORK_PORT, NETWORK_PORT, "UDP")
        logger.info("Finding NAT Type...")

        response = looping_retry(stun.get_ip_info, "0.0.0.0", NETWORK_PORT)

        logger.info("%s on %s:%s" % (response[0], response[1], response[2]))
        ip_address = response[1]
        port = response[2]

        if response[0] == "Full Cone":
            nat_type = FULL_CONE
        elif response[0] == "Restric NAT":
            nat_type = RESTRICTED
        else:
            nat_type = SYMMETRIC

        def on_bootstrap_complete(resp):
            logger.info("bootstrap complete")
            mserver.get_messages(mlistener)
            task.LoopingCall(check_unfunded_for_payment, db, libbitcoin_client, nlistener, TESTNET).start(600)

        protocol = OpenBazaarProtocol((ip_address, port), nat_type, testnet=TESTNET,
                                      relaying=True if nat_type == FULL_CONE else False)

        # kademlia
        storage = ForgetfulStorage() if TESTNET else PersistentStorage(db.get_database_path())
        relay_node = None
        if nat_type != FULL_CONE:
            for seed in SEEDS:
                try:
                    relay_node = (socket.gethostbyname(seed[0].split(":")[0]),
                                  28469 if TESTNET else 18469)
                    break
                except socket.gaierror:
                    pass

        try:
            kserver = Server.loadState(DATA_FOLDER + 'cache.pickle', ip_address, port, protocol, db,
                                       nat_type, relay_node, on_bootstrap_complete, storage)
        except Exception:
            node = Node(keys.guid, ip_address, port, keys.verify_key.encode(),
                        relay_node, nat_type, Profile(db).get().vendor)
            protocol.relay_node = node.relay_node
            kserver = Server(node, db, keys.signing_key, KSIZE, ALPHA, storage=storage)
            kserver.protocol.connect_multiplexer(protocol)
            kserver.bootstrap(kserver.querySeed(SEEDS)).addCallback(on_bootstrap_complete)
        kserver.saveStateRegularly(DATA_FOLDER + 'cache.pickle', 10)
        protocol.register_processor(kserver.protocol)

        # market
        mserver = network.Server(kserver, keys.signing_key, db)
        mserver.protocol.connect_multiplexer(protocol)
        protocol.register_processor(mserver.protocol)

        looping_retry(reactor.listenUDP, port, protocol)

        interface = "0.0.0.0" if ALLOWIP not in ("127.0.0.1", "0.0.0.0") else ALLOWIP

        # websockets api
        authenticated_sessions = []
        ws_api = WSFactory(mserver, kserver, only_ip=ALLOWIP)
        ws_factory = AuthenticatedWebSocketFactory(ws_api)
        ws_factory.authenticated_sessions = authenticated_sessions
        ws_factory.protocol = AuthenticatedWebSocketProtocol
        if SSL:
            reactor.listenSSL(WEBSOCKET_PORT, ws_factory,
                              ChainedOpenSSLContextFactory(SSL_KEY, SSL_CERT), interface=interface)
        else:
            reactor.listenTCP(WEBSOCKET_PORT, ws_factory, interface=interface)

        # rest api
        rest_api = RestAPI(mserver, kserver, protocol, username, password,
                           authenticated_sessions, only_ip=ALLOWIP)
        if SSL:
            reactor.listenSSL(REST_PORT, rest_api,
                              ChainedOpenSSLContextFactory(SSL_KEY, SSL_CERT), interface=interface)
        else:
            reactor.listenTCP(REST_PORT, rest_api, interface=interface)

        # blockchain
        if TESTNET:
            libbitcoin_client = LibbitcoinClient(LIBBITCOIN_SERVER_TESTNET, log=Logger(service="LibbitcoinClient"))
        else:
            libbitcoin_client = LibbitcoinClient(LIBBITCOIN_SERVER, log=Logger(service="LibbitcoinClient"))

        # listeners
        nlistener = NotificationListenerImpl(ws_api, db)
        mserver.protocol.add_listener(nlistener)
        mlistener = MessageListenerImpl(ws_api, db)
        mserver.protocol.add_listener(mlistener)
        blistener = BroadcastListenerImpl(ws_api, db)
        mserver.protocol.add_listener(blistener)

        protocol.set_servers(ws_api, libbitcoin_client)

        if first_startup:
            heartbeat_server.push(json.dumps({
                "status": "GUID generation complete",
                "username": username,
                "password": password
            }))

        heartbeat_server.set_status("online")

        logger.info("Startup took %s seconds" % str(round(time.time() - args[8], 2)))

    # database
    db = Database(TESTNET)

    # client authentication
    username, password = get_credentials(db)

    # heartbeat server
    interface = "0.0.0.0" if ALLOWIP not in ("127.0.0.1", "0.0.0.0") else ALLOWIP
    heartbeat_server = HeartbeatFactory(only_ip=ALLOWIP)
    if SSL:
        reactor.listenSSL(HEARTBEATPORT, WebSocketFactory(heartbeat_server),
                          ChainedOpenSSLContextFactory(SSL_KEY, SSL_CERT), interface=interface)
    else:
        reactor.listenTCP(HEARTBEATPORT, WebSocketFactory(heartbeat_server), interface=interface)

    # key generation
    KeyChain(db, start_server, heartbeat_server)

    reactor.run()


def _print_splash():
    # pylint: disable=anomalous-backslash-in-string
    okblue = '\033[94m'
    endc = '\033[0m'
    print "________             " + okblue + "         __________" + endc
    print "\_____  \ ______   ____   ____" + okblue + \
        "\______   \_____  _____________  _____ _______" + endc
    print " /   |   \\\____ \_/ __ \ /    \\" + okblue +\
        "|    |  _/\__  \ \___   /\__  \ \__  \\\_  __ \ " + endc
    print "/    |    \  |_> >  ___/|   |  \    " + okblue \
        + "|   \ / __ \_/    /  / __ \_/ __ \|  | \/" + endc
    print "\_______  /   __/ \___  >___|  /" + okblue,
    print "______  /(____  /_____ \(____  (____  /__|" + endc
    print "        \/|__|        \/     \/  " + okblue,
    print "     \/      \/      \/     \/     \/" + endc
    print
    print "OpenBazaar Server v0.1 starting..."
