# -*- coding: UTF-8 -*-
import logging
import struct
from dnslib import RCODE, DNSError, DNSRecord
from gevent.server import DatagramServer, StreamServer

LOG = logging.getLogger(__name__)


class ServerBase(object):
    truncate = False

    def __init__(self, router, server):
        server.set_handle(self.handle)
        self._server = server
        self._router = router

    # XXX: The Server methods shouldn't be here
    # TODO: refactor, split into server and handler...

    @property
    def started(self):
        return self._server.started

    @property
    def closed(self):
        return self._server.started

    def start(self):
        return self._server.start()

    def stop(self):
        return self._server.stop()

    def close(self):
        return self._server.close()

    def serve_forever(self, stop_timeout=None):
        return self._server.serve_forever(stop_timeout)

    def handle(self, socket, address):
        raise NotImplementedError()

    def resolve(self, request, context):
        if len(request.questions) != 1:
            # Whilst the packet format technically supports having more than
            # one record in the question section (see §4.1.2 of RFC 1035), in
            # practise it just doesn't work, as you've found. In particular
            # no-one has ever managed to define correct semantics for what to
            # do if the two questions were to result in two different RCODEs.
            reply = request.reply()
            reply.header.rcode = getattr(RCODE, 'NOTIMP')
            return reply

        try:
            return self._router.dispatch(request, context)

        except Exception:
            LOG.exception("While dispatching router")
            reply = request.reply()
            reply.header.rcode = getattr(RCODE, 'SERVFAIL')
            return reply

    def get_reply(self, data, address):
        request = DNSRecord.parse(data)
        context = dict(
            _client=dict(
                ip=address[0],
                port=address[1],
                proto=self.protocol,
            )
        )
        LOG.debug('Received request for %r from %r', request, address)
        reply = self.resolve(request, context)
        LOG.debug('Responding to %r with %r', request, reply)
        rdata = reply.pack()
        if self.truncate and len(rdata) > self.truncate:
            truncated_reply = reply.truncate()
            rdata = truncated_reply.pack()
        return rdata


class BaseTCPServer(ServerBase):
    protocol = 'tcp'

    def handle(self, socket, address):
        data = socket.recv(8192)
        length = struct.unpack("!H", bytes(data[:2]))[0]
        while len(data) - 2 < length:
            data += socket.recv(8192)
        data = data[2:]

        try:
            rdata = self.get_reply(data, address)
            rdata = struct.pack("!H", len(rdata)) + rdata
            socket.sendall(rdata)
        except DNSError:
            LOG.exception("While handling TCP response")


class BaseUDPServer(ServerBase):
    protocol = 'udp'

    def handle(self, data, address):
        try:
            rdata = self.get_reply(data, address)
            self._server.sendto(rdata, address)
        except DNSError:
            LOG.exception("While handling UDP response")


class TCPServer(BaseTCPServer):
    def __init__(self, router, listener):
        server = StreamServer(listener, handle=self.handle)
        super(TCPServer, self).__init__(router, server)


class UDPServer(BaseUDPServer):
    def __init__(self, router, listener):
        server = DatagramServer(listener, handle=self.handle)
        super(UDPServer, self).__init__(router, server)
