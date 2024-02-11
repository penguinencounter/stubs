import logging
import pathlib

import rich_click as click

# import click
from rich import print as rp
from rich.logging import RichHandler

from interpret import scan, ExpectationFailed

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="%H:%M:%S",
    handlers=[RichHandler()],
)
logger = logging.getLogger("stub CLI")


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=True, file_okay=True, dir_okay=False, resolve_path=True),
    shell_complete=True,
    default=".stubs",
)
@click.option(
    "--dry-run",
    "-d",
    help="Parse and log control flow, don't make any changes to the system",
    is_flag=True,
)
@click.option(
    "--no-backup",
    "-B",
    help="Don't make a backup of the current directory",
    is_flag=True,
)
def main(path, dry_run, no_backup):
    path_obj = pathlib.Path(path)
    logger.info(f"Loading file: {path_obj}")
    with open(path_obj, "r") as f:
        content = f.read()
    try:
        tokens = scan(content)
    except ExpectationFailed as e:
        logger.error(
            f"[bold red]{type(e).__name__}[/]: {e.rich_reason()}",
            extra={"markup": True, "highlighter": None},
        )
        exit(1)
    logger.info(tokens)


if __name__ == "__main__":
    main()
