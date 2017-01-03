# -*- coding: UTF-8 -*-
import logging
import requests
from dnslib import QTYPE, RR

LOG = logging.getLogger(__name__)


class Upstream(object):
    def __init__(self, **kwa):
        self.endpoint = kwa.get('endpoint')
        self.timeout = float(kwa.get('timeout', 0.5))
        assert self.timeout > 0.0

    def __call__(self, context, question, reply):
        return self.handle(context, question, reply)

    def handle(self, context, question, reply):
        raise NotImplementedError()


class HttpUpstream(Upstream):
    """
    Delivers the request object to an upstream HTTP service and
    decodes the response object.
    """
    def __init__(self, **kwa):
        super(HttpUpstream, self).__init__(**kwa)
        self._method = str(kwa.get('method', 'GET'))
        if self._method not in ['GET', 'POST']:
            raise ValueError('"method" must be one of: GET, POST')
        self._session = requests.Session()

    def handle(self, context, question, reply):
        raise NotImplementedError()

    def request(self, data, url_suffix='', **extra):
        # XXX: timeout given to Requests may not be the absolute timeout
        #      so it could delay longer than the timeout..
        # TODO: multiple endpoints, fail-over?
        if self._method == 'GET':
            http_resp = self._session.get(
                self.endpoint + url_suffix,
                params=data,
                timeout=self.timeout,
                **extra)
        elif self._method == 'POST':
            http_resp = self._session.post(
                self.endpoint + url_suffix,
                data=data,
                timeout=self.timeout,
                **extra)
        else:
            raise RuntimeError('Invalid HTTP method "%s"' % (self._method,))

        http_resp.raise_for_status()
        return http_resp


class GoogleDnsHttpUpstream(HttpUpstream):
    """
    Documentation:
     - https://developers.google.com/speed/public-dns/docs/dns-over-https

    XXX: how is Google's implementation different from DNS over HTTPS?
     - https://tools.ietf.org/html/draft-hoffman-dns-over-http-00
    """
    def __init__(self, **kwa):
        if 'endpoint' not in kwa:
            kwa['endpoint'] = 'https://dns.google.com/resolve'
        kwa['method'] = 'GET'
        super(GoogleDnsHttpUpstream, self).__init__(**kwa)

    def handle(self, context, question, reply):
        qname = str(question.qname)
        qtype = QTYPE[question.qtype]

        resp = self.request(dict(
            name=qname,
            type=qtype
        )).json()

        status = int(resp.get('Status'))
        answer_list = resp.get('Answer')
        if status:
            reply.header.rcode = status
            return status

        for answer in answer_list:
            if answer['type'] == 257:  # XXX: what is 257? And why skip...
                continue

            zone_record = str(' '.join([
                answer['name'],
                str(answer['TTL']),
                'IN',
                QTYPE[answer['type']],
                answer['data']
            ]))
            reply.add_answer(*RR.fromZone(zone_record))
        return reply
