# -*- coding: UTF-8 -*-
import gevent.monkey
gevent.monkey.patch_all()

from .server import UDPServer


class Resolver(object):
    def __call__(self, context, question, reply):
        return self.resolve(context, question, reply)

    def resolve(self, context, question, reply):
        raise NotImplementedError()


class MetaDNS(object):
    def __init__(self, config):
        self._options = config.options
        self._router = config.router

    def run(self):
        options = self._options
        server = UDPServer(self._router, (options.address, options.port))
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
