# Changelog

## v1.0

- Added Windows and Linux GUI builds.
- Added Turbo, Fast, Smart, Tryhard, and Unhinged modes.
- Added structured GUI logging instead of parsing arbitrary subprocess chunks.
- Added configurable chunk sizes and worker counts.
- Added entropy-soup bailout for incompressible data.
- Added ZIP/TAR/GZ/BZ2/XZ/LZMA extraction plus optional 7Z/RAR/TAR.ZST extraction.
- Added partial-output cleanup after cancel or failure.
- Kept backwards compatibility with the NAH1 archive format.

## v0.4.1

- Fixed Finder/open-with handoff for `.nah` files in the macOS GUI.

## v0.4

- Added a redesigned macOS GUI, more compression modes, better logs, archive extraction, and entropy detection.
