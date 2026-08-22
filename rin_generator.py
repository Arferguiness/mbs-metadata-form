#!/usr/bin/env python
"""
DDEX RIN 2.1 XML Generator
============================
Reads a JSON metadata file and produces a valid DDEX Recording Information
Notification (RIN) 2.1 XML, validated against the official RIN + AVS XSD schemas
using lxml.

Usage:
    python rin_generator.py <input.json> [output.xml]

If no output path is given, the XML is written next to the input file with
an .rin.xml extension.

Mick Boggis's DDEX party details are always pre-filled:
    DPID:  PA-DPIDA-2026082102-O
    Name:  Mick Boggis
    ISNI:  0000 0005 1481 2832
    Role:  MasteringEngineer
    Address: Parc An Pons, TR17 0HQ, Marazion, UK
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone

from lxml import etree

# ── Constants ──────────────────────────────────────────────────────────────

RIN_NS = "http://ddex.net/xml/rin/21"
AVS_NS = "http://ddex.net/xml/allowed-value-sets"

XSD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "DDEX RIN 2.1",
    "RIN-3171 - RIN 2.1 (XSD)",
)
RIN_XSD = os.path.join(XSD_DIR, "recording-information-notification.xsd")
AVS_XSD = os.path.join(XSD_DIR, "allowed-value-sets.xsd")

# Mick's pre-filled party details
MICK_DPID = "PA-DPIDA-2026082102-O"
MICK_DPID_NODASH = "PADPIDA2026082102O"  # XSD pattern: PADPIDA[a-zA-Z0-9]+ (no hyphens)
MICK_FULL_NAME = "Mick Boggis"
MICK_ISNI = "0000005148128320"  # ISNI without spaces for the ISNI element
MICK_ISNI_DISPLAY = "0000 0005 1481 2832"
MICK_ROLE = "MasteringEngineer"
MICK_ADDRESS_LINES = ["Parc An Pons"]
MICK_CITY = "Marazion"
MICK_POSTCODE = "TR17 0HQ"
MICK_TERRITORY = "GB"
MICK_PARTY_REF = "P1"  # Always P1 for Mick


# ── Helpers ────────────────────────────────────────────────────────────────

def _sub(parent, tag, text=None, nsmap=None, **attrs):
    """Create a child element under *parent*.  Because elementFormDefault is
    'unqualified', local child elements live in NO namespace — only the root
    element carries the RIN namespace.  lxml handles this correctly when we
    create children with no namespace on a parent that is in the RIN ns."""
    el = etree.SubElement(parent, tag)
    if text is not None:
        el.text = str(text)
    for k, v in attrs.items():
        el.set(k, str(v))
    return el


def _duration_to_iso8601(duration_str):
    """Convert 'MM:SS' or 'HH:MM:SS' to ISO 8601 duration PT...H...M...S."""
    parts = duration_str.strip().split(":")
    if len(parts) == 2:
        m, s = parts
        h = "0"
    elif len(parts) == 3:
        h, m, s = parts
    else:
        return f"PT{duration_str}S"  # fallback
    h, m, s = int(h), int(m), int(float(s))
    result = "PT"
    if h > 0:
        result += f"{h}H"
    if m > 0 or h > 0:
        result += f"{m}M"
    # handle fractional seconds
    if "." in duration_str.split(":")[-1]:
        result += f"{s}S"
    else:
        result += f"{s}S"
    return result


# ── XML builders ───────────────────────────────────────────────────────────

def build_message_header(rin_root, data):
    """Build the MessageHeader element."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    msg_id = str(uuid.uuid4())
    thread_id = str(uuid.uuid4())

    hdr = _sub(rin_root, "MessageHeader")
    _sub(hdr, "MessageThreadId", thread_id)
    _sub(hdr, "MessageId", msg_id)
    _sub(hdr, "RinProcessor", "Mick Boggis RIN Generator")
    _sub(hdr, "RinProcessorVersionid", "1.0.0")

    # MessageSender — Mick's DPID
    sender = _sub(hdr, "MessageSender")
    _sub(sender, "PartyId", MICK_DPID_NODASH)
    _sub(sender, "PartyName")
    _sub(sender.find("PartyName"), "FullName", MICK_FULL_NAME)

    # MessageRecipient — same as sender (self-addressed for mastering studio)
    recip = _sub(hdr, "MessageRecipient")
    _sub(recip, "PartyId", MICK_DPID_NODASH)
    _sub(recip, "PartyName")
    _sub(recip.find("PartyName"), "FullName", MICK_FULL_NAME)

    _sub(hdr, "MessageCreatedDateTime", now)

    # MessageControlType — TestMessage by default; LiveMessage only when
    # explicitly requested via data["message_control_type"] == "LiveMessage"
    # (or the artist-form flag data["metadata"]["live"] == True).
    control = data.get("message_control_type")
    if not control:
        meta = data.get("metadata", {}) or {}
        control = "LiveMessage" if meta.get("live") is True else "TestMessage"
    if control not in ("TestMessage", "LiveMessage"):
        control = "TestMessage"
    _sub(hdr, "MessageControlType", control)


def build_party_list(rin_root, data):
    """Build the PartyList with Mick always first (P1), then contributors."""
    party_list = _sub(rin_root, "PartyList")

    # ── Mick Boggis (P1) ────────────────────────────────────────────────
    mick = _sub(party_list, "Party")
    pid = _sub(mick, "PartyId")
    # XSD order: ISNI, DPID, IpiNameNumber, IPN, CisacSocietyId, ProprietaryId
    _sub(pid, "ISNI", MICK_ISNI)
    _sub(pid, "DPID", MICK_DPID_NODASH)
    _sub(mick, "PartyReference", MICK_PARTY_REF)
    pname = _sub(mick, "PartyName")
    _sub(pname, "FullName", MICK_FULL_NAME)
    _sub(pname, "FullNameAsciiTranscribed", MICK_FULL_NAME)
    _sub(mick, "IsOrganization", "false")
    addr = _sub(mick, "PostalAddress", SequenceNumber="1")
    for line in MICK_ADDRESS_LINES:
        _sub(addr, "PostalAddressLine", line)
    _sub(addr, "CityName", MICK_CITY)
    _sub(addr, "PostCode", MICK_POSTCODE)
    _sub(addr, "TerritoryCode", MICK_TERRITORY)

    # ── Additional contributors ──────────────────────────────────────────
    seen_refs = {MICK_PARTY_REF}
    for contrib in data.get("contributors", []):
        ref = contrib.get("party_ref", "")
        if not ref or ref in seen_refs:
            continue
        seen_refs.add(ref)

        party = _sub(party_list, "Party")
        pid_el = _sub(party, "PartyId")
        isni = contrib.get("isni", "").replace(" ", "")
        if isni:
            _sub(pid_el, "ISNI", isni)
        ipn = contrib.get("ipn")
        if ipn:
            _sub(pid_el, "IPN", ipn)
        # No DPID for non-Mick contributors — they need a ProprietaryId or nothing
        # PartyId requires at least one child; add a ProprietaryId with the party_ref
        _sub(pid_el, "ProprietaryId", ref, Namespace="Local")

        _sub(party, "PartyReference", ref)
        pn = _sub(party, "PartyName")
        _sub(pn, "FullName", contrib["name"])
        _sub(party, "IsOrganization", "false")


def build_musical_work_list(rin_root, data):
    """Build the MusicalWorkList from writers data."""
    writers = data.get("writers", [])
    if not writers:
        return

    work_list = _sub(rin_root, "MusicalWorkList")

    # Group writers by work_ref
    works = {}
    for w in writers:
        ref = w.get("work_ref", "W1")
        works.setdefault(ref, []).append(w)

    for work_ref, work_writers in works.items():
        work = _sub(work_list, "MusicalWork")
        _sub(work, "MusicalWorkReference", work_ref)
        # Title — use the first writer's name or the work ref
        title_el = _sub(work, "Title")
        _sub(title_el, "TitleText", work_writers[0].get("name", f"Work {work_ref}"))

        # Add ISWC if any writer has one
        iswc = work_writers[0].get("iswc")
        if iswc:
            mw_id = _sub(work, "MusicalWorkId")
            _sub(mw_id, "ISWC", iswc)

        # Contributors (writers)
        for i, w in enumerate(work_writers, 1):
            contrib = _sub(work, "Contributor", SequenceNumber=str(i))
            _sub(contrib, "MusicalWorkContributorReference", w.get("party_ref", MICK_PARTY_REF))
            role = w.get("role", "Composer")
            _sub(contrib, "Role", role)
            share = w.get("share")
            if share is not None:
                _sub(contrib, "RightSharePercentage", str(share))


def build_resource_list(rin_root, data):
    """Build the ResourceList with SoundRecording per track.

    XSD element order for SoundRecording (lines 2011-2248 of the XSD):
      Type, DisplayArtistName, DisplayArtist, SupplementalArtist,
      SoundRecordingId, ResourceReference, Title, VersionType,
      SoundRecordingDescriptorTag, RightsController, LanguageOfPerformance,
      SequenceNumber, KeySignature, TimeSignature, Tempo, Duration,
      PLine, ParentalWarningType, Genre, Status, Comment,
      SoundRecordingMusicalWorkReference, Contributor,
      SoundRecordingFileReference, SoundRecordingProjectReference,
      SoundRecordingSessionReference, SoundRecordingRecordingComponentReference,
      [SampledSoundRecording | ContainsSamples], CreationDate, IsMedley,
      AudioChannelConfiguration, TerritoryOfFixation, MasteredDate,
      FirstPublicationDate
    """
    tracks = data.get("tracks", [])
    if not tracks:
        return

    resource_list = _sub(rin_root, "ResourceList")
    tech = data.get("technical", {})

    for track in tracks:
        sr = _sub(resource_list, "SoundRecording")

        # DisplayArtistName (required, maxOccurs unbounded)
        artist_ref = track.get("display_artist_ref", MICK_PARTY_REF)
        artist_name = MICK_FULL_NAME
        for c in data.get("contributors", []):
            if c.get("party_ref") == artist_ref:
                artist_name = c.get("name", artist_name)
                break
        _sub(sr, "DisplayArtistName", artist_name, IsDefault="true")

        # DisplayArtist (optional, unbounded)
        da = _sub(sr, "DisplayArtist")
        _sub(da, "PartyReference", artist_ref)
        _sub(da, "ArtisticRole", MICK_ROLE)

        # SoundRecordingId with ISRC
        sr_id = _sub(sr, "SoundRecordingId")
        _sub(sr_id, "ISRC", track["isrc"])

        # ResourceReference (required)
        _sub(sr, "ResourceReference", track.get("resource_ref", "A1"))

        # Title (optional, unbounded)
        title_el = _sub(sr, "Title")
        _sub(title_el, "TitleText", track["title"])

        # LanguageOfPerformance (optional, unbounded) — before SequenceNumber
        lang = track.get("language", "en")
        _sub(sr, "LanguageOfPerformance", lang)

        # SequenceNumber (optional)
        ref_str = track.get("resource_ref", "A1")
        seq_str = ref_str[1:] if len(ref_str) > 1 and ref_str[1:].isdigit() else "1"
        _sub(sr, "SequenceNumber", seq_str)

        # KeySignature (optional)
        key = track.get("key")
        if key:
            _sub(sr, "KeySignature", key)

        # TimeSignature (optional) — not in our JSON schema, skip

        # Tempo (optional)
        bpm = track.get("bpm")
        if bpm:
            _sub(sr, "Tempo", str(bpm))

        # Duration (optional) — ISO 8601
        dur = track.get("duration")
        if dur:
            _sub(sr, "Duration", _duration_to_iso8601(dur))

        # PLine (optional)
        rights = data.get("rights", [])
        if rights:
            r = rights[0]
            p_line = _sub(sr, "PLine")
            year = r.get("p_line_year")
            if year:
                _sub(p_line, "Year", str(year))
            _sub(p_line, "PLineCompany", r.get("controller", ""))
            _sub(p_line, "PLineText", r.get("p_line", ""))

        # ParentalWarningType (optional)
        pw = track.get("parental_warning", "NotExplicit")
        _sub(sr, "ParentalWarningType", pw)

        # Genre (optional, unbounded)
        genre = track.get("genre")
        if genre:
            genre_el = _sub(sr, "Genre")
            _sub(genre_el, "GenreText", genre)
            subgenre = track.get("subgenre")
            if subgenre:
                _sub(genre_el, "SubGenre", subgenre)

        # SoundRecordingMusicalWorkReference (required, unbounded)
        for wref in track.get("writer_refs", ["W1"]):
            _sub(sr, "SoundRecordingMusicalWorkReference", wref)

        # Contributors — Mick as MasteringEngineer on each track
        contrib = _sub(sr, "Contributor", SequenceNumber="1")
        _sub(contrib, "ContributorPartyReference", MICK_PARTY_REF)
        _sub(contrib, "Role", MICK_ROLE)

        # Add other contributors from the data
        for i, c in enumerate(data.get("contributors", []), 2):
            if c.get("party_ref") == MICK_PARTY_REF:
                continue  # Already added as MasteringEngineer
            c_contrib = _sub(sr, "Contributor", SequenceNumber=str(i))
            _sub(c_contrib, "ContributorPartyReference", c["party_ref"])
            # Map role to valid AVS ResourceContributorRole values
            role = c.get("role", "Performer")
            _sub(c_contrib, "Role", role)
            instrument = c.get("instrument")
            if instrument:
                # Map common instrument names to valid AVS InstrumentType values
                INSTRUMENT_MAP = {
                    "Vocals": "Voice",
                    "Vocalist": "LeadVocalist",
                    "Electric Guitar": "ElectricGuitar",
                    "Acoustic Guitar": "AcousticGuitar",
                    "Bass": "Bass",
                    "Bass Guitar": "ElectricBassGuitar",
                    "Electric Bass": "ElectricBassGuitar",
                    "Drums": "DrumKit",
                    "Piano": "Piano",
                    "Keyboard": "Keyboard",
                    "Keyboards": "Keyboard",
                    "Synthesizer": "Synthesizer",
                    "Organ": "Organ",
                    "Violin": "Violin",
                    "Viola": "Viola",
                    "Cello": "Cello",
                    "Double Bass": "DoubleBass",
                    "Flute": "Flute",
                    "Saxophone": "Saxophone",
                    "Trumpet": "Trumpet",
                    "Trombone": "Trombone",
                    "Clarinet": "Clarinet",
                    "Percussion": "PercussionInstrument",
                    "Turntables": "Turntable",
                    "Programmer": "Synthesizer",
                }
                mapped = INSTRUMENT_MAP.get(instrument, instrument)
                if mapped == instrument and " " in instrument:
                    # Not found in map and has spaces — use UserDefined
                    _sub(c_contrib, "InstrumentType", "UserDefined",
                         UserDefinedValue=instrument)
                else:
                    _sub(c_contrib, "InstrumentType", mapped)

        # SoundRecordingProjectReference (optional, unbounded)
        project = data.get("project", {})
        if project:
            _sub(sr, "SoundRecordingProjectReference", project.get("reference", "J1"))

        # SoundRecordingSessionReference (optional, unbounded)
        for s in data.get("sessions", []):
            _sub(sr, "SoundRecordingSessionReference", s.get("ref", "O1"))

        # ContainsSamples = false (choice: SampledSoundRecording | ContainsSamples)
        _sub(sr, "ContainsSamples", "false")

        # AudioChannelConfiguration (optional)
        channels = tech.get("channels", "Stereo")
        _sub(sr, "AudioChannelConfiguration", channels)

        # TerritoryOfFixation (optional)
        sessions = data.get("sessions", [])
        for s in sessions:
            country = s.get("country")
            if country:
                _sub(sr, "TerritoryOfFixation", country)
                break

        # MasteredDate (optional)
        for s in sessions:
            if s.get("type") in ("MasteringSession", "Mastering"):
                _sub(sr, "MasteredDate", s.get("date", ""))
                break


def build_recording_component_list(rin_root, data):
    """Build the RecordingComponentList linking SoundRecordings to sessions."""
    tracks = data.get("tracks", [])
    if not tracks:
        return

    rc_list = _sub(rin_root, "RecordingComponentList")

    for i, track in enumerate(tracks, 1):
        rc = _sub(rc_list, "RecordingComponent")
        _sub(rc, "RecordingComponentReference", f"K{i}")
        _sub(rc, "SequenceNumber", str(i))
        _sub(rc, "Title", track["title"])
        _sub(rc, "DisplayArtistName", track.get("display_artist", "Mick Boggis"), IsDefault="true")

        # Contributor — Mick as MasteringEngineer
        contrib = _sub(rc, "Contributor", SequenceNumber="1")
        _sub(contrib, "RecordingComponentContributorReference", MICK_PARTY_REF)
        _sub(contrib, "Role", MICK_ROLE)


def build_project_list(rin_root, data):
    """Build the ProjectList."""
    project = data.get("project")
    if not project:
        return

    proj_list = _sub(rin_root, "ProjectList")
    proj = _sub(proj_list, "Project")

    # ProjectId with catalogue number and UPC
    proj_id = _sub(proj, "ProjectId")
    cat = project.get("catalogue_number")
    if cat:
        _sub(proj_id, "ProprietaryId", cat, Namespace="CatalogueNumber")
    upc = project.get("upc")
    if upc:
        _sub(proj_id, "ProprietaryId", upc, Namespace="UPC")

    _sub(proj, "ProjectReference", project.get("reference", "J1"))
    _sub(proj, "ProjectName", project.get("title", ""))

    # Genre at project level
    tracks = data.get("tracks", [])
    if tracks and tracks[0].get("genre"):
        genre_el = _sub(proj, "Genre")
        _sub(genre_el, "GenreText", tracks[0]["genre"])

    # Contributor — Mick as MasteringEngineer
    contrib = _sub(proj, "Contributor", SequenceNumber="1")
    _sub(contrib, "ProjectContributorReference", MICK_PARTY_REF)
    _sub(contrib, "Role", MICK_ROLE)

    # Add other contributors
    for i, c in enumerate(data.get("contributors", []), 2):
        if c.get("party_ref") == MICK_PARTY_REF:
            continue
        c_contrib = _sub(proj, "Contributor", SequenceNumber=str(i))
        _sub(c_contrib, "ProjectContributorReference", c["party_ref"])
        _sub(c_contrib, "Role", c.get("role", "Performer"))


def build_session_list(rin_root, data):
    """Build the SessionList."""
    sessions = data.get("sessions", [])
    if not sessions:
        return

    session_list = _sub(rin_root, "SessionList")

    for s in sessions:
        sess = _sub(session_list, "Session")
        _sub(sess, "SessionReference", s.get("ref", "O1"))
        SESSION_TYPE_MAP = {
            "RecordingSession": "Recording",
            "MixingSession": "Mixing",
            "MasteringSession": "Mastering",
            "OverdubSession": "Overdub",
            "EditingSession": "Editing",
            "RehearsalSession": "PreProduction",
            "ProgrammingSession": "Production",
        }
        session_type = SESSION_TYPE_MAP.get(s.get("type", "Mastering"), s.get("type", "Mastering"))
        _sub(sess, "SessionType", session_type)

        date = s.get("date")
        if date:
            # Convert to ISO 8601 datetime
            _sub(sess, "StartDateTime", f"{date}T00:00:00Z")

        # Venue
        venue = _sub(sess, "Venue")
        _sub(venue, "VenueName", s.get("venue", "Mick Boggis Studios"))
        _sub(venue, "VenueAddress", s.get("city", "Marazion"))
        _sub(venue, "TerritoryCode", s.get("country", "GB"))
        room = s.get("room")
        if room:
            _sub(venue, "VenueRoom", room)

        # Technical details
        tech = data.get("technical", {})
        bit_depth = tech.get("bit_depth")
        if bit_depth:
            _sub(sess, "BitDepth", str(bit_depth))
        sample_rate = tech.get("sample_rate")
        if sample_rate:
            # XSD expects kHz, so divide by 1000
            _sub(sess, "SamplingRate", str(float(sample_rate) / 1000))

        # Contributors — Mick as MasteringEngineer
        contrib = _sub(sess, "Contributor", SequenceNumber="1")
        _sub(contrib, "SessionContributorReference", MICK_PARTY_REF)
        _sub(contrib, "Role", MICK_ROLE)

        # Project reference
        project = data.get("project", {})
        if project:
            _sub(sess, "SessionProjectReference", project.get("reference", "J1"))

        # SoundRecording references
        for track in data.get("tracks", []):
            _sub(sess, "SessionSoundRecordingReference", track.get("resource_ref", "A1"))

        # RecordingComponent references
        for i, track in enumerate(data.get("tracks", []), 1):
            _sub(sess, "SessionRecordingComponentReference", f"K{i}")


# ── Validation ──────────────────────────────────────────────────────────────

def validate_xml(xml_tree, xsd_path):
    """Validate the XML tree against the RIN XSD (which imports AVS).

    Returns (is_valid, list_of_error_strings).
    """
    errors = []

    # We need to handle the xmldsig import — the XSD imports from a URL that
    # may not be fetchable offline.  We'll try direct loading first; if the
    # xmldsig schema can't be fetched, we'll use a more lenient approach.
    try:
        schema_doc = etree.parse(xsd_path)
        schema = etree.XMLSchema(schema_doc)
        is_valid = schema.validate(xml_tree)
        if not is_valid:
            for err in schema.error_log:
                errors.append(f"Line {err.line}: {err.message}")
        return is_valid, errors
    except etree.XMLSchemaParseError as e:
        # The XSD imports xmldsig from a URL that may fail offline.
        # Fall back to a namespace-aware validation without the import.
        errors.append(f"XSD parse error: {e}")
        # Try again with a custom resolver that provides a minimal xmldsig schema
        return _validate_with_local_xmldsig(xml_tree, xsd_path, errors)


def _validate_with_local_xmldsig(xml_tree, xsd_path, errors_so_far):
    """Validate using a local minimal xmldsig schema so the import resolves."""
    minimal_ds = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
           targetNamespace="http://www.w3.org/2000/09/xmldsig#"
           elementFormDefault="qualified">
  <xs:complexType name="SignedInfoType">
    <xs:sequence>
      <xs:any namespace="##any" processContents="lax" minOccurs="0" maxOccurs="unbounded"/>
    </xs:sequence>
    <xs:attribute name="Id" type="xs:ID"/>
  </xs:complexType>
  <xs:complexType name="SignatureValueType">
    <xs:simpleContent>
      <xs:extension base="xs:base64Binary">
        <xs:attribute name="Id" type="xs:ID"/>
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>
  <xs:complexType name="X509IssuerSerialType">
    <xs:sequence>
      <xs:element name="X509IssuerName" type="xs:string"/>
      <xs:element name="X509SerialNumber" type="xs:integer"/>
    </xs:sequence>
  </xs:complexType>
</xs:schema>
"""
    import tempfile

    # Write the minimal xmldsig schema to a temp file
    ds_dir = os.path.join(os.path.dirname(xsd_path), "_xmldsig_local")
    os.makedirs(ds_dir, exist_ok=True)
    ds_file = os.path.join(ds_dir, "xmldsig-core-schema.xsd")
    with open(ds_file, "w", encoding="utf-8") as f:
        f.write(minimal_ds)

    # Re-parse the RIN XSD — it references the xmldsig via schemaLocation
    # which points to a URL. We need to redirect that. Let's create a
    # modified copy of the RIN XSD with the local path.
    with open(xsd_path, "r", encoding="utf-8") as f:
        xsd_text = f.read()

    # Replace the xmldsig schemaLocation URL with our local file
    xsd_text_modified = xsd_text.replace(
        "http://www.w3.org/TR/2002/REC-xmldsig-core-20020212/xmldsig-core-schema.xsd",
        os.path.basename(ds_file),
    )

    # Write modified XSD to temp
    modified_xsd = os.path.join(os.path.dirname(xsd_path), "_rin_modified.xsd")
    with open(modified_xsd, "w", encoding="utf-8") as f:
        f.write(xsd_text_modified)

    try:
        schema_doc = etree.parse(modified_xsd)
        schema = etree.XMLSchema(schema_doc)
        is_valid = schema.validate(xml_tree)
        if not is_valid:
            errors = []
            for err in schema.error_log:
                errors.append(f"Line {err.line}: {err.message}")
            return is_valid, errors
        return True, []
    except Exception as e:
        errors_so_far.append(f"Fallback validation error: {e}")
        return False, errors_so_far
    finally:
        # Clean up temp files
        for tmp in [modified_xsd, ds_file]:
            try:
                os.remove(tmp)
            except OSError:
                pass
        try:
            os.rmdir(ds_dir)
        except OSError:
            pass


# ── Main generation ─────────────────────────────────────────────────────────

def generate_rin(data):
    """Generate the RIN XML etree from the data dict.

    The RIN XSD uses elementFormDefault="unqualified", which means only the
    root element (RecordingInformationNotification) is in the RIN namespace;
    all child elements are in NO namespace (unqualified).

    We achieve this by using a prefixed namespace (rin:) on the root element
    and creating all children with no namespace. lxml correctly serializes
    this: the root gets xmlns:rin="..." and children have no prefix.
    """
    nsmap = {"rin": RIN_NS}
    rin_root = etree.Element(
        "{%s}RecordingInformationNotification" % RIN_NS,
        nsmap=nsmap,
    )
    rin_root.set("SchemaVersionId", "2.1")
    rin_root.set("AvsVersionId", "4")
    rin_root.set("LanguageAndScriptCode", "en")

    build_message_header(rin_root, data)
    build_party_list(rin_root, data)
    build_musical_work_list(rin_root, data)
    build_resource_list(rin_root, data)
    build_recording_component_list(rin_root, data)
    build_project_list(rin_root, data)
    build_session_list(rin_root, data)

    return etree.ElementTree(rin_root)


def main():
    # --live flag flips the message to LiveMessage; default is TestMessage
    args = list(sys.argv[1:])
    live = False
    if "--live" in args:
        live = True
        args.remove("--live")

    if len(args) < 1:
        print("Usage: python rin_generator.py <input.json> [output.xml] [--live]")
        print("  Default MessageControlType is TestMessage; pass --live for LiveMessage.")
        sys.exit(1)

    input_path = args[0]
    if len(args) >= 2:
        output_path = args[1]
    else:
        base, _ = os.path.splitext(input_path)
        output_path = base + ".rin.xml"

    # Read JSON
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # CLI --live overrides; otherwise generator defaults to TestMessage
    if live:
        data["message_control_type"] = "LiveMessage"

    control = data.get("message_control_type") or (
        "LiveMessage" if (data.get("metadata", {}) or {}).get("live") is True else "TestMessage")
    print(f"Generating RIN 2.1 XML from: {input_path}")
    print(f"MessageControlType: {control}")

    # Generate XML
    tree = generate_rin(data)

    # Pretty-print and write
    xml_str = etree.tostring(
        tree,
        pretty_print=True,
        xml_declaration=True,
        encoding="UTF-8",
    )
    with open(output_path, "wb") as f:
        f.write(xml_str)
    print(f"XML written to: {output_path}")

    # Validate
    print("\n" + "=" * 60)
    print("VALIDATION REPORT")
    print("=" * 60)

    if not os.path.exists(RIN_XSD):
        print(f"WARNING: RIN XSD not found at {RIN_XSD}")
        print("XML generated but not validated.")
        sys.exit(0)

    # Re-parse the generated XML for validation
    xml_tree = etree.parse(output_path)

    is_valid, errors = validate_xml(xml_tree, RIN_XSD)

    if is_valid:
        print("✓ XML is VALID against RIN 2.1 XSD schemas")
        print(f"  Schema: {RIN_XSD}")
        print(f"  AVS:    {AVS_XSD}")
    else:
        print("✗ XML FAILED validation:")
        for err in errors:
            print(f"  - {err}")

    print("=" * 60)
    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())