import dataclasses
from typing import Any, Callable, Optional


def cli_parameter(
    short_name: Optional[str] = None,
    default: Any = dataclasses.MISSING,
    default_factory: Optional[Callable[[], Any]] = dataclasses.MISSING,
    required: bool = False,
    help: Optional[str] = None,
):
    """A decorator to mark a field as configurable through a CLI parameter."""

    # If this is a required argument, we need to set a default value to anything,
    # otherwise, the class cannot be constructed by the YAML parser.
    return dataclasses.field(
        default=default if not required else None,
        default_factory=default_factory,
        repr=True,
        metadata=dict(
            is_cli_parameter=True,
            short_name=short_name,
            help=help,
            required=required,
            default=default,
            default_factory=default_factory,
        ),
    )


def get_all_cli_parameters(cls, name_prefix="", short_prefix=""):
    """Get all the CLI parameters of a class."""
    cli_parameters = []
    fields = dataclasses.fields(cls)
    for field in fields:
        if field.metadata.get("is_cli_parameter", False):
            field_type = cls.__annotations__[field.name]
            if dataclasses.is_dataclass(field_type):
                cli_parameters += get_all_cli_parameters(
                    field_type,
                    f"{name_prefix}{field.name}." if name_prefix else f"{field.name}.",
                    f"{short_prefix}{field.metadata['short_name']}."
                    if short_prefix
                    else f"{field.metadata['short_name']}.",
                )
            else:
                cli_parameters.append(
                    dict(
                        type=field_type,
                        name=name_prefix + field.name,
                        short_name=short_prefix + field.metadata["short_name"],
                        default=field.metadata["default"],
                        default_factory=field.metadata["default_factory"],
                        required=field.metadata["required"],
                        help=field.metadata["help"],
                    )
                )
    return cli_parameters


def update_object_with_dict(obj, d):
    """Update an object with a dictionary considering nested values.

    Args:
        obj: The object to update.
        d: The dictionary to use to update the object.
    """
    if not dataclasses.is_dataclass(type(obj)):
        return

    # Update the top-level fields.
    keys = [k for k in d.keys() if "." not in k]
    for k in keys:
        potential_fields = [f for f in dataclasses.fields(type(obj)) if f.name == k]
        if len(potential_fields) == 0:
            raise ValueError(f"Unknown argument {k} for {type(obj).__name__}")
        field = potential_fields[0]
        # Only update the field if it is a CLI parameter and the value is not
        # the default one.
        if field.metadata.get("is_cli_parameter", False):
            if field.metadata["default_factory"] is not dataclasses.MISSING:
                default = field.metadata["default_factory"]()
            else:
                default = field.metadata["default"]

            if d[k] != default:
                setattr(obj, k, d[k])

    # Update the nested fields.
    inner_keys = sorted([k for k in d.keys() if "." in k])
    previous_inner_key = None
    previous_inner_index = 0
    for i, k in enumerate(inner_keys):
        inner_key = k.split(".")[0]
        if previous_inner_key is None:
            previous_inner_key = inner_key
        if inner_key != previous_inner_key or i == len(inner_keys) - 1:
            inner_dict = {
                ".".join(ki.split(".")[1:]): d[ki]
                for ki in inner_keys[previous_inner_index:i]
            }
            update_object_with_dict(getattr(obj, previous_inner_key), inner_dict)
            previous_inner_key = inner_key
            previous_inner_index = i