#!/usr/bin/env python3
"""Atomic, exclusive persistence adapter for HELIX transactions."""

import json
import os
import tempfile


def load_transaction(path: str) -> dict | None:
    path = os.path.abspath(path)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_transaction(path: str, transaction: dict) -> None:
    path = os.path.abspath(path)
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    lock = path + ".lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as e:
        raise RuntimeError(f"transaction is locked: {path}") from e
    temp = None
    try:
        os.close(fd)
        handle, temp = tempfile.mkstemp(prefix=".helix-tx-", suffix=".json",
                                        dir=directory)
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as f:
            json.dump(transaction, f, ensure_ascii=False, sort_keys=True,
                      indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
        temp = None
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)
        try:
            os.unlink(lock)
        except FileNotFoundError:
            pass
