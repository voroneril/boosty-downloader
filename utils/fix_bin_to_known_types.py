#!/usr/bin/env python3
"""
fix_bin_to_known_types_v5.py

Zero-click defaults for double-click launch:
- If started **без аргументов**, сканирует папку, где лежит скрипт, и **сразу ПЕРЕИМЕНОВЫВАЕТ** (apply).
- Без перезаписи: если целевой файл существует, добавит " (1)", " (2)" и т. п.
- Покажет сводку; на Windows при запуске без аргументов попросит нажать Enter перед закрытием окна.

Параметры (необязательны — только если нужно изменить поведение):
  root (путь)   — задать другую папку
  --ext .dat    — искать другой исходный суффикс (по умолчанию .bin)
  --overwrite   — разрешить перезапись целевых файлов
  --log CSV     — сохранить CSV-лог
  --unzip       — авто-распаковать ZIP после переименования
  --dry-run     — НЕ менять файлы, только показать действия (если нужно обезопаситься)
"""

from __future__ import annotations
import argparse
from pathlib import Path
import sys
import csv
import os

def read_head(path: Path, n: int = 1024) -> bytes:
    with path.open("rb") as f:
        return f.read(n)

def read_at(path: Path, offset: int, n: int) -> bytes:
    with path.open("rb") as f:
        f.seek(offset)
        return f.read(n)

def unique_dest(dest: Path) -> Path:
    if not dest.exists():
        return dest
    stem = dest.stem
    ext = dest.suffix
    parent = dest.parent
    i = 1
    while True:
        candidate = parent / f"{stem} ({i}){ext}"
        if not candidate.exists():
            return candidate
        i += 1

def unzip_to_folder(zip_path: Path, target_dir: Path) -> None:
    import zipfile
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(target_dir)

# --- format checks (same as v4) ---
def is_zip(head: bytes) -> bool: return head[:4] in (b"\x50\x4B\x03\x04", b"\x50\x4B\x05\x06", b"\x50\x4B\x07\x08")
def is_pdf(head: bytes) -> bool: return head.startswith(b"%PDF-")
def is_rar(head: bytes) -> bool: return head.startswith(b"Rar!\x1A\x07\x00") or head.startswith(b"Rar!\x1A\x07\x01\x00")
def is_7z(head: bytes) -> bool: return head.startswith(b"\x37\x7A\xBC\xAF\x27\x1C")
def is_gz(head: bytes) -> bool: return head.startswith(b"\x1F\x8B\x08")
def is_bz2(head: bytes) -> bool: return head.startswith(b"BZh")
def is_xz(head: bytes) -> bool: return head.startswith(b"\xFD\x37\x7A\x58\x5A\x00")
def is_tar(path: Path) -> bool:
    try: return read_at(path, 257, 5) == b"ustar"
    except Exception: return False
def is_jpeg(head: bytes) -> bool: return head[:3] == b"\xFF\xD8\xFF"
def is_png(head: bytes) -> bool: return head.startswith(b"\x89PNG\r\n\x1A\x0A")
def is_gif(head: bytes) -> bool: return head.startswith(b"GIF87a") or head.startswith(b"GIF89a")
def is_webp(head: bytes) -> bool: return head.startswith(b"RIFF") and head[8:12] == b"WEBP"
def is_tiff(head: bytes) -> bool: return head.startswith(b"II*\x00") or head.startswith(b"MM\x00*")
def is_bmp(head: bytes) -> bool: return head.startswith(b"BM")
def is_iso_bmff(head: bytes) -> bool: return len(head) >= 12 and head[4:8] == b"ftyp"
def iso_bmff_brand(head: bytes) -> set[bytes]:
    brands = set()
    if len(head) >= 32 and head[4:8] == b"ftyp":
        brands.add(head[8:12])
        for i in range(16, min(len(head), 64), 4):
            brands.add(head[i:i+4])
    return brands
def is_mp3(head: bytes) -> bool: return head.startswith(b"ID3")
def is_wav(head: bytes) -> bool: return head.startswith(b"RIFF") and head[8:12] == b"WAVE"
def is_flac(head: bytes) -> bool: return head.startswith(b"fLaC")
def is_ogg(head: bytes) -> bool: return head.startswith(b"OggS")
def is_rtf(head: bytes) -> bool: return head.startswith(b"{\\rtf")
def is_ole_cfb(head: bytes) -> bool: return head.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1")

def detect_zip_subtype(path: Path) -> str | None:
    import zipfile
    try:
        with zipfile.ZipFile(path, 'r') as zf:
            namelist = set(zf.namelist())
            if "mimetype" in namelist:
                try:
                    with zf.open("mimetype") as m:
                        mt = m.read(100).decode("ascii", errors="ignore").strip()
                    if mt == "application/epub+zip":
                        return "epub"
                    od_map = {
                        "application/vnd.oasis.opendocument.text": "odt",
                        "application/vnd.oasis.opendocument.spreadsheet": "ods",
                        "application/vnd.oasis.opendocument.presentation": "odp",
                    }
                    if mt in od_map:
                        return od_map[mt]
                except Exception:
                    pass
            if "[Content_Types].xml" in namelist:
                if any(n.startswith("word/") for n in namelist): return "docx"
                if any(n.startswith("xl/") for n in namelist):   return "xlsx"
                if any(n.startswith("ppt/") for n in namelist):  return "pptx"
            return None
    except Exception:
        return None

def detect_ole_subtype(head: bytes) -> str | None:
    h = head
    if b"WordDocument" in h or b"\x00W\x00o\x00r\x00d\x00D\x00o\x00c\x00u\x00m\x00e\x00n\x00t\x00" in h: return "doc"
    if b"Workbook" in h or b"\x00W\x00o\x00r\x00k\x00b\x00o\x00o\x00k\x00" in h: return "xls"
    if b"PowerPoint Document" in h or b"\x00P\x00o\x00w\x00e\x00r\x00P\x00o\x00i\x00n\x00t\x00 \x00D\x00o\x00c\x00u\x00m\x00e\x00n\x00t\x00" in h: return "ppt"
    return None

def detect_type(path: Path) -> str | None:
    try:
        with path.open("rb") as f:
            head = f.read(4096)
    except Exception:
        return None

    if is_pdf(head): return "pdf"
    if is_rtf(head): return "rtf"

    if is_zip(head):
        subtype = detect_zip_subtype(path)
        return subtype or "zip"
    if is_rar(head): return "rar"
    if is_7z(head):  return "7z"
    if is_gz(head):  return "gz"
    if is_bz2(head): return "bz2"
    if is_xz(head):  return "xz"
    if is_tar(path): return "tar"

    if is_jpeg(head): return "jpg"
    if is_png(head):  return "png"
    if is_gif(head):  return "gif"
    if is_webp(head): return "webp"
    if is_tiff(head): return "tiff"
    if is_bmp(head):  return "bmp"

    if is_iso_bmff(head):
        brands = iso_bmff_brand(head)
        heif_brands = {b"heic", b"heix", b"hevc", b"heim", b"heis", b"mif1", b"msf1"}
        avif_brands = {b"avif", b"avis"}
        mov_brand  = {b"qt  "}
        mp4ish     = {b"isom", b"iso2", b"mp41", b"mp42", b"iso6", b"avc1", b"MSNV", b"M4V "}
        if brands & avif_brands: return "avif"
        if brands & heif_brands: return "heic"
        if brands & mov_brand:   return "mov"
        if brands & mp4ish:      return "mp4"

    if is_mp3(head): return "mp3"
    if is_wav(head): return "wav"
    if is_flac(head): return "flac"
    if is_ogg(head): return "ogg"

    if is_ole_cfb(head):
        subtype = detect_ole_subtype(head)
        if subtype: return subtype
        return None

    return None

def process(root: Path, *, ext: str, apply: bool, overwrite: bool, log_path: Path | None, unzip: bool) -> dict:
    changed = skipped = errors = total = unzipped = 0
    rows = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() == ext.lower():
            total += 1
            detected = detect_type(p)
            if detected:
                new_suffix = f".{detected}"
                dest = p.with_suffix(new_suffix)
                final_dest = dest if (overwrite or not dest.exists()) else unique_dest(dest)
                action = "rename" if apply else "would_rename"
                try:
                    if apply: p.rename(final_dest)
                    rows.append({"source": str(p), "detected": detected, "destination": str(final_dest), "action": action, "status": "ok"})
                    print(f"[{action}] {p} -> {final_dest}")
                    if apply:
                        changed += 1
                        if unzip and final_dest.suffix.lower() == ".zip":
                            try:
                                out_dir = final_dest.with_suffix("")
                                out_dir = out_dir.parent / (out_dir.name + "_unzipped")
                                out_dir.mkdir(exist_ok=True)
                                unzip_to_folder(final_dest, out_dir)
                                print(f"[unzip] {final_dest} -> {out_dir}")
                                unzipped += 1
                            except Exception as e:
                                print(f"[unzip-error] {final_dest}: {e}", file=sys.stderr)
                except Exception as e:
                    errors += 1
                    print(f"[error] {p}: {e}", file=sys.stderr)
                    rows.append({"source": str(p), "detected": detected, "destination": str(final_dest), "action": action, "status": f"error: {e}"})
            else:
                skipped += 1
                print(f"[skip] {p} (unknown format)")
                rows.append({"source": str(p), "detected": "unknown", "destination": "", "action": "skip", "status": "unknown"})
    summary = {
        "root": str(root),
        "ext": ext,
        "total_candidates": total,
        "renamed": changed if apply else 0,
        "would_rename": changed if not apply else 0,
        "unzipped": unzipped if apply else 0,
        "skipped": skipped,
        "errors": errors,
    }
    if log_path:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("w", newline="", encoding="utf-8") as f:
                import csv as _csv
                writer = _csv.DictWriter(f, fieldnames=["source","detected","destination","action","status"])
                writer.writeheader(); writer.writerows(rows)
            print(f"[log] Saved to {log_path}")
        except Exception as e:
            print(f"[log-error] {e}", file=sys.stderr)

    print("\nSummary:")
    for k, v in summary.items(): print(f"  {k}: {v}")
    return summary

def maybe_pause(need_pause: bool):
    try:
        if need_pause and os.name == "nt":
            input("\nГотово. Нажмите Enter, чтобы закрыть окно...")
    except EOFError:
        pass

def main():
    parser = argparse.ArgumentParser(description="Detect and fix misnamed files by magic bytes (auto-apply if no args).", add_help=True)
    parser.add_argument("root", nargs="?", default=None, help="Папка для сканирования. По умолчанию — папка со скриптом.")
    parser.add_argument("--ext", default=".bin", help="Какое расширение искать (по умолчанию .bin).")
    parser.add_argument("--overwrite", action="store_true", help="Разрешить перезапись уже существующих файлов.")
    parser.add_argument("--log", type=Path, default=None, help="CSV-лог изменений.")
    parser.add_argument("--unzip", action="store_true", help="Распаковывать ZIP после переименования.")
    parser.add_argument("--dry-run", action="store_true", help="Только показать, что будет сделано, без изменений.")
    args = parser.parse_args()

    no_args_mode = (len(sys.argv) == 1)  # двойной клик / без параметров
    script_dir = Path(__file__).resolve().parent
    root = Path(args.root).expanduser().resolve() if args.root else script_dir

    if not root.exists():
        print(f"Root path does not exist: {root}", file=sys.stderr); sys.exit(2)

    # Если без аргументов — включаем apply по умолчанию, иначе уважаем --dry-run
    apply = True if no_args_mode else (not args.dry_run)

    print(f"[info] Scanning root: {root}")
    print(f"[info] Mode: {'APPLY (rename files)' if apply else 'DRY-RUN (no changes)'}")
    print(f"[info] Source extension: {args.ext}")
    if args.log: print(f"[info] Logging to: {args.log}")
    if args.unzip: print(f"[info] Unzip after .zip rename: enabled")
    if args.overwrite: print(f"[info] Overwrite: enabled")

    process(root, ext=args.ext, apply=apply, overwrite=args.overwrite, log_path=args.log, unzip=args.unzip)

    # Пауза, чтобы окно не закрывалось мгновенно при двойном клике
    maybe_pause(no_args_mode)

if __name__ == "__main__":
    main()
