#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2026 Daniel Nylander <daniel@danielnylander.se>

"""Glossary data model."""

from dataclasses import dataclass, field


@dataclass
class Term:
    """A single glossary term."""
    source: str = ""
    target: str = ""
    language: str = ""
    context: str = ""
    comment: str = ""


@dataclass
class Glossary:
    """A collection of terms."""
    terms: list = field(default_factory=list)

    def merge(self, other):
        """Merge another glossary into this one. Returns count of new terms added."""
        existing = {(t.source, t.target, t.language) for t in self.terms}
        added = 0
        for t in other.terms:
            key = (t.source, t.target, t.language)
            if key not in existing:
                self.terms.append(t)
                existing.add(key)
                added += 1
        return added
