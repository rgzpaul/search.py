# Python Search Tool

Recursive text search tool with GUI. Select a folder, enter search text, optionally filter by file extensions. Finds all occurrences across files displaying filename, line number, and matched content.

## Requirements

- Python 3.x
- Tkinter (included with Python)

## Usage

```bash
python search.py
```

1. Click **Browse** to select a folder
2. Enter search text
3. (Optional) Enter file extensions to filter: `php,js,html`
4. Check **Case sensitive** if needed
5. Click **Search**

## Features

- Recursive folder scanning
- Extension filtering for faster searches
- Case sensitive option
- Threaded search (UI stays responsive)
- Displays file path, line number, and content
