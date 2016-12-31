from __future__ import print_function
from .upstream import GoogleDnsHttpUpstream


def googlehttps(**options):
    return GoogleDnsHttpUpstream(**options)
