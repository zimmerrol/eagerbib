import argparse
import dataclasses
import os
import typing
from typing import Optional, Type, TypeVar

from . import utils as ut
from .config import (BaseConfig, DBLPCrawlerConfig, MainConfig,  # noqa: F401
                     NameNormalizationConfig, OnlineUpdaterConfig,
                     OutputProcessorConfig)

__basefolder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


C = TypeVar("C", bound=BaseConfig)


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
        conditional_kwargs = {"type": clip["type"]}
        if clip["default_factory"] is not dataclasses.MISSING:
            default = clip["default_factory"]()
            if isinstance(default, (list, tuple)):
                conditional_kwargs["nargs"] = "+"
                inner_types = typing.get_args(clip["type"])
                if inner_types is not None:
                    if len(inner_types) == 1:
                        conditional_kwargs["type"] = inner_types[0]
                    else:
                        raise ValueError(
                            "Only one inner type is supported for lists/tuples."
                        )
        else:
            default = clip["default"]

        if clip["type"] == bool:
            conditional_kwargs["action"] = __BooleanOptionalAction
        parser.add_argument(
            *args,
            default=default,
            help=clip["help"],
            required=clip["required"],
            **conditional_kwargs
        )

    return parser


class __BooleanOptionalAction(argparse.Action):
    """Extends argparse.BooleanOptionalAction to support nested configurations."""

    def __init__(
        self,
        option_strings,
        dest,
        default=None,
        type=None,
        choices=None,
        required=False,
        help=None,
        metavar=None,
    ):
        _option_strings = []
        for option_string in option_strings:
            _option_strings.append(option_string)

            option_string_parts = option_string.split(".")

            if option_string_parts[0].startswith("--"):
                option_string_parts[-1] = "no-" + option_string_parts[-1]
                option_string = ".".join(option_string_parts)
                _option_strings.append(option_string)

        if (
            help is not None
            and default is not None
            and default is not argparse.SUPPRESS
        ):
            help += " (default: %(default)s)"

        super().__init__(
            option_strings=_option_strings,
            dest=dest,
            nargs=0,
            default=default,
            type=type,
            choices=choices,
            required=required,
            help=help,
            metavar=metavar,
        )

    def __call__(self, parser, namespace, values, option_string=None):
        if option_string in self.option_strings:
            setattr(
                namespace,
                self.dest,
                not (
                    option_string.split(".")[-1].startswith("--no-")
                    or option_string.split(".")[-1].startswith("no-")
                ),
            )

    def format_usage(self):
        return " | ".join(self.option_strings)


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
