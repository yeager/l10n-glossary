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

## 🌍 Contributing Translations

Help translate this app into your language! All translations are managed via Transifex.

**→ [Translate on Transifex](https://app.transifex.com/danielnylander/l10n-glossary/)**

### How to contribute:
1. Visit the [Transifex project page](https://app.transifex.com/danielnylander/l10n-glossary/)
2. Create a free account (or log in)
3. Select your language and start translating

### Currently supported languages:
Arabic, Czech, Danish, German, Spanish, Finnish, French, Italian, Japanese, Korean, Norwegian Bokmål, Dutch, Polish, Brazilian Portuguese, Russian, Swedish, Ukrainian, Chinese (Simplified)

### Notes:
- Please do **not** submit pull requests with .po file changes — they are synced automatically from Transifex
- Source strings are pushed to Transifex daily via GitHub Actions
- Translations are pulled back and included in releases

New language? Open an [issue](https://github.com/yeager/l10n-glossary/issues) and we'll add it!