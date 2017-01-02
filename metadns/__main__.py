# -*- coding: UTF-8 -*-
from __future__ import print_function
import sys
import argparse
import logging
import yaml


def _args_to_config(args, config):
    if 'options' not in config:
        config['options'] = dict()
    config['options']['port'] = args.port
    config['options']['address'] = args.address
    config['options']['loglevel'] = args.loglevel
    config['options']['logconfig'] = args.logconfig
    return config


def _parse_args():
    """
    :returns: args, config - Arguments and config dictionary
    """
    #
    # First parse config file argument so we can extract the defaults
    conf_parser = argparse.ArgumentParser(description="Meta DNS Server",
                                          add_help=False)
    conf_parser.add_argument("-c", "--config", metavar="FILE", nargs='?',
                             type=argparse.FileType('r'),
                             help="Configuration file")
    initial_args, remaining_argv = conf_parser.parse_known_args()
    #
    # Default defaults are provided, in case they aren't in the config
    defaults = dict(
        port=53,
        address="0.0.0.0",
        timeout=5
    )
    if initial_args.config:
        # Accept default options from config file
        config = yaml.load(initial_args.config.read())
        if 'options' in config:
            defaults.update(config["options"])
            del config['options']
    else:
        config = dict()
    #
    # Then setup & parse the rest of the arguments
    psr = argparse.ArgumentParser(parents=[conf_parser])
    psr.set_defaults(**defaults)
    psr.add_argument("--port", "-p", type=int, metavar="<port>",
                     help="DNS server listen port (default:%r)" % (
                         defaults['port'],))
    psr.add_argument("--address", "-a", metavar="<address>",
                     help="DNS server listen address (default:%r)" % (
                         defaults['address'],))
    psr.add_argument("--timeout", "-t", type=float,
                     metavar="<timeout>",
                     help="Upstream timeout (default: 5s)")
    psr.add_argument("--logconfig", '-L', type=argparse.FileType('r'),
                     nargs='?', metavar='FILE',
                     help="Python logging config INI file")
    psr.add_argument('-q', '--quiet', action='store_true',
                     help="Don't print results to console")
    psr.add_argument('-v', '--verbose', action='store_const',
                     dest="loglevel", const=logging.INFO,
                     help="Log informational messages")
    psr.add_argument('--debug', action='store_const', dest="loglevel",
                     const=logging.DEBUG, default=logging.WARNING,
                     help="Log debugging messages")
    args = psr.parse_args(remaining_argv)
    return _args_to_config(args, config)


def main():
    config = _parse_args()
    options = config['options']
    log_config = options.get('log_config')
    if log_config:
        if isinstance(log_config, str):
            log_config = open(log_config, 'r')
        logging.config.fileConfig(log_config.name)
    else:
        logging.basicConfig(level=options['loglevel'])

    # Import *after* configuring logging so that per-module getLogger
    # inherits the settings we've configured above
    from . import MetaDNS
    return MetaDNS(config).run()


if __name__ == "__main__":
    sys.exit(main())
