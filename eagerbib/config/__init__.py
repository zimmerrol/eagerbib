import argparse
import dataclasses
import os
from typing import Type, TypeVar, Optional

from . import utils as ut
from .config import MainConfig, OutputProcessorConfig, NameNormalizationConfig, OnlineUpdaterConfig, DBLPCrawlerConfig, BaseConfig  # noqa: F401


__basefolder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


C = TypeVar('C', bound=BaseConfig)
def __get_arg_parser(cfg_cls: Type[C]) -> argparse.ArgumentParser:
    """Create a parser for the command line arguments.

    Args:
        cfg_cls: The config class to use.

    Returns:
        argparse.ArgumentParser: The parser.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", "-c", type=str, default=None, help="The config yaml file to use."
    )

    # Add all the parameters to the parser.
    cli_parameters = ut.get_all_cli_parameters(cfg_cls)
    for clip in cli_parameters:
        args = ["--" + clip["name"].replace("_", "-")]
        if clip["short_name"] is not None:
            # For now, argparse does not support multiple short names that start
            # identically. Therefore, we disable short names for now for nested
            # objects.
            # TODO: Revisit this.
            if "." not in clip["short_name"]:
                args.append("-" + clip["short_name"])
        if clip["default_factory"] is not dataclasses.MISSING:
            default = clip["default_factory"]()
        else:
            default = clip["default"]
        parser.add_argument(
            *args,
            type=clip["type"],
            default=default,
            help=clip["help"],
            required=clip["required"],
        )

    return parser


def get_config(cfg_cls: Type[C], default_config_fn: Optional[str] = None) -> C:
    """Get the config based on the indicated config file and other arguments.

    Args:
        cfg_cls: The config class to use.
        default_config_fn: The default config file to use if no config file is
            indicated. If None, no default config file is used.

    Returns:
        MainConfig: The config.
    """
    parser = __get_arg_parser(cfg_cls)
    args = parser.parse_args()
    if args.config is not None:
        config = cfg_cls.from_yaml_file(args.config)
    else:
        if default_config_fn is not None and os.path.exists(default_config_fn):
            config = cfg_cls.from_yaml_file(default_config_fn)
        else:
            config = cfg_cls()
    del args.config
    ut.update_object_with_dict(config, args.__dict__)

    return config
