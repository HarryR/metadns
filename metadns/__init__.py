# -*- coding: UTF-8 -*-
from __future__ import print_function
import logging
import gevent.monkey

gevent.monkey.patch_all()

from .server import UDPServer
from .router import DNSRouter


LOG = logging.getLogger(__name__)


class MetaDNS(object):
    def __init__(self, args, config):        
        self._args = args
        self._router = DNSRouter.create_from_config(config)

    def run(self):
        args = self._args
        server = UDPServer(self._router, (args.address, args.port))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
