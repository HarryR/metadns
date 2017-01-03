# -*- coding: UTF-8 -*-
from __future__ import print_function
import sys
import logging
from .config import Config


def main():
    config = Config.from_args()
    options = config.options
    if options.log_config:
        logging.config.fileConfig(options.log_config.name)
    else:
        logging.basicConfig(level=options.log_level)

    # Import *after* configuring logging so that per-module getLogger
    # inherits the settings we've configured above
    from . import MetaDNS
    return MetaDNS(config).run()


if __name__ == "__main__":
    sys.exit(main())
