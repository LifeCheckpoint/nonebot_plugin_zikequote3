from dataclasses import dataclass
from typing import Any
import click
import shlex
import typer

def parse_command(parser: typer.Typer, line: str) -> Any:
    tokens = shlex.split(line)
    try:
        result = parser(
            args=tokens,
            prog_name="",
            standalone_mode=False
        )
        return result
    except typer.Exit as exc:
        raise ValueError("命令请求退出: help / exit") from exc
    except click.ClickException as exc:
        raise ValueError(exc.format_message()) from exc
