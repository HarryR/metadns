# -*- coding: UTF-8 -*-
import sys
import os
import argparse
import logging
from .router import DNSRouter


class Options(argparse.Namespace):
    @property
    def address(self):
        return self._address

    @address.setter
    def address(self, value):
        self._address = value

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        assert isinstance(value, int)
        assert value > 0
        assert value < 0xFFFF
        self._port = value

    @classmethod
    def defaults(cls):
        return dict(
            port=53,
            address="0.0.0.0",
            timeout=5,
            log_level=logging.WARNING
        )


def _load_config_dict(config_file):
    """
    Load a config file dictionary from a file, while optionally providing
    default options.
    """
    defaults = Options.defaults()
    config_data = dict()

    if isinstance(config_file, str):
        config_file = open(config_file, 'r')

    if config_file:
        _, extension = os.path.splitext(config_file.name)
        if extension in ['.yaml', '.yml']:
            import yaml
            config_data = yaml.load(config_file.read())
        elif extension == '.json':
            import json
            config_data = json.load(config_file.read())
        else:
            # TODO: support XML, INI etc.?
            raise RuntimeError("Unknown config file extension '%s'" % (extension,))
        config_data['options']['config'] = config_file

    if 'options' in config_data:
        config_data['options'].update(defaults)
    else:
        config_data['options'] = defaults

    return config_data


class Config(object):
    def __init__(self, options, router):
        self.options = options
        self.router = router

    @classmethod
    def from_dict(cls, data):
        options_data = data.get('options')
        if not options_data:
            raise ValueError('No "options" in config dictionary')
        options = Options(**options_data)
        router = DNSRouter.create_from_list(data.get('routes', []))
        return cls(options, router)

    @classmethod
    def from_args(cls, args=None, parents=None):
        """
        Load configuration file into a dictionary
        Parse command-line style arguments into the dictionary
        Then use `from_dict` to convert the combined dict into a Config object
        :returns Config:
        """

        # First parse config file argument so we can extract the defaults
        if parents is None:
            parents = []
        conf_parser = argparse.ArgumentParser(add_help=False, parents=parents)
        conf_parser.add_argument("-c", "--config", metavar="FILE", nargs='?',
                                 type=argparse.FileType('r'),
                                 help="Configuration file")
        initial_args, remaining_argv = conf_parser.parse_known_args()
        psr = argparse.ArgumentParser(parents=[conf_parser])

        # Load the intial config file, then options from the config are sent
        # back into the argument parser.
        config_data = _load_config_dict(initial_args.config)
        options = config_data.get('options', dict())
        psr.set_defaults(**options)

        # Setup command-line configurable arguments
        psr.add_argument('--debug-config', action='store_true',
                         help="Display parsed configuration options and exit")
        psr.add_argument("--port", "-p", type=int, metavar="<ip-port>",
                         help="DNS server listen port (default:%r)" % (
                            options['port'],))
        psr.add_argument("--address", "-a", metavar="<ip-address>",
                         help="DNS server listen address (default:%r)" % (
                            options['address'],))
        psr.add_argument("--timeout", "-t", type=float,
                         metavar="<timeout>",
                         help="Default upstream timeout (default: %r)" % (
                            options['timeout']))
        psr.add_argument("--log-config", '-L', type=argparse.FileType('r'),
                         nargs='?', metavar='FILE',
                         help="Python logging config INI file")
        psr.add_argument('-q', '--quiet', action='store_true',
                         help="Don't print results to console")
        psr.add_argument('-v', '--verbose', action='store_const',
                         dest="log_level", const=logging.INFO,
                         help="Log informational messages")
        psr.add_argument('--debug', action='store_const', dest="log_level",
                         const=logging.DEBUG, default=logging.WARNING,
                         help="Log debugging messages")

        # Parse arguments, then add the parsed arguments back into the config
        args = psr.parse_args(remaining_argv)
        if 'options' not in config_data:
            config_data['options'] = dict()
        config_data['options'].update(vars(args))

        if config_data['options'].get('debug_config'):
            # TODO: output in multiple formats, JSON, YAML etc.
            from pprint import PrettyPrinter
            PrettyPrinter().pprint(config_data)
            sys.exit(123)

        return cls.from_dict(config_data)
