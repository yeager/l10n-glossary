# Glossary Editor

A GTK4/Adwaita application for creating and managing translation glossaries (TBX/CSV/TSV).

## Features

- Create/open glossary files (TBX, CSV, TSV)
- Add/edit/delete terms (source, target, context, comment)
- Search and filter terms
- Import terms from .po/.ts files (extract frequent terms)
- Export to TBX, CSV, TSV
- Consistency check: scan .po/.ts files against glossary
- Support for multiple languages in the same glossary
- Merge glossaries

## Installation

### Debian/Ubuntu

```bash
# Add repository
curl -fsSL https://yeager.github.io/debian-repo/KEY.gpg | sudo gpg --dearmor -o /usr/share/keyrings/yeager-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/yeager-archive-keyring.gpg] https://yeager.github.io/debian-repo stable main" | sudo tee /etc/apt/sources.list.d/yeager.list
sudo apt update
sudo apt install l10n-glossary
```

### Fedora/RHEL

```bash
sudo dnf config-manager --add-repo https://yeager.github.io/rpm-repo/yeager.repo
sudo dnf install l10n-glossary
```

### From source

```bash
pip install .
l10n-glossary
```

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

## License

GPL-3.0-or-later — Daniel Nylander <daniel@danielnylander.se>
