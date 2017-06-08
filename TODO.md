Config class
 - Multiple listeners
 - Other named objects (e.g. databases, data sources)
 - Routes


Listeners:
 - type (dns, http)
 - protocol (tcp, udp)
 - listen (ip, port)


Testing:
 - unit tests
 - test DNS query with dig, of various types
 - ensure functionality of each action works
 - Python 2.7/2.6 and 3.5/3.6


Error handling:
 - Define classes in metadns namespace for all DNS errors
 - e.g. NXDOMAIN, SERVFAIL
 - Throw these errors consistently, rather than returning None


WSGI compatibility, for providing Google DNS over HTTPS style interface


IETF DNS Queries over HTTPS support
 - https://tools.ietf.org/html/draft-hoffman-dns-over-http-01
 - https://tools.ietf.org/html/draft-hoffman-dns-in-json-10


Don't enforce gevent everywhere (e.g. in wsgi handler), but use it by default


zone file, retrieved from URL, reuse `HttpUpstream`


easier Bottle.py or Flask style route names with capture, e.g. "*.<user>.example.com"
 - gives you 'user' in context


use parameters captured from route in URLs and other options.


Python web-framework style applications, e.g.

	@metadns.route(glob="*.example.com", qtype='A')
	def example_A(ctx, query, reply):
	    pass


License:
 - compatible with dnslib BSD license
 - AGPLv3?
