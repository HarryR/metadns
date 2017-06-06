# -*- coding: UTF-8 -*-
import requests
import json
import decimal

class HttpUpstream(object):
    """
    Delivers the request object to an upstream HTTP service and
    decodes the response object.
    """
    def __init__(self, **kwa):
        self.url = kwa.get('url')
        self.timeout = float(kwa.get('timeout', 0.5))
        assert self.timeout > 0.0
        self._method = str(kwa.get('method', 'GET'))
        if self._method not in ['GET', 'POST']:
            raise ValueError('"method" must be one of: GET, POST')
        self._session = requests.Session()

    def request(self, data, url_suffix='', **extra):
        # XXX: timeout given to Requests may not be the absolute timeout
        #      so it could delay longer than the timeout..
        # TODO: multiple endpoints, fail-over?
        if self._method == 'GET':
            http_resp = self._session.get(
                self.url + url_suffix,
                params=data,
                timeout=self.timeout,
                **extra)
        elif self._method == 'POST':
            http_resp = self._session.post(
                self.url + url_suffix,
                data=data,
                timeout=self.timeout,
                **extra)
        else:
            raise RuntimeError('Invalid HTTP method "%s"' % (self._method,))

        http_resp.raise_for_status()
        return http_resp


class JSONRPCError(Exception):
    def __init__(self, rpc_error):
        Exception.__init__(self)
        self.error = rpc_error


class JSONRPCMethod(object):
    """
    Translates Python calls into JSON-RPC calls via upstream HTTP transport
    """
    def __init__(self, upstream, name):
        self._upstream = upstream
        self._name = name

    def __getattr__(self, name):
        sub_name = '.'.join([self._name, name])
        return JSONRPCMethod(self._upstream, sub_name)

    def __call__(self, *args):
        data = dict(
            version='1.1',
            method=self._name,
            params=args,
            id=self._upstream.jsonrpc_inc_id()
        )
        http_resp = self._upstream.request(data)
        resp = json.loads(http_resp.text, parse_float=decimal.Decimal)
        if resp['error']:
            JSONRPCError(resp['error'])
        elif 'result' not in resp:
            JSONRPCError(dict(
                code=-343,
                message='missing JSON-RPC result',
            ))
        else:
            return resp['result']


class JSONRPCProxy(HttpUpstream):
    def __init__(self, **kwa):
        super(JSONRPCProxy, self).__init__(**kwa)
        self._id_ctr = 0

    def jsonrpc_inc_id(self):
        self._id_ctr = self._id_ctr + 1
        return self._id_ctr

    def jsonrpc(self, name):
        return JSONRPCMethod(self, name)

    def __getattr__(self, name):
        return JSONRPCMethod(self, name)
