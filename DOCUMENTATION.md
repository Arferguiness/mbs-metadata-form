# Mick Boggis Studios — Metadata Pipeline Documentation

## Overview

The Metadata Pipeline takes artist-submitted form data and produces:
1. **RIN 2.1 XML** — validated against DDEX XSD schemas
2. **CD-Text CSV** — for one-click import into WaveLab Pro 13
3. **CD Track Info summary** — for manual entry of BPM/Key/Credits
4. **Embedded WAV files** — all metadata chunks written directly by Python

**No MICK DEFAULT.dat. No auto-variables.** Python writes actual values from the form directly into the WAV file chunks after WaveLab renders clean audio.

## Pipeline Location

```
V:\My Drive\Obsidian Vaults\Mick's Custom WaveLab Workflow\Metadata Pipeline\
├── pipeline.py            — master orchestrator
├── metadata_embed.py      — RIFF+BEXT+MD5+aXML+ID3v2 embedding
├── rin_generator.py       — DDEX RIN 2.1 XML generator (XSD-validated)
├── cdtext_generator.py    — WaveLab CD-Text CSV generator
├── form.html              — artist-facing web form (self-contained)
├── form_lists.json        — 18 dropdown lists from XLSX
├── test_project.json      — sample test data
└── DDEX RIN 2.1\          — XSD schemas (reference)
```

## Prerequisites

```bash
pip install mutagen lxml openpyxl
```

## Step-by-Step Workflow

### Step 1: Artist fills the form

Send the artist `form.html` (or host it on GitHub Pages). The artist fills in:
- Project details (title, type, catalogue number, label)
- Sound Recording per track (ISRC, title, duration, genre, key, BPM, etc.)
- Session details (recording, mixing — mastering pre-filled with Mick's details)
- Contributors (Mick Boggis pre-filled as MasteringEngineer, read-only)
- Writers & splits
- Rights & ownership
- Technical details

The artist clicks **Submit** → downloads a JSON file → emails it to `mickmastering@gmail.com`.

### Step 2: Run the pipeline (pre-master)

```bash
cd "V:\My Drive\Obsidian Vaults\Mick's Custom WaveLab Workflow\Metadata Pipeline"
python pipeline.py "path\to\artist_submission.json" --output-dir "path\to\project\folder"
```

This generates:
- `{ProjectTitle}_RIN.xml` — validated RIN 2.1 XML
- `{ProjectTitle}_CDText.csv` — CD-Text for WaveLab import
- `{ProjectTitle}_TrackInfo.txt` — CD Track Info 1-4 summary

### Step 3: Import CD-Text into WaveLab

1. Open your montage in WaveLab Pro 13
2. Open the CD-Text Editor (Stream Deck button or Functions > Edit CD-Text)
3. Click **Import**
4. Select the generated `{ProjectTitle}_CDText.csv`
5. CD-Text is populated for album + all tracks

### Step 4: Enter CD Track Info 1-4

Open the `{ProjectTitle}_TrackInfo.txt` file. For each track, enter:
- **Track Info 1** = BPM
- **Track Info 2** = Key
- **Track Info 3** = "Mastered by Mick Boggis" (or use `@riff_info_ieng@`)
- **Track Info 4** = Musician Credits

These are needed for CD/DDP delivery only. The rendered WAV files will have all values embedded by Python (Step 6).

### Step 5: Master and render

Master the album as normal. Render to `Artist-Title_DIGITAL_MASTER_V1`.
**Do NOT load MICK DEFAULT.dat.** Do NOT touch the Metadata tab. Just render clean audio.

### Step 6: Embed metadata into rendered WAVs

```bash
python pipeline.py "path\to\artist_submission.json" --render-dir "path\to\rendered\wavs" --output-dir "path\to\project\folder"
```

This embeds into each WAV file:
- **RIFF INFO**: IART, INAM, IPRD, IENG, IGNR, IWRI, ISFT, ICRD, ITRK
- **BEXT**: Description, Originator (Mick Boggis Studios), Originator Reference (DPID), Date/Time, Coding History
- **MD5**: Audio data checksum
- **aXML**: EBU Core XML with ISRC
- **ID3v2**: TIT2, TPE1, TALB, TBPM, TKEY, TLAN, TMCL, TSRC, TCOM, TCON, TCOP, COMM ("Mastered by Mick Boggis"), TRCK, TDRC, TOPE, TOLY, TIT1, TPE2

### Step 7: Deliver

- RIN XML + embedded WAV files to the artist/label
- CD/DDP if needed (CD-Text already in WaveLab)

## ID3v2 → WaveLab Field Mapping

| ID3v2 Frame | Content | WaveLab CD Track Info |
|---|---|---|
| TBPM | BPM | Info 1 |
| TKEY | Key | Info 2 |
| TLAN | Language | Info 3 |
| TMCL | Musician Credits | Info 4 |
| TSRC | ISRC | ISRC field |
| TIT2 | Track Title | CD-Text Title |
| TPE1 | Artist | CD-Text Performer |
| TALB | Album | CD-Text Album |
| TCOM | Songwriter | CD-Text Songwriter |
| COMM | "Mastered by Mick Boggis" | CD-Text Message |

## Form Hosting (Optional)

To host the form online for artists:
1. Create a GitHub repository
2. Upload `form.html`
3. Enable GitHub Pages
4. Share the URL with artists

Or simply email `form.html` as a file — it works offline in any browser.

*Stored in: Mick's Custom WaveLab Workflow/Metadata Pipeline/DOCUMENTATION.md*