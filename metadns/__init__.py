# -*- coding: UTF-8 -*-
from __future__ import print_function
import logging
import gevent.monkey

gevent.monkey.patch_all()

from .server import UDPServer
from .router import DNSRouter


LOG = logging.getLogger(__name__)


class MetaDNS(object):
    def __init__(self, config):
        self._options = config['options']
        self._router = DNSRouter.create_from_config(config)

    def run(self):
        options = self._options
        server = UDPServer(self._router, (options['address'], options['port']))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
