#!/usr/bin/env python3
"""
Mick Boggis Studios — Master Metadata Pipeline
Orchestrates the full pipeline: form JSON → RIN XML + CD-Text CSV + WAV metadata embedding

Usage:
    python pipeline.py <form_json> [--render-dir <dir>] [--output-dir <dir>]

The pipeline:
1. Reads the form JSON (from the web form or the XLSX)
2. Generates RIN 2.1 XML (validated against XSD)
3. Generates CD-Text CSV (for WaveLab import)
4. Generates CD Track Info summary (for manual entry)
5. If --render-dir is provided, embeds metadata into all WAV files in that directory
6. Outputs everything to the output directory (default: alongside the form JSON)
"""

import json
import sys
import os
import argparse
import datetime
from pathlib import Path


# ── Mick Boggis constants ──────────────────────────────────────────────────
MICK_NAME = "Mick Boggis"
MICK_ISNI = "0000000514812832"
MICK_STUDIO = "Mick Boggis Studios"
MICK_DPID = "PA-DPIDA-2026082102-O"
MICK_ADDRESS = "Parc An Pons, TR17 0HQ, Marazion, UK"
MICK_CREDIT = "Mastered by Mick Boggis"
MICK_ENGINEER_FIELD = f"Mastering Engineer Mick Boggis ISNI: {MICK_ISNI}"


def load_form_json(json_path: str) -> dict:
    """Load the form data from JSON."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_rin(meta: dict, output_path: str) -> dict:
    """Generate RIN 2.1 XML and validate against XSD."""
    # Import here to avoid circular dependency
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)
    
    from rin_generator import generate_rin, validate_xml
    
    xml_path = output_path
    tree = generate_rin(meta)
    tree.write(xml_path, encoding="UTF-8", xml_declaration=True, pretty_print=True)
    
    xsd_dir = os.path.join(script_dir, "..", "DDEX RIN 2.1", "RIN-3171 - RIN 2.1 (XSD)")
    xsd_path = os.path.join(xsd_dir, "recording-information-notification.xsd")
    
    # Re-parse the written file for validation
    from lxml import etree
    parsed = etree.parse(xml_path)
    is_valid, errors = validate_xml(parsed, xsd_path)
    
    validation = {"valid": is_valid, "errors": errors}
    
    return {"xml_path": xml_path, "validation": validation}


def generate_cdtext(meta: dict, output_path: str) -> str:
    """Generate CD-Text CSV for WaveLab import."""
    from cdtext_generator import generate_cdtext_csv
    rows = generate_cdtext_csv(meta, output_path)
    return output_path


def generate_track_info_summary(meta: dict, output_path: str) -> None:
    """Generate a human-readable summary of CD Track Info 1-4 for manual entry."""
    tracks = meta.get("tracks", [])
    lines = []
    lines.append("MICK BOGGIS STUDIOS — CD TRACK INFO SUMMARY")
    lines.append("=" * 50)
    lines.append("Enter these values in WaveLab CD Metadata > CD Track Info 1-4:")
    lines.append("  Track Info 1 = BPM")
    lines.append("  Track Info 2 = Key")
    lines.append("  Track Info 3 = Technical Engineering Credits")
    lines.append("  Track Info 4 = Musician Credits")
    lines.append("")
    lines.append("-" * 50)
    
    for i, track in enumerate(tracks, 1):
        lines.append(f"Track {i}: {track.get('title', 'Untitled')}")
        lines.append(f"  Info 1 (BPM):              {track.get('bpm', '')}")
        lines.append(f"  Info 2 (Key):              {track.get('key', '')}")
        lines.append(f"  Info 3 (Tech Eng Credits):  {MICK_CREDIT}")
        
        # Build musician credits from contributors
        credits = []
        for c in meta.get("contributors", []):
            if c.get("instrument") and c.get("name"):
                credits.append(f"{c['instrument']}: {c['name']}")
        musician_credits = ", ".join(credits) if credits else ""
        lines.append(f"  Info 4 (Musician Credits):  {musician_credits}")
        lines.append("")
    
    lines.append("-" * 50)
    lines.append(f"Engineering credits auto-variable: @riff_info_ieng@")
    lines.append(f"This resolves to: {MICK_ENGINEER_FIELD}")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def embed_wav_metadata(meta: dict, render_dir: str) -> list:
    """
    Embed metadata into all WAV files in the render directory.
    Returns a list of verification results.
    """
    from metadata_embed import embed_all
    
    results = []
    tracks = meta.get("tracks", [])
    
    # Find all WAV files in the render directory, sorted
    wav_files = sorted([f for f in os.listdir(render_dir) if f.lower().endswith(".wav")])
    
    if len(wav_files) != len(tracks):
        print(f"WARNING: {len(wav_files)} WAV files found, {len(tracks)} tracks in metadata")
        print(f"  Files: {wav_files}")
    
    for i, wav_file in enumerate(wav_files):
        wav_path = os.path.join(render_dir, wav_file)
        
        # Get track metadata — try to match by ISRC in filename, else by order
        track_meta = {}
        if i < len(tracks):
            track = tracks[i]
            track_meta = {
                "title": track.get("title", ""),
                "artist": track.get("artist", ""),
                "album": meta.get("project", {}).get("title", ""),
                "performer": track.get("artist", ""),
                "engineer": MICK_ENGINEER_FIELD,
                "genre": track.get("genre", ""),
                "writer": track.get("writer", ""),
                "track": f"{i+1}/{len(tracks)}",
                "isrc": track.get("isrc", ""),
                "bpm": track.get("bpm", ""),
                "key": track.get("key", ""),
                "language": track.get("language", "en"),
                "copyright": meta.get("rights", [{}])[0].get("p_line", "") if meta.get("rights") else "",
                "musician_credits": [
                    (c.get("instrument", ""), c.get("name", ""))
                    for c in meta.get("contributors", [])
                    if c.get("instrument") and c.get("name")
                ],
                "bext_description": f"{track.get('isrc', '')} {track.get('title', '')}",
                "bext_originator": MICK_STUDIO,
                "bext_originator_reference": MICK_DPID,
                "bext_origination_date": datetime.date.today().isoformat(),
                "bext_origination_time": datetime.datetime.now().strftime("%H:%M:%S"),
                "bext_coding_history": f"A=PCM,F={meta.get('technical', {}).get('sample_rate', '48000')},W={meta.get('technical', {}).get('bit_depth', '24')}\r\nA=PCM,F={meta.get('technical', {}).get('sample_rate', '48000')},W={meta.get('technical', {}).get('bit_depth', '24')}",
                "render_date": datetime.date.today().isoformat(),
            }
        
        print(f"  Embedding: {wav_file}")
        result = embed_all(wav_path, track_meta)
        results.append(result)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Mick Boggis Studios — Master Metadata Pipeline")
    parser.add_argument("form_json", help="Path to the form JSON file")
    parser.add_argument("--render-dir", help="Directory containing rendered WAV files to embed metadata into")
    parser.add_argument("--output-dir", help="Output directory (default: alongside form JSON)")
    
    args = parser.parse_args()
    
    # Determine output directory
    output_dir = args.output_dir or os.path.dirname(os.path.abspath(args.form_json))
    os.makedirs(output_dir, exist_ok=True)
    
    # Load form data
    print("=" * 60)
    print("MICK BOGGIS STUDIOS — METADATA PIPELINE")
    print("=" * 60)
    print()
    
    meta = load_form_json(args.form_json)
    project_title = meta.get("project", {}).get("title", "Unknown Project")
    print(f"Project: {project_title}")
    print(f"Tracks: {len(meta.get('tracks', []))}")
    print(f"Contributors: {len(meta.get('contributors', []))}")
    print()
    
    # 1. Generate RIN XML
    print("─" * 60)
    print("[1/4] Generating RIN 2.1 XML...")
    rin_path = os.path.join(output_dir, f"{project_title}_RIN.xml")
    try:
        rin_result = generate_rin(meta, rin_path)
        print(f"  ✓ RIN XML: {rin_result['xml_path']}")
        if rin_result["validation"].get("valid"):
            print(f"  ✓ XSD validation: PASSED")
        else:
            print(f"  ✗ XSD validation: FAILED")
            for err in rin_result["validation"].get("errors", []):
                print(f"    {err}")
    except Exception as e:
        print(f"  ✗ RIN generation failed: {e}")
    
    # 2. Generate CD-Text CSV
    print()
    print("─" * 60)
    print("[2/4] Generating CD-Text CSV...")
    cdtext_path = os.path.join(output_dir, f"{project_title}_CDText.csv")
    try:
        generate_cdtext(meta, cdtext_path)
        print(f"  ✓ CD-Text CSV: {cdtext_path}")
    except Exception as e:
        print(f"  ✗ CD-Text generation failed: {e}")
    
    # 3. Generate CD Track Info summary
    print()
    print("─" * 60)
    print("[3/4] Generating CD Track Info summary...")
    summary_path = os.path.join(output_dir, f"{project_title}_TrackInfo.txt")
    try:
        generate_track_info_summary(meta, summary_path)
        print(f"  ✓ Track Info summary: {summary_path}")
    except Exception as e:
        print(f"  ✗ Track Info summary failed: {e}")
    
    # 4. Embed metadata into WAV files (if render dir provided)
    print()
    print("─" * 60)
    if args.render_dir:
        print(f"[4/4] Embedding metadata into WAV files in {args.render_dir}...")
        try:
            results = embed_wav_metadata(meta, args.render_dir)
            print(f"  ✓ Processed {len(results)} WAV files")
            for r in results:
                chunks = r.get("chunks", [])
                id3 = r.get("id3v2", {})
                print(f"    {os.path.basename(r['file'])}: {len(chunks)} chunks, {len(id3)} ID3v2 tags")
        except Exception as e:
            print(f"  ✗ WAV embedding failed: {e}")
    else:
        print("[4/4] Skipping WAV embedding (no --render-dir provided)")
    
    print()
    print("=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print()
    print("Next steps:")
    print("  1. Import CD-Text CSV into WaveLab (CD-Text Editor > Import)")
    print("  2. Enter CD Track Info 1-4 from the summary file")
    print("  3. Master and render Artist-Title_DIGITAL_MASTER_V1")
    print("  4. Run: python pipeline.py form.json --render-dir <rendered_files>")
    print("  5. Deliver RIN XML + rendered WAVs")


if __name__ == "__main__":
    main()