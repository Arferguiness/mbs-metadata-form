/*
 * ═══════════════════════════════════════════════════════════════
 *  MICK BOGGIS STUDIOS — Metadata Form Receiver (Google Apps Script)
 * ═══════════════════════════════════════════════════════════════
 *
 *  Receives JSON submitted by form.html and, for every submission:
 *    1. Emails the full JSON to you as a .json attachment
 *    2. Saves the .json into a Google Drive folder
 *    3. Appends a summary row to a Google Sheet log
 *
 *  Everything runs on your own Google account — free, no limits that matter.
 *
 *  SETUP: see DEPLOY-HOSTING.md in this folder for click-by-click steps.
 * ═══════════════════════════════════════════════════════════════
 */

// ── CONFIG ──────────────────────────────────────────────────────
var NOTIFY_EMAIL = 'mickmastering@gmail.com';   // where submissions are emailed
var DRIVE_FOLDER_NAME = 'Mick Boggis Studios — Metadata Submissions'; // Drive folder (auto-created)
var LOG_SHEET_NAME = 'Metadata Submissions Log'; // Sheet (auto-created)
// ────────────────────────────────────────────────────────────────

function doPost(e) {
  try {
    var raw = (e && e.postData && e.postData.contents) ? e.postData.contents : '{}';
    var data = JSON.parse(raw);

    var project = data.project || {};
    var title = project.title || 'Untitled';
    var safeTitle = title.replace(/[^a-zA-Z0-9_-]/g, '_');
    var stamp = Utilities.formatDate(new Date(), 'GMT', 'yyyy-MM-dd_HH-mm-ss');
    var fileName = safeTitle + '_' + stamp + '.json';
    var pretty = JSON.stringify(data, null, 2);

    // 1) Save to Drive
    var folder = getOrCreateFolder_(DRIVE_FOLDER_NAME);
    var file = folder.createFile(fileName, pretty, MimeType.PLAIN_TEXT);

    // 2) Email with attachment
    var trackCount = (data.tracks || []).length;
    var contribCount = (data.contributors || []).length;
    var summary =
      'New metadata submission received.\n\n' +
      'Project:      ' + title + '\n' +
      'Type:         ' + (project.type || '—') + '\n' +
      'Catalogue #:  ' + (project.catalogue_number || '—') + '\n' +
      'Label:        ' + (project.label || '—') + '\n' +
      'Tracks:       ' + trackCount + '\n' +
      'Contributors: ' + contribCount + '\n' +
      'Received:     ' + new Date().toString() + '\n\n' +
      'Saved to Drive: ' + file.getUrl() + '\n\n' +
      'The full JSON is attached and ready for the pipeline.';

    MailApp.sendEmail({
      to: NOTIFY_EMAIL,
      subject: '🎚 Metadata Submission — ' + title + ' (' + trackCount + ' tracks)',
      body: summary,
      attachments: [{
        fileName: fileName,
        mimeType: 'application/json',
        content: pretty
      }]
    });

    // 3) Append to log sheet
    appendToLog_({
      received: new Date(),
      title: title,
      type: project.type || '',
      catalogue: project.catalogue_number || '',
      label: project.label || '',
      tracks: trackCount,
      contributors: contribCount,
      driveUrl: file.getUrl()
    });

    return json_({status: 'ok', file: fileName, url: file.getUrl()});
  } catch (err) {
    // Email the raw payload so nothing is ever lost, even on a parse error
    try {
      MailApp.sendEmail(NOTIFY_EMAIL,
        '⚠ Metadata Submission ERROR',
        'An error occurred: ' + err + '\n\nRaw payload:\n' +
        ((e && e.postData && e.postData.contents) || '(none)'));
    } catch (e2) {}
    return json_({status: 'error', message: String(err)});
  }
}

function doGet() {
  return json_({status: 'alive', service: 'Mick Boggis Studios Metadata Receiver'});
}

// ── Helpers ─────────────────────────────────────────────────────
function getOrCreateFolder_(name) {
  var it = DriveApp.getFoldersByName(name);
  return it.hasNext() ? it.next() : DriveApp.createFolder(name);
}

function appendToLog_(row) {
  var files = DriveApp.getFilesByName(LOG_SHEET_NAME);
  var ss;
  if (files.hasNext()) {
    ss = SpreadsheetApp.open(files.next());
  } else {
    ss = SpreadsheetApp.create(LOG_SHEET_NAME);
    ss.getActiveSheet().appendRow(
      ['Received', 'Project Title', 'Type', 'Catalogue #', 'Label', 'Tracks', 'Contributors', 'Drive Link']);
  }
  ss.getActiveSheet().appendRow(
    [row.received, row.title, row.type, row.catalogue, row.label, row.tracks, row.contributors, row.driveUrl]);
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
