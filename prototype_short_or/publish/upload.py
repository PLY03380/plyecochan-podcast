#!/usr/bin/env python3
"""
upload.py — Upload vidéo sur YouTube (YouTube Data API v3)
Usage: python upload.py --video video/short_fr.mp4 --metadata metadata_FR.md --playlist "Actualités économiques FR"
"""

import argparse
import os
import pickle
import re
from pathlib import Path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = Path.home() / ".youtube_token.pickle"
CLIENT_SECRETS = Path(__file__).parent.parent / "config" / "client_secrets.json"

# ─── Parse metadata markdown ────────────────────────────────────
def parse_metadata(md_path: Path) -> dict:
    content = md_path.read_text(encoding="utf-8")
    data = {}

    # Titre
    m = re.search(r"## Titre\s*\n\*\*(.+?)\*\*", content)
    data["title"] = m.group(1).strip() if m else "Sans titre"

    # Description (tout entre "## Description" et "## Sources" ou "## Tags")
    m = re.search(r"## Description\s*\n(.*?)(?:\n## |\Z)", content, re.DOTALL)
    data["description"] = m.group(1).strip() if m else ""

    # Tags
    m = re.search(r"## Tags\s*\n(.+?)(?:\n## |\Z)", content, re.DOTALL)
    if m:
        tags = [t.strip() for t in m.group(1).split(",") if t.strip()]
        data["tags"] = tags[:500]  # YouTube max 500 chars total
    else:
        data["tags"] = []

    # Playlist (depuis "## Playlist")
    m = re.search(r"## Playlist\s*\n\*\*(.+?)\*\*", content)
    data["playlist"] = m.group(1).strip() if m else ""

    return data

# ─── Auth ───────────────────────────────────────────────────────
def get_authenticated_service():
    creds = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRETS.exists():
                raise FileNotFoundError(f"Client secrets non trouvé: {CLIENT_SECRETS}\nCréez un projet Google Cloud, activez YouTube Data API v3, téléchargez client_secrets.json dans config/")
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)

# ─── Upload ─────────────────────────────────────────────────────
def upload_video(youtube, video_path: Path, metadata: dict, playlist_title: str = None):
    body = {
        "snippet": {
            "title": metadata["title"][:100],  # max 100 chars
            "description": metadata["description"][:5000],
            "tags": metadata["tags"],
            "categoryId": "25",  # News & Politics
            "defaultLanguage": "fr",
            "defaultAudioLanguage": "fr",
        },
        "status": {
            "privacyStatus": "private",  # "private" pour test, "public" pour publier
            "selfDeclaredMadeForKids": False,
        }
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    print(f"⬆️ Uploading {video_path.name}...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Progression: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"✅ Video uploaded: https://youtu.be/{video_id}")

    # Ajouter à la playlist si fournie
    if playlist_title:
        add_to_playlist(youtube, video_id, playlist_title)

    return video_id

def add_to_playlist(youtube, video_id: str, playlist_title: str):
    # Chercher playlist existante
    playlists = youtube.playlists().list(part="snippet", mine=True, maxResults=50).execute()
    playlist_id = None
    for pl in playlists.get("items", []):
        if pl["snippet"]["title"] == playlist_title:
            playlist_id = pl["id"]
            break

    if not playlist_id:
        # Créer playlist
        print(f"📝 Creating playlist: {playlist_title}")
        pl_body = {"snippet": {"title": playlist_title}, "status": {"privacyStatus": "public"}}
        pl_response = youtube.playlists().insert(part="snippet,status", body=pl_body).execute()
        playlist_id = pl_response["id"]

    # Ajouter vidéo
    youtube.playlistItems().insert(
        part="snippet",
        body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}
    ).execute()
    print(f"✅ Added to playlist: {playlist_title}")

# ─── Main ───────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Upload video to YouTube")
    parser.add_argument("--video", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--playlist", help="Playlist title (overrides metadata)")
    args = parser.parse_args()

    metadata = parse_metadata(args.metadata)
    playlist = args.playlist or metadata.get("playlist")

    youtube = get_authenticated_service()
    upload_video(youtube, args.video, metadata, playlist)

if __name__ == "__main__":
    main()