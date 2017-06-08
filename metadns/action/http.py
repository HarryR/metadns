# -*- coding: UTF-8 -*-
from dnslib import QTYPE, RR
from metadns.httputil import HttpUpstream
from metadns import Resolver


class GoogleDnsHttpResolver(HttpUpstream, Resolver):
    """
    Documentation:
     - https://developers.google.com/speed/public-dns/docs/dns-over-https

    XXX: how is Google's implementation different from DNS over HTTPS?
     - https://tools.ietf.org/html/draft-hoffman-dns-over-http-00
    """
    def __init__(self, **kwa):
        if 'url' not in kwa:
            kwa['url'] = 'https://dns.google.com/resolve'
        kwa['method'] = 'GET'
        super(GoogleDnsHttpResolver, self).__init__(**kwa)

    def resolve(self, context, question, reply):
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
                'IN',  # IN is implicit, as per documentation
                QTYPE[answer['type']],
                answer['data']
            ]))
            reply.add_answer(*RR.fromZone(zone_record))
        return reply
