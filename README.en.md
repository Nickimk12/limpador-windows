🇧🇷 [Português](README.md) | 🇺🇸 English

# Temporary Files Cleaner for Windows

A graphical program that cleans temporary files and caches on **Windows 10 and 11**, built with Python (tkinter). It shows how much space will be freed **before** anything is deleted.

> ℹ️ The program's interface is in **Portuguese**. Button names are shown below with their English meaning.

## What does it clean?

| Category | Checked by default |
|---|---|
| User temporary files | Yes |
| Windows temporary files | Yes |
| Windows Update cache | Yes |
| Error reports (CrashDumps) | Yes |
| Edge, Chrome and Brave cache (all profiles) | Yes |
| Prefetch | No |
| Windows logs | No |
| Recycle Bin | No |

## Features

- Dry run: shows the size of each category before deleting
- Confirmation before cleaning
- Age filter: deletes only files older than X days (default: 1 day)
- Warning when a browser is open
- Progress bar and log area
- Log saved to `limpador_log.txt`, next to the program

## How to install and use

### Option 1: download the program (recommended)

1. Go to the [**Releases**](../../releases) tab of this repository.
2. Download the file `arquivos_temporarios_windows.exe`
3. Double-click it and allow it to run as Administrator.
4. Click **Analisar de novo** ("Analyze again"), check what you want to clean and click **Limpar selecionados** ("Clean selected").

> Windows SmartScreen or your antivirus may show a warning, because the program is **not digitally signed**. The full source code is in this repository and can be reviewed. If you prefer, run it from the source code (option 2).

### Option 2: run from the source code

Requirements: Windows 10/11 and [Python 3.8+](https://www.python.org/downloads/) (tkinter is included in the official installer).

```
python arquivos_temporarios_windows.py
```

To open it without the terminal window, rename the file to `arquivos_temporarios_windows.pyw` and double-click it.

### Build your own .exe

```
pip install pyinstaller
pyinstaller --onefile --noconsole --uac-admin arquivos_temporarios_windows.py
```

The file will be created in the `dist` folder.

## Important warnings

- **Deletion is permanent.** Review the list before confirming.
- Close your browsers before cleaning their cache, otherwise part of it will not be deleted.
- Avoid cleaning while Windows installations or updates are in progress.
- **Prefetch** and **Windows logs** are unchecked by default: they free little space and have side effects (programs open slower for a while, and there are fewer records for diagnostics).
- If you want, create a Windows restore point before using it.
- This software is provided **without warranty**, under the MIT license. Use it at your own risk.

## Found a problem?

Open an [Issue](../../issues) with your Windows version, what happened and, if available, the error message or the contents of `limpador_log.txt`

## License

Distributed under the MIT license. See the [LICENSE](LICENSE) file.
