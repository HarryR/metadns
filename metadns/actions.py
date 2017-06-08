# -*- coding: UTF-8 -*-

def googlehttps(**options):
    from .action.http import GoogleDnsHttpResolver
    return GoogleDnsHttpResolver(**options)

def zone(**options):
    from .action.zone import ZoneResolver
    return ZoneResolver(**options)

def namecoin(**options):
	from .action.namecoin import NamecoinResolver
	return NamecoinResolver(**options)
