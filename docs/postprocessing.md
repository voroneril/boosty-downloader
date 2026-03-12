Two post-processing utilities (auto extension fixer + offline index generator)

Hello! 👋

Thank you for the excellent tool. I see active development (latest release v2.0.1 on 25 Sep 2025), a clean CLI and a “Contributing” section — so I’d like to propose two small but useful utilities to post-process downloaded content. I think they could be added as separate CLI subcommands or placed in a `utils/` folder and documented.

---

## 1) `fix_bin_to_known_types.py` — auto-detect format by magic bytes and rename

**Why:** sometimes files are downloaded without correct extensions (e.g. `.bin`). This script detects the real type (PDF / ZIP / JPEG / PNG / GIF / WebP / TIFF / BMP / MP3 / WAV / FLAC / OGG / archives TAR / 7z / RAR / GZ / BZ2 / XZ, ISO-BMFF containers — MP4 / MOV / HEIC / AVIF; DOCX / XLSX / PPTX / EPUB / ODT / ODS / ODP and older OLE DOC / XLS / PPT) and renames them to the proper extension. It supports a safe “dry run” mode (no overwrite) and name collision handling (adding `(1)`, `(2)`), optional auto-unzip of ZIP, and a CSV log.

**Key features:**

- **Zero-click mode** (double click / run without args) — scans current folder and applies changes
- `--dry-run` to preview without modifying
- `--ext` to change which source suffix to treat (default `.bin`)
- `--overwrite` to allow overwriting existing files
- `--log` — path to CSV log file
- `--unzip` — after renaming, unzip ZIP files automatically

**How to run (examples):**

```shell
# (0) Double click / no args — apply changes in the script’s directory
python fix_bin_to_known_types.py

# (1) Scan a given folder but just preview changes
python fix_bin_to_known_types.py "/path/to/folder" --dry-run

# (2) Rename only files with suffix .dat and write CSV log
python fix_bin_to_known_types.py "/path/to/folder" --ext .dat --log changes.csv

# (3) Rename, unzip ZIPs, allow overwrite
python fix_bin_to_known_types.py "/path/to/folder" --unzip --overwrite
```

**Suggested integration into the project:**

- **Option A (subcommand):** add `boosty-downloader fix-ext` (or `repair`) with mapping of flags (`--dry-run`, `--ext`, `--log`, `--unzip`, `--overwrite`)
- **Option B (utility):** place under `utils/fix_bin_to_known_types.py` and mention in README as a recommended post-processing step (especially useful when mirroring sources that may lose extensions)
- **Tests:** include byte-signature fixtures for popular formats and test correct renaming, idempotence, collision handling

---

## 2) `build_index_tree_search_folder_subtree.py` — offline `index.html` generator for folder trees

**Why:** to create a convenient offline index of a downloaded library: fast search **by folder names only** (if a folder matches → show its entire subtree: subfolders + files), collapsible/expandable tree, match highlighting, node state persistence (via `localStorage`). In the end, the user gets a browsable “catalog” of their collection in the browser.

**What it does:**

- Recursively scans the directory tree, excluding technical directories (`.git`, `__pycache__`, `.idea`, `.vscode`, `_index`, hidden folders)
- Renders a clean dark-theme `index.html` (responsive layout, sticky header, toolbar with search and “Expand All” / “Collapse All” buttons)
- Search is client-side (no backend), highlights matches and persists open nodes between reloads
- Optionally limit displayed files by extension via `ALLOWED_FILE_EXTS`

**How to run:**

```shell
# Generate index.html in current folder:
python build_index_tree_search_folder_subtree.py

# Then open index.html in browser to browse/search the collection offline.
```

**Suggested integration into the project:**

- **Option A (subcommand):** `boosty-downloader make-index` → scans the `output` directory and writes `index.html`
- **Option B (post-hook):** add a flag to main CLI, e.g. `--make-index`, to auto-generate the index after downloads complete
- In documentation: short section “Offline catalog of downloaded content” with screenshot and examples

---

## Proposed repository layout

```
boosty_downloader/
  …
utils/
  fix_bin_to_known_types.py
  build_index_tree_search_folder_subtree.py
docs/
  postprocessing.md   # instructions, examples, flags
```

## Why this helps users of boosty-downloader

- **Fewer “junk” .bin files:** correct extensions make files clickable in file managers and better recognized by media tools
- **Offline navigation made easy:** many use your downloader as a backup — an `index.html` gives them a self-contained browser interface for searching and browsing
- **Dependency-light:** both utilities are pure Python and run “out of box” (no heavy external deps)

If the additions are useful to the community, I would be honored to have my name included in the “Credits / Contributors” section.

Thank you for your time and effort! 🙌

[build_index_tree_search_folder_subtree_fix.py](https://github.com/user-attachments/files/22618326/build_index_tree_search_folder_subtree_fix.py)

[fix_bin_to_known_types_v5.py](https://github.com/user-attachments/files/22618327/fix_bin_to_known_types_v5.py)

Source: https://github.com/Glitchy-Sheep/boosty-downloader/issues/75

