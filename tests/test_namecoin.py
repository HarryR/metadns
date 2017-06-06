# -*- coding: UTF-8 -*-

from __future__ import print_function

from metadns.action.namecoin import (INamecoinNamespace, namecoin_dict_to_zone,
									 namecoin_walk)
from dnslib import RR, QTYPE


class DictNamecoinNamespace(INamecoinNamespace):
	def __init__(self, data):
		self._data = data

	def lookup(self, namespaced_name):
		return self._data.get(namespaced_name)


def test_basic():
	"""
	Ensure that Namecoin to Zone translator can be parsed and meets some 
	fairly basic validity checks. This also ensures that any fundamental 
	changes to how 
	"""
	data = DictNamecoinNamespace({
		'd/test': {
			 "ip": "192.168.1.1",
			 "ip6": "2001:4860:0:1001::68"
		}
	})
	result = namecoin_dict_to_zone("test", "", data.lookup("d/test"))
	expected = """$ORIGIN test.
$TTL 3600
@ IN A 192.168.1.1
@ IN AAAA 2001:4860:0:1001::68"""
	assert result == expected

	parsed = RR.fromZone(result)
	record_A = parsed[0]
	record_AAAA = parsed[1]
	assert record_A.rname == 'test.'
	assert record_A.rtype == QTYPE.A
	assert str(record_A.rdata) == '192.168.1.1'
	assert record_AAAA.rtype == QTYPE.AAAA
	assert str(record_AAAA.rdata) == '2001:4860:0:1001::68'


def test_walk_delegate():
	"""Verify delegation works"""
	namespace = DictNamecoinNamespace({
		'd/toplevel': {
			'delegate': ["s/sublevel"]
		},
		's/sublevel': {
			'ip': "192.168.1.1",
		}
	})
	result = namecoin_walk(namespace, namespace.lookup('d/toplevel'))
	assert result['ip'] == '192.168.1.1'


def test_walk_delegate_sub():
	"""Verify delegation to a sub-name works"""
	namespace = DictNamecoinNamespace({
		'd/toplevel': {
			'delegate': ["s/sublevel", 'www']
		},
		's/sublevel': {
			'map': {
				'www': {
					'ip': "192.168.1.1",				
				}
			}
		}
	})
	result = namecoin_walk(namespace, namespace.lookup('d/toplevel'))
	assert result['ip'] == '192.168.1.1'

def test_walk_delegate_loop():
	namespace = DictNamecoinNamespace({
		'd/toplevel': {
			'delegate': ["d/toplevel"]
		}
	})
	try:
		namecoin_walk(namespace, namespace.lookup('d/toplevel'))
	except Exception as ex:
		assert isinstance(ex, RuntimeError)
