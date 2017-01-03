# -*- coding: UTF-8 -*-
from __future__ import print_function


def googlehttps(**options):
    from .act.http import GoogleDnsHttpResolver
    return GoogleDnsHttpResolver(**options)

def zone(**options):
    from .act.zone import ZoneResolver
    return ZoneResolver(**options)
