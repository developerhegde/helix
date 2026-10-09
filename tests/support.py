"""Shared test helpers: synthetic acme-* profiles and an in-process CLI runner."""

import contextlib
import io
import os
import shutil
from datetime import datetime, timezone

import yaml

from helix import product_identity as pid
from helix.cli.main import main

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "acme-a")
NOW = datetime(2026, 10, 9, tzinfo=timezone.utc)


def make_profile(tmp, mutate=None, env_extra=""):
    """Copy the healthy fixture into tmp; mutate(doc) edits the profile mapping in place."""
    root = os.path.join(tmp, "acme-a")
    shutil.copytree(FIXTURE, root)
    path = os.path.join(root, pid.PROFILE_FILENAME)
    if mutate is not None:
        with open(path) as handle:
            doc = yaml.safe_load(handle)
        mutate(doc)
        with open(path, "w") as handle:
            yaml.safe_dump(doc, handle, sort_keys=False)
    if env_extra:
        with open(os.path.join(root, ".env"), "a") as handle:
            handle.write(env_extra)
    return root


def run_cli(*argv, now=NOW):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(list(argv), now=now)
    return code, out.getvalue(), err.getvalue()
