# -*- coding: utf-8 -*-
import copy
from metadns import Resolver
from dnslib import RR,QTYPE,RCODE

class ZoneResolver(Resolver):
    def __init__(self, **kwa):
        self.ttl = int(kwa.get('ttl', 0))
        self.origin = kwa.get('origin')

        self.glob = bool(kwa.get('glob'))
        self.eq = 'matchGlob' if self.glob else '__eq__'

        # Zone can be a string, or a list of strings
        zone_str = kwa.get('zone')
        if isinstance(zone_str, list):
            zone_str = "\n".join(zone_str)

        # Or loaded from a file
        zone_file = kwa.get('file')
        if zone_file:
            zone_str = open(zone_file, 'r').read()

        self.zone = [(rr.rname, QTYPE[rr.rtype], rr)
                     for rr in RR.fromZone(zone_str, origin=self.origin, ttl=self.ttl)]

    def resolve(self, context, question, reply):
        """
        Respond to DNS request - parameters are request packet & handler.
        Method is expected to return DNS response
        """
        qname = question.qname
        qtype = QTYPE[question.qtype]
        for name, rtype, rr in self.zone:
            # Check if label & type match
            if getattr(qname, self.eq)(name) and (qtype == rtype or 
                                                  qtype == 'ANY' or 
                                                  rtype == 'CNAME'):
                # If we have a glob match fix reply label
                if self.glob:
                    a = copy.copy(rr)
                    a.rname = qname
                    reply.add_answer(a)
                else:
                    reply.add_answer(rr)
                # Check for A/AAAA records associated with reply and
                # add in additional section
                if rtype in ['CNAME', 'NS', 'MX', 'PTR']:
                    for a_name, a_rtype, a_rr in self.zone:
                        if a_name == rr.rdata.label and a_rtype in ['A', 'AAAA']:
                            reply.add_ar(a_rr)
        if not reply.rr:
            return None
        return reply
