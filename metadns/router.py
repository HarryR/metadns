# -*- coding: UTF-8 -*-
from __future__ import print_function
import re
from dnslib import RCODE, QTYPE, CLASS, DNSLabel, DNSQuestion, RR


REGEXP_TYPE = type(re.compile(''))


class BaseMatcher(object):
    def __init__(self, qclass, qtype):
        if isinstance(qtype, str):
            qtype = getattr(QTYPE, qtype)
        if isinstance(qclass, str):
            qclass = getattr(CLASS, qclass)
        self.qtype = qtype
        self.qclass = qclass

    def match_name(self, qname):
        assert isinstance(qname, DNSLabel)
        raise NotImplementedError()

    def __call__(self, question):
        assert isinstance(question, DNSQuestion)
        if question.qclass != 0xFF:  # *
            if question.qclass != self.qclass:
                return None
        if question.qclass != 0xFF:  # ANY
            if question.qclass != self.qclass:
                return None
        return self.match_name(question.qname)


class RegexMatcher(BaseMatcher):
    def __init__(self, qclass, qtype, regex):
        super(RegexMatcher, self).__init__(qclass, qtype)
        if not isinstance(regex, REGEXP_TYPE):
            regex = re.compile(regex)
        self._regex = regex

    def match_name(self, qname):
        match = self._regex.match(str(qname))
        if match:
            return match.groupdict()


class GlobMatcher(BaseMatcher):
    def __init__(self, qclass, qtype, glob_str):
        super(GlobMatcher, self).__init__(qclass, qtype)
        self._glob = glob_str

    def match_name(self, qname):
        if qname.matchGlob(self._glob):
            # XXX: glob returns nothing...
            return dict()


def create_matcher(options):
    qclass = options.get('qclass', 'IN')
    qtype = options.get('qtype', 'ANY')
    # TODO: support formats like '<name:int>.*.example.com'
    # A mix between glob and HTTP webapp style routes.
    # These should be translated to regular expressions
    if 'glob' in options:
        return GlobMatcher(qclass, qtype, options.pop('glob'))
    elif 'name' in options:
        return GlobMatcher(qclass, qtype, options.pop('name'))
    elif 'regex' in options:
        return RegexMatcher(qclass, qtype, options.pop('regex'))
    raise RuntimeError("Unknown match type")


def _create_action(options):
    """
    Create an action object from a dictionary of options
    Alternately just an action name can be provided.
    :returns: constructs object to resolve DNS query
    """
    # Load 'module' and action 'name' from options, handling both dict and str
    module = 'metadns.actions'
    if isinstance(options, str):
        action_name = options
        options = dict()
    else:
        assert isinstance(options, dict)
        if 'name' not in options:
            raise ValueError("No 'name' in action")
        action_name = options.pop('name')
        if 'module' in options:
            module = options.pop('module')

    # Construct instance of action, using remaining options
    mod = __import__(module, fromlist=[action_name])
    klass = getattr(mod, action_name)
    if klass is None:
        raise RuntimeError("Cannot find action '{}' in {}".format(
            action_name, module))
    obj = klass(**options)

    assert callable(obj)
    return obj


class Route(object):
    def __init__(self, matcher, handler, options):
        assert callable(matcher)
        self.match = matcher
        self._handler = handler
        self._final = bool(options.get('final', True))

    @classmethod
    def create_from_dict(cls, options):
        matcher = create_matcher(options)
        action = options.pop('action')
        handler = _create_action(action)
        return Route(matcher, handler, options)

    @property
    def final(self):
        """
        Once this route has been matched, no more routes will be processed
        """
        return self._final

    def dispatch(self, context, query, reply):
        response = self._handler(context, query, reply)
        if isinstance(reply, str):
            # Allow handler to respond with a string in BIND zone-format
            reply.add_answer(*RR.fromZone(response))
        else:
            reply = response
        return reply


class DNSRouter(object):
    __slots__ = ('_routes',)
    """
    A collection of Routes are used by the DNS Router to direct queries to
    the correct handlers for a DNS name and type.
    """
    @classmethod
    def create_from_list(cls, routes):
        assert isinstance(routes, (set, list))
        return DNSRouter([
            Route.create_from_dict(X)
            for X in routes
        ])

    def __init__(self, routes=None):
        if routes:
            assert isinstance(routes, list)
        else:
            routes = list()
        self._routes = routes

    def add(self, route):
        self._routes.append(route)

    def lookup(self, question):
        """
        :returns OrderedDict: Routes and their match data for the queried name
        """
        assert isinstance(question, DNSQuestion)
        results = list()
        for route in self._routes:
            match = route.match(question)
            if match is not None:
                assert isinstance(match, dict)
                results.append((route, match))
                if route.final:
                    break
        return results

    def dispatch(self, request, extra_context=None):
        response = None
        question = request.q
        for route, context in self.lookup(question):
            if extra_context:
                context.update(extra_context)
            tmp_response = response or request.reply()
            reply = route.dispatch(context, question, tmp_response)
            if reply:
                response = reply
                if route.final:
                    break
        if not response:
            response = request.reply()
            response.header.rcode = getattr(RCODE, 'NXDOMAIN')
        return response
