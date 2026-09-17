"""Parse .claude/shared/project-config.md GitHub-flavoured markdown tables.

Row-lookup logic: split each table row on '|', trim whitespace and backticks,
match column 2, return column 3.

Exports:
  read_config_value(label)        -> str | None    first value where column-2 == label
  list_config_keys(section="")    -> list[str]      all column-2 labels (optionally one section)
  read_config_section(section)    -> str | None     raw markdown of one ## section

@author Samson Paul, samson.paul@experionglobal.com
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import project_config_path  # noqa: E402

# Markdown table separator row: optional space, '|', optional space, then dashes.
_SEPARATOR_ROW = re.compile(r"^\s*\|\s*-+")


def _clean(cell):
    """Trim surrounding whitespace and backticks from a table cell."""
    return cell.strip().strip("`").strip()


def _config_lines():
    """Yield the lines of project-config.md, or nothing if it is unavailable."""
    path = project_config_path()
    if not path or not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as handle:
        return handle.read().splitlines()


def read_config_value(label):
    """Return the column-3 value of the first `| label | value |` row, or None."""
    for line in _config_lines():
        if "|" not in line:
            continue
        parts = line.split("|")
        if len(parts) < 4:
            continue
        key = _clean(parts[1])
        if not key or set(key) == {"-"}:
            continue
        if key == label:
            return _clean(parts[2])
    return None


def list_config_keys(section=""):
    """Return all column-2 labels, optionally scoped to one ## section."""
    keys = []
    in_target = section == ""
    in_table_body = False
    for line in _config_lines():
        if line.startswith("## "):
            current_section = line[3:]
            in_target = (section == "" or current_section == section)
            in_table_body = False
            continue
        if line.strip() == "":
            in_table_body = False
            continue
        if _SEPARATOR_ROW.match(line):
            in_table_body = True
            continue
        if "|" in line:
            if not in_target or not in_table_body:
                continue
            parts = line.split("|")
            if len(parts) < 4:
                continue
            key = _clean(parts[1])
            if not key or set(key) == {"-"}:
                continue
            keys.append(key)
    return keys


def read_config_section(section):
    """Return the raw markdown of one ## section (heading included), or None."""
    collected = []
    in_section = False
    for line in _config_lines():
        if line.startswith("## "):
            if in_section:
                break
            in_section = (line[3:] == section)
        if in_section:
            collected.append(line)
    return "\n".join(collected) if collected else None
