#!/usr/bin/env python3
"""
Mick Boggis Studios — Metadata Embedding Engine
Embeds RIFF INFO, BEXT, ID3v2, MD5, and aXML chunks into WAV files in a single pass.
No WaveLab metadata preset needed. No auto-variables. Actual values from form data.

Usage:
    python metadata_embed.py <wav_file> <metadata_json>
    
    metadata_json: path to JSON file with all track metadata
"""

import struct
import io
import hashlib
import os
import json
import sys
import datetime
from pathlib import Path


def _pad(data: bytes, alignment: int = 2) -> bytes:
    """Pad bytes to even alignment."""
    if len(data) % alignment != 0:
        data += b"\x00" * (alignment - len(data) % alignment)
    return data


def _ascii_field(value: str, size: int) -> bytes:
    """Encode a string as fixed-width ASCII, null-padded."""
    return value.encode("ascii", errors="replace")[:size].ljust(size, b"\x00")


def build_bext(meta: dict) -> bytes:
    """Build the BEXT (Broadcast Extension) chunk."""
    bext = b""
    bext += _ascii_field(meta.get("bext_description", ""), 256)
    bext += _ascii_field(meta.get("bext_originator", "Mick Boggis Studios"), 32)
    bext += _ascii_field(meta.get("bext_originator_reference", ""), 32)
    bext += _ascii_field(meta.get("bext_origination_date", ""), 10)
    bext += _ascii_field(meta.get("bext_origination_time", ""), 8)
    # TimeReference (64-bit) — 0 for rendered files
    bext += struct.pack("<I", 0)  # low
    bext += struct.pack("<I", 0)  # high
    bext += struct.pack("<H", 2)  # BWF version 2
    bext += b"\x00" * 64          # UMID (blank — WaveLab can auto-generate)
    # Loudness fields (BWF v2)
    bext += struct.pack("<H", 0)   # Loudness version
    bext += struct.pack("<h", 0)   # Loudness value
    bext += struct.pack("<h", 0)   # Loudness range
    bext += struct.pack("<h", 0)   # Max true peak
    bext += struct.pack("<h", 0)   # Max momentary loudness
    bext += struct.pack("<h", 0)   # Max short-term loudness
    bext += b"\x00" * 180          # Reserved
    # Coding history
    coding = meta.get("bext_coding_history", "")
    bext += coding.encode("ascii", errors="replace")
    return bext


def build_riff_info(meta: dict) -> bytes:
    """Build the RIFF INFO LIST chunk."""
    fields = [
        ("IART", meta.get("artist", "")),
        ("INAM", meta.get("title", "")),
        ("IPRD", meta.get("album", "")),
        ("IENG", meta.get("engineer", "Mastering Engineer Mick Boggis ISNI: 0000000514812832")),
        ("IGNR", meta.get("genre", "")),
        ("IWRI", meta.get("writer", "")),
        ("ISFT", "Mick Boggis Studios Metadata Pipeline"),
        ("ICRD", meta.get("render_date", datetime.date.today().isoformat())),
        ("ITRK", meta.get("track", "")),
    ]
    info_data = b""
    for code, value in fields:
        val_bytes = value.encode("utf-8", errors="replace") + b"\x00"
        val_bytes = _pad(val_bytes)
        info_data += code.encode("ascii") + struct.pack("<I", len(val_bytes)) + val_bytes
    return b"INFO" + info_data


def build_axml(isrc: str) -> bytes:
    """Build the aXML chunk with EBU Core ISRC metadata."""
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ebuCoreMain xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:ebucore="urn:ebu:metadata-schema:ebuCore_2012">
  <ebucore:coreMetadata>
    <ebucore:identifier>
      <dc:identifier typeLabel="ISRC" typeDefinition="International Standard Recording Code">{isrc}</dc:identifier>
    </ebucore:identifier>
  </ebucore:coreMetadata>
</ebuCoreMain>"""
    return xml.encode("utf-8")


def embed_riff_bext_md5_axml(wav_path: str, meta: dict) -> None:
    """
    Rewrite a WAV file with BEXT, RIFF INFO LIST, MD5, and aXML chunks.
    Preserves the original fmt and data chunks.
    """
    with open(wav_path, "rb") as f:
        wav_data = f.read()

    if wav_data[:4] != b"RIFF" or wav_data[8:12] != b"WAVE":
        raise ValueError(f"Not a valid RIFF/WAVE file: {wav_path}")

    # Parse existing chunks
    existing = {}
    pos = 12
    while pos < len(wav_data):
        cid = wav_data[pos:pos + 4]
        csz = struct.unpack("<I", wav_data[pos + 4:pos + 8])[0]
        cdata = wav_data[pos + 8:pos + 8 + csz]
        existing[cid] = cdata
        pos += 8 + csz
        if csz % 2 != 0:
            pos += 1

    if b"fmt " not in existing or b"data" not in existing:
        raise ValueError(f"Missing fmt or data chunk in {wav_path}")

    fmt_data = existing[b"fmt "]
    audio_data = existing[b"data"]

    # Build new chunks
    bext_chunk = build_bext(meta)
    info_chunk = build_riff_info(meta)
    md5_chunk = hashlib.md5(audio_data).digest()
    axml_chunk = build_axml(meta.get("isrc", ""))

    # Rebuild WAV: bext, fmt, data, LIST, MD5, axml
    output = io.BytesIO()
    output.write(b"RIFF")
    output.write(b"\x00\x00\x00\x00")  # placeholder for size
    output.write(b"WAVE")

    chunks_to_write = [
        (b"bext", bext_chunk),
        (b"fmt ", fmt_data),
        (b"data", audio_data),
        (b"LIST", info_chunk),
        (b"MD5 ", md5_chunk),
        (b"axml", axml_chunk),
    ]

    for cid, cdata in chunks_to_write:
        output.write(cid)
        output.write(struct.pack("<I", len(cdata)))
        output.write(cdata)
        if len(cdata) % 2 != 0:
            output.write(b"\x00")

    total_size = output.tell() - 8
    output.seek(4)
    output.write(struct.pack("<I", total_size))

    with open(wav_path, "wb") as f:
        f.write(output.getvalue())


def embed_id3v2(wav_path: str, meta: dict) -> None:
    """Add ID3v2 tags to a WAV file using mutagen."""
    from mutagen.wave import WAVE
    from mutagen.id3 import (
        TIT2, TPE1, TPE2, TALB, TBPM, TKEY, TSRC, TCOM, TCON, TCOP,
        COMM, TLAN, TMCL, TRCK, TDRC, TOPE, TOLY, TEXT, TIT1
    )

    f = WAVE(wav_path)
    if f.tags is None:
        f.add_tags()

    tags = f.tags
    tags.add(TIT2(encoding=3, text=meta.get("title", "")))
    tags.add(TPE1(encoding=3, text=meta.get("artist", "")))
    tags.add(TPE2(encoding=3, text=meta.get("album", "")))
    tags.add(TALB(encoding=3, text=meta.get("album", "")))
    tags.add(TBPM(encoding=3, text=meta.get("bpm", "")))
    tags.add(TKEY(encoding=3, text=meta.get("key", "")))
    tags.add(TSRC(encoding=3, text=meta.get("isrc", "")))
    tags.add(TCOM(encoding=3, text=meta.get("writer", "")))
    tags.add(TCON(encoding=3, text=meta.get("genre", "")))
    tags.add(TCOP(encoding=3, text=meta.get("copyright", "")))
    tags.add(COMM(encoding=3, lang="eng", desc="", text="Mastered by Mick Boggis"))
    tags.add(TRCK(encoding=3, text=meta.get("track", "")))
    tags.add(TDRC(encoding=3, text=str(datetime.date.today().year)))
    tags.add(TLAN(encoding=3, text=meta.get("language", "")))

    # Musician Credits List — list of (instrument, name) tuples
    credits = meta.get("musician_credits", [])
    if credits:
        tags.add(TMCL(encoding=3, people=[(instr, name) for instr, name in credits]))

    tags.add(TOPE(encoding=3, text=meta.get("performer", meta.get("artist", ""))))
    tags.add(TOLY(encoding=3, text=meta.get("writer", "")))
    tags.add(TIT1(encoding=3, text="Music"))  # Content group
    if meta.get("lyrics"):
        tags.add(TEXT(encoding=3, text=meta["lyrics"]))

    f.save()


def embed_all(wav_path: str, meta: dict) -> dict:
    """
    Single-pass embedding: RIFF INFO + BEXT + MD5 + aXML + ID3v2.
    Returns a verification summary.
    """
    # Step 1: RIFF INFO + BEXT + MD5 + aXML (pure Python, rewrites file)
    embed_riff_bext_md5_axml(wav_path, meta)

    # Step 2: ID3v2 tags (mutagen, appends to the file)
    embed_id3v2(wav_path, meta)

    # Step 3: Verify
    from mutagen.wave import WAVE
    f = WAVE(wav_path)
    verify = {"file": wav_path, "size_bytes": os.path.getsize(wav_path), "id3v2": {}}
    if f.tags:
        for key in sorted(f.tags.keys()):
            tag = f.tags[key]
            verify["id3v2"][key] = str(tag)

    # Verify binary chunks
    with open(wav_path, "rb") as fh:
        data = fh.read()
    chunks_found = []
    pos = 12
    while pos < len(data):
        cid = data[pos:pos + 4]
        if pos + 8 > len(data):
            break
        csz = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        chunks_found.append(cid.decode("ascii", errors="replace"))
        pos += 8 + csz
        if csz % 2 != 0:
            pos += 1
    verify["chunks"] = chunks_found

    return verify


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python metadata_embed.py <wav_file> <metadata_json>")
        sys.exit(1)

    wav_path = sys.argv[1]
    json_path = sys.argv[2]

    with open(json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    result = embed_all(wav_path, meta)
    print(json.dumps(result, indent=2))