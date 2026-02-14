# Glossary Editor (l10n-glossary)

A GTK4/Adwaita application for managing localization glossaries — term lists per language/project with inconsistency detection.

## Features

- Create/open glossary files (TBX, CSV, TSV)
- Add/edit/delete terms (source, target, context, comment)
- Search and filter terms
- Import terms from .po/.ts files (extract frequent terms)
- Export to TBX, CSV, TSV
- Consistency check: scan .po/.ts files against glossary, flag inconsistent translations
- Support for multiple languages in the same glossary
- Merge glossaries

## Installation

### From .deb package

```bash
sudo apt install ./l10n-glossary_0.1.0_all.deb
```

### From source

```bash
pip install .
l10n-glossary
```

## Dependencies

- Python 3.10+
- GTK 4
- libadwaita 1.x
- PyGObject
- lxml

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).

## Author

Daniel Nylander <daniel@danielnylander.se>

## Translation

Translations are managed via [Transifex](https://app.transifex.com/danielnylander/l10n-glossary/). See [po/README.md](po/README.md) for details.
