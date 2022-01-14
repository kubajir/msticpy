# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
"""Requirements file writer from setup.py extras."""
import argparse
import difflib
import sys
from importlib import import_module
from pathlib import Path
from typing import List

VERSION = "1.0.0"

__version__ = VERSION
__author__ = "Ian Hellen"


def _add_script_args():
    parser = argparse.ArgumentParser(
        description=f"Package imports analyer. v.{VERSION}"
    )
    parser.add_argument(
        "--out",
        "-o",
        default="./requirements-all.txt",
        required=False,
        help="Path of output file",
    )
    parser.add_argument(
        "--setup",
        "-s",
        default="./setup.py",
        required=False,
        help="Path of setup.py to process.",
    )
    parser.add_argument(
        "--extra",
        "-e",
        default="all",
        required=False,
        help="Name of extra to use.",
    )
    parser.add_argument(
        "--diff",
        "-d",
        required=False,
        action="store_true",
        help="Print diffs, don't write file.",
    )
    parser.add_argument(
        "--print",
        "-p",
        required=False,
        action="store_true",
        help="Print new requirements, don't write file.",
    )
    return parser


def _get_current_reqs_all(app_args):
    current_reqs = Path(app_args.out)
    if current_reqs.is_file():
        curr_text = current_reqs.read_text(encoding="utf-8")
        return sorted(
            req
            for req in curr_text.split("\n")
            if req.strip() and not req.strip().startswith("#")
        )
    return []


def _compare_reqs(new, current):
    return list(
        difflib.context_diff(
            sorted(new, key=str.casefold),
            sorted(current, key=str.casefold),
            fromfile="Corrected",
            tofile="Current",
        )
    )


def _write_requirements(app_args, extras: List[str]):
    Path(app_args.out).write_text("\n".join(extras), encoding="utf-8")


def _get_extras_from_setup(
    extra: str = "all",
    include_base: bool = False,
) -> List[str]:
    """
    Return list of extras from setup.py.

    Parameters
    ----------
    extra : str, optiona
        The name of the extra to return, by default "all"
    include_base : bool, optional
        If True include install_requires, by default False

    Returns
    -------
    List[str]
        List of package requirements.

    Notes
    -----
    Duplicated from tools/toollib/import_analyzer.py

    """
    setup_mod = import_module("setup")
    extras = getattr(setup_mod, "EXTRAS").get(extra)
    if include_base:
        base_install = getattr(setup_mod, "INSTALL_REQUIRES")
        extras.extend(
            [req.strip() for req in base_install if not req.strip().startswith("#")]
        )
    return sorted(list(set(extras)), key=str.casefold)


# pylint: disable=invalid-name
if __name__ == "__main__":
    arg_parser = _add_script_args()
    args = arg_parser.parse_args()

    extra_reqs = _get_extras_from_setup(
        extra="all",
        include_base=True,
    )

    if args.print:
        print("\n".join(extra_reqs))
        sys.exit(0)

    existing_reqs = _get_current_reqs_all(args)
    diff_reqs = _compare_reqs(new=extra_reqs, current=existing_reqs)
    if diff_reqs:
        if args.diff:
            print("\n".join(diff.strip() for diff in diff_reqs))
        else:
            _write_requirements(app_args=args, extras=extra_reqs)
        sys.exit(1)
