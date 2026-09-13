# NAH

> **Lossless compression that knows when to say nah.**

![Version](https://img.shields.io/badge/version-1.0-blue)
![Platforms](https://img.shields.io/badge/platforms-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-Apache--2.0-green)

NAH is a lossless file-compression project with a slightly unserious personality and one serious rule: **if compressing a chunk makes it bigger, NAH keeps the smaller candidate instead.**

It splits files into chunks, compares multiple lossless codecs, and stores the best result for each chunk. Unpacking reconstructs the original bytes exactly.

> **Version note:** **NAH v1.0** is the application release. The archive format remains **NAH1 / format version 1**, preserving compatibility with earlier `.nah` archives.

## Highlights

- Five modes: **Turbo, Fast, Smart, Tryhard, Unhinged**
- Per-chunk selection between **STORE, DEFLATE, BZ2, and LZMA**
- **Skip entropy soup** for random, encrypted, or already-compressed data
- CRC32 verification during unpacking
- Structured GUI logs instead of parsing arbitrary subprocess chunks
- Archive extraction support for ZIP, TAR, GZ, BZ2, XZ, and LZMA
- Optional 7Z, RAR, and TAR.ZST extraction through compatible external tools
- Windows, Linux, and macOS versions

## Compression modes

| Mode | Behaviour |
| --- | --- |
| **Turbo** | DEFLATE level 1 with aggressive entropy bailout. Fastest. |
| **Fast** | DEFLATE-focused for a good speed/size balance. |
| **Smart** | Default. Probes chunks and only tries expensive codecs when useful. |
| **Tryhard** | Adds stronger BZ2/LZMA attempts while retaining Fast's DEFLATE candidate. |
| **Unhinged** | Maximum built-in effort on promising chunks. |

## Random files vs. mathematics

NAH does **not** claim that truly random data can always be made smaller. No lossless compressor can guarantee a shorter unique representation for every possible input.

With **Skip entropy soup** enabled, NAH detects chunks that are extremely unlikely to compress and stores them immediately. So `/dev/urandom` doesn't make Tryhard spend geological time discovering that randomness is, in fact, random. 💀

## Archive extraction

| Format | Support |
| --- | --- |
| `.nah` | Built in |
| `.zip` | Built in |
| `.tar`, `.tar.gz`, `.tgz` | Built in |
| `.tar.bz2`, `.tbz`, `.tbz2` | Built in |
| `.tar.xz`, `.txz`, `.tar.lzma`, `.tlz` | Built in |
| `.gz`, `.bz2`, `.xz`, `.lzma` | Built in |
| `.7z`, `.rar` | Via a compatible external extractor |
| `.tar.zst`, `.tzst` | Via an external extractor with Zstandard support |

## How `.nah` works

A NAH1 archive stores the original filename and divides its contents into independent chunks. For each chunk, NAH can compare:

- **STORE** — no compression
- **DEFLATE** — zlib
- **BZ2** — bzip2
- **LZMA** — LZMA/XZ-family compression

Only the smallest candidate is written. Each chunk records its codec, original size, stored size, and CRC32. When unpacking, NAH reconstructs and verifies the original stream.

That means a successful round trip should not merely *sound* or *look* the same — the restored file is intended to be **byte-for-byte identical**.

## Current limitations

- NAH1 currently compresses individual files rather than whole folders.
- Some archive formats such as 7Z and RAR require an external extractor.
- Incompressible files can become a tiny bit larger because the NAH container itself needs metadata.
- There is no fake “compress every random file by 10 MB” mode. Mathematics has unfortunately declined the feature request.

## Project status

**v1.0** expands NAH beyond its original macOS build with Windows and Linux versions, improved compression modes, reliable GUI logging, entropy bailout, and broader archive extraction.

See [`CHANGELOG.md`](CHANGELOG.md) for the version history. Source/build files and release packages are being added to this repository as the v1.0 release is assembled.

## License

NAH is licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE).

---

Made because `.zip` looked at a file and NAH said **nah, I can try harder.**