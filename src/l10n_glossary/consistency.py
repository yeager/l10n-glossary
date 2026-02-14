#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Daniel Nylander <daniel@danielnylander.se>

"""Consistency checker — scan PO/TS files against a glossary."""

import os
import re
import gettext
from lxml import etree

_ = gettext.gettext


def check_consistency(glossary, path):
    """Check a PO or TS file against the glossary.

    Returns a list of dicts: {source, expected, found, line}
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".po":
        return _check_po(glossary, path)
    elif ext == ".ts":
        return _check_ts(glossary, path)
    else:
        raise ValueError(_("Unsupported file format: {}").format(ext))


def _check_po(glossary, path):
    """Check a PO file against glossary."""
    issues = []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Detect language
    lang_match = re.search(r'Language:\s*(\S+)', content)
    lang = lang_match.group(1) if lang_match else ""

    # Build lookup: source -> expected target(s) for this language
    expected = {}
    for term in glossary.terms:
        if not lang or term.language == lang or not term.language:
            expected.setdefault(term.source.lower(), []).append(term)

    # Parse entries
    entries = re.findall(
        r'msgid\s+"((?:[^"\\]|\\.)*)"\s*\n(?:.*?\n)*?msgstr\s+"((?:[^"\\]|\\.)*)"',
        content)

    for msgid, msgstr in entries:
        if not msgid or not msgstr:
            continue
        msgid_clean = msgid.replace('\\n', '\n').replace('\\"', '"')
        msgstr_clean = msgstr.replace('\\n', '\n').replace('\\"', '"')

        # Check if any glossary source term appears in this msgid
        for term_key, term_list in expected.items():
            if term_key in msgid_clean.lower():
                for term in term_list:
                    if (term.target.lower() not in msgstr_clean.lower()
                            and term.target):
                        issues.append({
                            "source": term.source,
                            "expected": term.target,
                            "found": msgstr_clean[:80],
                        })

    return issues


def _check_ts(glossary, path):
    """Check a TS file against glossary."""
    issues = []
    tree = etree.parse(path)
    root = tree.getroot()
    lang = root.get("language", "")

    expected = {}
    for term in glossary.terms:
        if not lang or term.language == lang or not term.language:
            expected.setdefault(term.source.lower(), []).append(term)

    for message in root.findall(".//message"):
        source_el = message.find("source")
        trans_el = message.find("translation")
        if source_el is None or trans_el is None:
            continue
        source = (source_el.text or "").strip()
        translation = (trans_el.text or "").strip()
        if not source or not translation:
            continue

        for term_key, term_list in expected.items():
            if term_key in source.lower():
                for term in term_list:
                    if (term.target.lower() not in translation.lower()
                            and term.target):
                        issues.append({
                            "source": term.source,
                            "expected": term.target,
                            "found": translation[:80],
                        })

    return issues
