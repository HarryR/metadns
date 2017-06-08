# -*- coding: UTF-8 -*-

import json

from metadns import Resolver
from metadns.httputil import JSONRPCProxy
from .zone import ZoneResolver


def make_list(var):
    if isinstance(var, (list, set)):
        return var
    return [var]


class INamecoinNamespace(object):
    def lookup(self, namespaced_name):
        raise NotImplementedError()


class NamecoinNamespaceJSONRPC(INamecoinNamespace):
    """
    Retrieves DNS dictionary information in Namecoin format by querying the 
    JSON-RPC service of a Namecoin daemon.
    """

    def __init__(self, **kwa):
        if 'url' not in kwa:
            kwa['url'] = 'http://localhost:8443/'
        kwa['method'] = 'POST'
        self._rpc = JSONRPCProxy(**kwa)

    def lookup(self, namespaced_name):
        """
        Retrieve Domain Name data from Namecoin daemon via JSON-RPC
        namespaced_name must include the "s/" or "d/" namespace prefix
        :returns int, dict: absolute expiry time, dns data dict
        """
        # TODO: cache responses, avoid another JSON-RPC name_show lookup
        data = self._rpc.name_show(namespaced_name)
        max_ttl = int(data.get('expires_in'))
        if max_ttl > 0:
            try:
                return max_ttl, json.loads(data.get('value'))
            except ValueError:
                return None


def namecoin_walk(namespace, root, subdomains=None, current=None, escape=20):
    """
    Traverse the Namecoin DNS structures and return the dict matching the name
    Recursive function, saves root, walks subdomains with current level
    Avoids infinite recursion by decrementing 'escape' parameter
    """
    if root is None:
        return None
    if escape <= 0:
        raise RuntimeError("Namecoin resolver reached escape velocity!")
    if current is None:
        current = root

    if 'delegate' in current or isinstance(current, list):
        """
        Delegates control of this domain to the given Namecoin name, or a
        sub-domain entry defined within that name. All other entries are
        ignored. See: https://wiki.namecoin.info/?title=Domain_Name_Specification_2.0#Importing_and_delegation

        Sub-domains can be referenced through a second item in the array,
        using the sub-domain reference notation. So, ["s/example001"] and
        ["s/example001", ""] refer to the same data.
        """
        delegate = current['delegate']
        assert isinstance(delegate, list)
        delegate_sub = None
        if len(delegate) > 1:
            delegate_sub = delegate[1]
        delegate_top = delegate[0]

        # New namespace replaces current
        root = current = namespace.lookup(delegate_top)
        if current is None:
            raise RuntimeError("Failed to lookup delegated name " + delegate)

        if delegate_sub:
            # Sub-domain prepended to list
            if not subdomains:
                subdomains = []
            subdomains = [delegate_sub] + subdomains

        # Process an immediate delegate...
        if 'delegate' in current:
            return namecoin_walk(namespace, root, subdomains, current, escape - 1)

    # TODO: support 'import' and 'translate', as they override others
    # For 'translate', need to resolve a namespace and replace current root
    # TODO: 'alias'

    if not subdomains:  # End of the chain        
        return current
    assert isinstance(subdomains, list)

    sub_map = current.get('map')
    if not sub_map:
        # XXX: what to do here? Return NXDOMAIN?
        raise RuntimeError("Could not find maps, subdomains remaining!")

    sub_data = sub_map.get(subdomains[0])
    return namecoin_walk(namespace, root, subdomains[1:], sub_data, escape - 1)


def namecoin_dict_to_zone(origin, name, namecoin_dict, ttl=3600):
    if origin[-1] != '.':
        origin += '.'

    zone = [
        "$ORIGIN " + origin,
        "$TTL " + str(ttl),
    ]

    # TODO: validate values depending on their type
    for key, data in namecoin_dict.items():
        if name == '':
            name = '@'        
        if key == "ip":
            for value in make_list(data):
                zone.append("%s IN A %s" % (name, value))
        elif key == "ip6":
            for value in make_list(data):
                zone.append("%s IN AAAA %s" % (name, value))
        elif key in ["tor", "i2p"]:
            # XXX: returning CNAME for both tor and i2p will round-robin
            #      requests to one of them, rather than fail-over to whichever 
            #      one is available.
            for value in make_list(data):
                zone.append("%s IN CNAME %s" % (name, value))
        elif key == "service":
            for service, proto, prio, weight, port, target in value:
                zone.append("_%s._%s.%s IN SRV %d %d %d %s" % (
                    service, proto, name,
                    prio, weight, port, target))
        elif key in ["dns", "ns"]:
            zone.append("%s IN NS %s" % (name, value))

        # XXX: freenet does not correspond to a DNS record
        # XXX: LOC not supported by dnslib - https://en.wikipedia.org/wiki/LOC_record
        # TODO: "tls" (TLSA/DANE) record support
        #  - TLSA/DANE - https://tools.ietf.org/html/rfc6698
        #  - See: https://forum.namecoin.org/viewtopic.php?f=5&t=1137

    return "\n".join(zone)


def namecoin_resolve(dns_root_name, namecoin_name, subdomains, namespace):
    pass


class NamecoinResolver(Resolver):
    """
    The Namecoin resolver responds to DNS queries by looking up the name in 
    Namecoin and translating the JSON dictionary into a DNS response.

    JSON-RPC API
    - https://wiki.namecoin.info/index.php?title=Client_API

    Specification for values
    - https://wiki.namecoin.info/?title=Domain_Name_Specification_2.0

    okTurtles Blockchain resolver, implements NMC specification
    - https://github.com/okTurtles/dnschain/blob/master/src/lib/blockchain.coffee

    NamecoinToBind NMC to Zone translator
    - https://github.com/khalahan/NamecoinToBind/blob/master/name.class.php

    Namecoin pipe backend for PowerDNS
    - http://www.average.org/pdns-pipe-nmc/

    TinyDNS zone generator
    - https://github.com/tkooda/namecoin-tinydns-data
    """
    def __init__(self, **kwa):
        self._namespace = NamecoinNamespaceJSONRPC(**kwa)

    def _extract_name(self, context, qname):
        """
        Extract top-level domain and subdomains from queried name
        """
        if 'name' in context:
            qname = context['name']
        else:
            # When the domain name isn't provided in the context
            # Check if it matches the default .bit
            if qname.endswith('.bit'):
                qname = qname[:-4]
            else:
                raise RuntimeError('Domain is "%s", unknown TLD!' % (qname,))

        # Split into top-level and sub-domains
        split_domain = qname.split('.')
        domain_name = split_domain[-1]
        subdomains = split_domain[:-1][::-1]  # Reversed, eu.www = [www, eu]

        return domain_name, subdomains

    def resolve(self, context, question, reply):
        domain_name, subdomains = self._extract_name(context, question.qname)
        # TODO: validate domain name
        max_ttl, data = self._namespace.lookup('d/' + domain_name)
        namecoin_dict = namecoin_walk(self._namespace, data, subdomains)
        if namecoin_dict is None:
            return None  # Effectively NXDOMAIN

        resolver = ZoneResolver(
            zone=namecoin_dict_to_zone(domain_name, name, namecoin_dict)
        )
        return resolver.resolve(context, question, reply)
