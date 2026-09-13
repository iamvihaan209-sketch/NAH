# NAH

> **Lossless compression that knows when to say nah.**

[![Build NAH v1.0](https://github.com/iamvihaan209-sketch/NAH/actions/workflows/build.yml/badge.svg)](https://github.com/iamvihaan209-sketch/NAH/actions/workflows/build.yml)
![Python 3](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-green)

NAH is a small lossless file compressor with a slightly unserious personality and one serious rule: **if compression makes a chunk bigger, NAH keeps the smaller version instead.**

The app splits a file into chunks, tries several lossless codecs, stores the winner for each chunk, and can reconstruct the original bytes exactly. It also includes a GUI and archive extraction tools.

> **Version note:** **v1.0** is the application release for Windows and Linux. The on-disk archive format is still **NAH1 / format version 1**, so earlier `.nah` archives remain compatible.

## Highlights

- Five modes: **Turbo, Fast, Smart, Tryhard, Unhinged**
- Per-chunk selection between **STORE, DEFLATE, BZ2, and LZMA**
- **Skip entropy soup** option for random/encrypted/already-tight data
- CRC32 verification while unpacking
- GUI with structured, reliable in-app logs
- Extracts `.zip`, `.tar`, `.tar.gz`, `.tar.bz2`, `.tar.xz`, `.gz`, `.bz2`, `.xz`, and `.lzma`
- Optional extraction of `.7z`, `.rar`, and `.tar.zst` through external tools when available
- Windows and Linux standalone builds through GitHub Actions

## Compression modes

| Mode | Behaviour |
| --- | --- |
| **Turbo** | DEFLATE level 1 and aggressive entropy bailout. Fastest option. |
| **Fast** | DEFLATE-focused. Good when you mainly care about speed. |
| **Smart** | Default. Probes chunks and only tries expensive codecs when useful. |
| **Tryhard** | Tries stronger BZ2/LZMA candidates while keeping Fast's DEFLATE candidate. |
| **Unhinged** | Maximum built-in effort, including stronger LZMA settings on promising data. |

### About random files

NAH does **not** pretend that truly random data can always be made smaller. Lossless compression cannot guarantee that every possible input maps to a shorter unique output.

With **Skip entropy soup** enabled, NAH quickly detects chunks that are extremely unlikely to compress and stores them instead of wasting ages trying every codec. So `/dev/urandom` should stay essentially the same size plus a tiny amount of container metadata rather than taking geological time to prove that random bytes are random. 💀

## Run from source

NAH's compressor and GUI use Python's standard library. You need **Python 3.10+** and **Tkinter**.

### Linux

```bash
git clone https://github.com/iamvihaan209-sketch/NAH.git
cd NAH
python3 src/nah_gui.py
```

Some distributions package Tkinter separately as `python3-tk`.

### Windows

```powershell
git clone https://github.com/iamvihaan209-sketch/NAH.git
cd NAH
pyw src\nah_gui.py
```

## CLI

```bash
# Smart mode
python src/nah.py pack example.bin

# Tryhard
python src/nah.py pack example.bin --mode max

# Unhinged
python src/nah.py pack example.bin --mode unhinged

# Restore the original bytes
python src/nah.py unpack example.bin.nah

# See which codecs won
python src/nah.py inspect example.bin.nah

# Decode + verify every chunk
python src/nah.py prove-it example.bin.nah

# Extract another archive format
python src/nah.py extract archive.zip
```

## Archive extraction

| Format | Support |
| --- | --- |
| `.nah` | Built in |
| `.zip` | Built in |
| `.tar`, `.tar.gz`, `.tgz` | Built in |
| `.tar.bz2`, `.tbz`, `.tbz2` | Built in |
| `.tar.xz`, `.txz`, `.tar.lzma`, `.tlz` | Built in |
| `.gz`, `.bz2`, `.xz`, `.lzma` | Built in |
| `.7z`, `.rar` | External extractor (`7z`/`7zz`, `unar`, `unrar`, or capable `bsdtar`) |
| `.tar.zst`, `.tzst` | External extractor with Zstandard support |

ZIP and TAR extraction validate output paths before writing so entries cannot simply escape the destination with `../` paths. For externally handled formats, safety also depends on the extractor being used.

## Standalone builds

The repository includes a GitHub Actions workflow that builds Windows and Linux versions whenever a `v*` tag is pushed, or when the workflow is run manually.

You can also build locally with PyInstaller:

```bash
python -m pip install pyinstaller
```

**Linux:**

```bash
cd linux
./build-executable.sh
```

**Windows:**

```powershell
cd windows
.\build-executable.ps1
```

## How `.nah` works

A NAH1 archive stores the original filename and splits the input into independent chunks. Each chunk can be stored with one of these codecs:

- **STORE** — no compression
- **DEFLATE** — zlib
- **BZ2** — bzip2
- **LZMA** — LZMA/XZ-family compression

NAH writes only the smallest candidate it tried. Each chunk includes its original size, stored size, codec ID, and CRC32. During unpacking, NAH reconstructs the original stream and verifies the chunk before writing it.

That means a successful `.nah` round trip should not merely *sound* or *look* identical — the restored file is intended to be **byte-for-byte identical**.

## Repository layout

```text
src/
  nah.py             compressor + archive engine + CLI
  nah_gui.py         cross-platform GUI
linux/               Linux launch/install/build helpers
windows/             Windows launch/build/file-association helpers
.github/workflows/   automated Windows + Linux builds
```

## Current limitations

- NAH1 currently compresses **individual files**, not entire folders.
- `.7z`, `.rar`, and `.tar.zst` extraction requires an external extractor.
- Incompressible data can become very slightly larger because the archive needs headers and metadata.
- Source builds require Python 3 + Tkinter; standalone binaries are produced with PyInstaller.

## Quick sanity tests

- A large all-zero file should become dramatically smaller.
- Cryptographically random data should trigger entropy bailout and stay almost the same size.
- Unpacking a `.nah` file should reproduce the original SHA-256 hash exactly.

## License

NAH is licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE).

---

Made because `.zip` looked at a file and NAH said **nah, I can try harder.**