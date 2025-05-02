#!/usr/bin/env python3
# merge_markdown_from_drive.py

from pathlib import Path
import sys, time
from tqdm import tqdm
from googleapiclient.errors import HttpError
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# ───────────────────────────────────────── configuration ──
SCOPES          = ['https://www.googleapis.com/auth/drive.readonly']

#  << paste the exact “folders/…ID” from the Drive URL >>
ROOT_FOLDER_ID  = '1zw6DvvQCkoNCHgArEQLRhFjpCcuEbDPz'

OUTPUT_DIR      = Path('merged_markdown')
SEPARATOR       = '\n\n---\n'          # visual break between articles

MAX_RETRIES     = 3                    # for transient download errors
TRANSIENT_CODES = {500, 502, 503, 504}
# ──────────────────────────────────────────────────────────


def auth_drive() -> GoogleDrive:
    """Authorise (cached) and return a GoogleDrive instance."""
    base = Path(__file__).resolve().parent
    gauth = GoogleAuth()

    # absolute path so it’s found regardless of working dir
    gauth.settings['client_config_file'] = str(base / 'client_secrets.json')
    gauth.settings['get_refresh_token']  = True
    gauth.settings['oauth_scope']        = SCOPES

    cred_file = base / 'credentials.json'
    if cred_file.exists():
        gauth.LoadCredentialsFile(str(cred_file))

    if not gauth.credentials or gauth.access_token_expired:
        gauth.LocalWebserverAuth()
        gauth.SaveCredentialsFile(str(cred_file))

    return GoogleDrive(gauth)


def glist(drive: GoogleDrive, query: str):
    """List files/folders with the always‑needed shared‑drive flags."""
    return drive.ListFile({
        'q': query,
        'supportsAllDrives': True,
        'includeItemsFromAllDrives': True
    }).GetList()


def recurse_md_files(drive: GoogleDrive, folder_id: str):
    """Yield (title,id) for every .md file below folder_id (all depths)."""
    for item in glist(drive, f"'{folder_id}' in parents and trashed=false"):
        if item['mimeType'] == 'application/vnd.google-apps.folder':
            yield from recurse_md_files(drive, item['id'])
        elif item['title'].lower().endswith('.md'):
            yield item['title'], item['id']


def safe_download_md(drive: GoogleDrive, fid: str):
    """Download file text with retry/back‑off for 5xx errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return drive.CreateFile({'id': fid}).GetContentString(encoding='utf-8')
        except HttpError as e:
            if getattr(e.resp, 'status', None) in TRANSIENT_CODES:
                wait = 2 ** attempt
                print(f"   transient {e.resp.status} on {fid} — retry {attempt}/{MAX_RETRIES} in {wait}s")
                time.sleep(wait)
                continue
            raise
        except Exception:
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            raise
    return None


def merge_folder(drive: GoogleDrive, folder):
    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"{folder['title']}.md"

    items = list(recurse_md_files(drive, folder['id']))
    if not items:
        print(f"⚠️  {folder['title']} is empty ‑ skipped")
        return

    with out_path.open('w', encoding='utf-8') as fout:
        for title, fid in tqdm(items, desc=f"Bundling {folder['title']}", unit='file'):
            text = safe_download_md(drive, fid)
            if text is None:
                print(f"   ⚠️ skipped {title} (id {fid}) after {MAX_RETRIES} failures")
                continue
            fout.write(f"{SEPARATOR}# {title}\n\n{text}")

    print(f"✅  {folder['title']}  →  {out_path}")


def main():
    drive = auth_drive()

    # If the folder lives only in “Shared with me”, add a shortcut to My Drive
    top_folders = glist(
        drive,
        f"'{ROOT_FOLDER_ID}' in parents "
        f"and mimeType='application/vnd.google-apps.folder' "
        f"and trashed=false"
    )

    if not top_folders:
        sys.exit("No sub‑folders found – is ROOT_FOLDER_ID correct & visible to the Drive API?")

    for folder in top_folders:
        merge_folder(drive, folder)


if __name__ == '__main__':
    main()
