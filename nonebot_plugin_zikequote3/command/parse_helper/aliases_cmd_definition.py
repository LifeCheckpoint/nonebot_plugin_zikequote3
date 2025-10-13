from ...imports import *
from typer.models import CommandFunctionType


def cmd_name_alias(parser: typer.Typer, names: Sequence[str]):
    def decorator(func: CommandFunctionType) -> CommandFunctionType:
        for name in names:
            parser.command(name)(func)
        return func
    return decorator