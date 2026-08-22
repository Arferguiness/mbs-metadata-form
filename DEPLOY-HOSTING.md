# Hosting the Form + Auto-Receiving Submissions

This sets up the Mick Boggis Studios Master Metadata Form so it lives online and
**every submission is emailed to you, saved to Google Drive, and logged in a Sheet
— automatically, the instant an artist hits Submit.**

Two one-time jobs:
- **Part A** — deploy the Google Apps Script receiver (the bit that emails you)
- **Part B** — host `form.html` online so artists can reach it

Total time: ~20 minutes. Cost: **£0**.

---

## PART A — Deploy the Google Apps Script Receiver

### A1. Create the script
1. Go to **https://script.google.com** (sign in as **mickmastering@gmail.com**)
2. Click **New project** (top left)
3. Delete the placeholder `function myFunction() {}`
4. Open `google-apps-script.gs` from this folder, copy **all** of it, paste it in
5. Click the **💾 Save** icon. Name the project e.g. `Metadata Receiver`

### A2. Deploy it as a Web App
1. Top right → **Deploy** → **New deployment**
2. Click the ⚙ gear next to "Select type" → choose **Web app**
3. Set:
   - **Description:** `Metadata form receiver`
   - **Execute as:** **Me (mickmastering@gmail.com)**
   - **Who has access:** **Anyone**  ← important, so artists can post without logging in
4. Click **Deploy**

### A3. Authorize (one time)
1. Google shows "Authorization required" → click **Authorize access**
2. Choose your **mickmastering@gmail.com** account
3. You'll see "Google hasn't verified this app" (normal — it's your own script):
   click **Advanced** → **Go to Metadata Receiver (unsafe)** → **Allow**
4. Copy the **Web app URL** it gives you. It looks like:
   `https://script.google.com/macros/s/AKfy..../exec`
   **Keep this URL** — you need it in Part A4.

### A4. Wire the URL into the form
Tell me the URL and I'll paste it in for you, **or** do it yourself:
1. Open `form.html` in a text editor
2. Find this line (near the bottom, in the submit function):
   ```js
   const ENDPOINT = 'PASTE_YOUR_APPS_SCRIPT_URL_HERE';
   ```
3. Replace the placeholder with your Web app URL:
   ```js
   const ENDPOINT = 'https://script.google.com/macros/s/AKfy..../exec';
   ```
4. Save.

### A5. Test it
1. Open the Web app URL in a browser — you should see
   `{"status":"alive","service":"Mick Boggis Studios Metadata Receiver"}`
2. Open `form.html`, fill in a project title + a track, click **Generate / Submit**
3. Within a few seconds you should get an email at mickmastering@gmail.com with the
   JSON attached, a new file in the Drive folder, and a row in the log Sheet.

**What you get on every submission:**
- 📧 Email with the full JSON attached + a readable summary
- 📁 A `.json` file in Drive folder **"Mick Boggis Studios — Metadata Submissions"**
- 📊 A row in the **"Metadata Submissions Log"** Sheet (project, tracks, link, etc.)

The saved/emailed JSON is exactly what `pipeline.py` consumes — drop it straight in.

---

## PART B — Host form.html Online (pick one)

### Option 1 — GitHub Pages (recommended: free, custom-friendly)
1. Create a free account at **https://github.com** if you don't have one
2. New repository → name it e.g. `mbs-metadata-form` → **Public** → Create
3. **Add file → Upload files** → drag in `form.html`
4. Rename it to `index.html` (so the URL is clean), commit
5. Repo **Settings → Pages** → Source: **Deploy from a branch** → Branch: **main** / **/(root)** → Save
6. Wait ~1 minute. Your form is live at:
   https://github.com/Arferguiness/mbs-metadata-form.git
7. Send that link to artists.

### Option 2 — Netlify Drop (fastest: drag-and-drop, no account needed to start)
1. Go to **https://app.netlify.com/drop**
2. Drag `form.html` (renamed to `index.html`) onto the page
3. You instantly get a live URL like `https://random-name.netlify.app`
4. (Optional) sign up free to rename it to `mbs-metadata.netlify.app`

### Option 3 — Google Sites (all-Google, simplest to manage)
1. **https://sites.google.com** → blank site
2. Insert → **Embed** → **Embed code** → paste the contents of `form.html`
   *(Note: Google Sites sandboxes embeds; if the form misbehaves, use Option 1 or 2 —
   GitHub Pages serves the raw file and always works.)*

---

## Updating the form later
When I change `form.html`, just re-upload it to wherever you hosted it
(replace the file on GitHub / re-drag on Netlify). The Apps Script URL never changes,
so submissions keep flowing.

## Turning off / changing where it emails
Edit `NOTIFY_EMAIL` at the top of the Apps Script, then **Deploy → Manage deployments
→ Edit → Version: New version → Deploy**. (You must redeploy a new version for script
edits to take effect.)

---

*Stored in: Mick's Custom WaveLab Workflow/Metadata Pipeline/DEPLOY-HOSTING.md*
