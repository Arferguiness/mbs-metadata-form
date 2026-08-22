#!/usr/bin/env python3
"""
Mick Boggis Studios — CD-Text CSV Generator
Generates a CSV file for WaveLab Pro 13 CD-Text import.

WaveLab imports CD-Text from a CSV file (UTF-8, semicolon-separated).
First row = album-level CD-Text. Subsequent rows = per-track CD-Text.

CD-Text fields (per the Red Book CD-Text standard):
- Title (album or track title)
- Performer (artist)
- Songwriter
- Composer (optional, same as songwriter for most releases)
- Message ("Mastered by Mick Boggis")

Usage:
    python cdtext_generator.py <metadata_json> <output_csv>
"""

import json
import sys
import csv
import io


def generate_cdtext_csv(meta: dict, output_path: str) -> None:
    """
    Generate a CD-Text CSV file for WaveLab import.
    
    WaveLab expects semicolon-separated CSV, UTF-8 encoded.
    Row 1: album-level (title, performer, songwriter, composer, message, ISRC)
    Row 2+: per-track (title, performer, songwriter, composer, message, ISRC)
    """
    project = meta.get("project", {})
    tracks = meta.get("tracks", [])
    
    # Determine album-level values
    album_title = project.get("title", "")
    
    # Use the first track's display artist as the album performer
    # (all tracks typically share the same performer; batch-copy in WaveLab handles this)
    if tracks:
        album_performer = tracks[0].get("artist", project.get("label", ""))
    else:
        album_performer = project.get("label", "")
    
    # Album songwriter — leave blank if tracks have different writers
    album_songwriter = ""
    if tracks and all(t.get("writer", "") == tracks[0].get("writer", "") for t in tracks):
        album_songwriter = tracks[0].get("writer", "")
    
    album_message = "Mastered by Mick Boggis"
    
    # Build rows
    rows = []
    
    # Album row
    rows.append([
        album_title,           # Title
        album_performer,       # Performer
        album_songwriter,      # Songwriter
        album_songwriter,      # Composer (same as songwriter)
        album_message,         # Message
        "",                    # ISRC (album level — blank)
    ])
    
    # Track rows
    for track in tracks:
        rows.append([
            track.get("title", ""),
            track.get("artist", album_performer),
            track.get("writer", ""),
            track.get("writer", ""),      # Composer = Songwriter
            "Mastered by Mick Boggis",     # Message per track
            track.get("isrc", ""),          # ISRC
        ])
    
    # Write as semicolon-separated CSV, UTF-8
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        for row in rows:
            writer.writerow(row)
    
    return rows


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python cdtext_generator.py <metadata_json> <output_csv>")
        sys.exit(1)
    
    json_path = sys.argv[1]
    output_path = sys.argv[2]
    
    with open(json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    
    rows = generate_cdtext_csv(meta, output_path)
    
    print(f"CD-Text CSV written to: {output_path}")
    print(f"Rows: {len(rows)} (1 album + {len(rows)-1} tracks)")
    print()
    print("Preview:")
    for i, row in enumerate(rows):
        label = "ALBUM" if i == 0 else f"Track {i}"
        print(f"  {label}: {' | '.join(row[:3])}...")