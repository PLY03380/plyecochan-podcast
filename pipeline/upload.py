"""upload.py — Upload vidéo sur YouTube (Data API v3) avec métadonnées pipeline."""
import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

log = logging.getLogger("upload")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
           "https://www.googleapis.com/auth/youtube.force-ssl"]
TOKEN_FILE = Path.home() / ".youtube_token.pickle"
CLIENT_SECRETS = Path(__file__).resolve().parent.parent / "config" / "client_secrets.json"

YT_CATEGORY_ID = "25"  # News & Politics
YT_PRIVACY = "public"  # "private" pour test, "public" pour publier


def get_authenticated_service():
    """Authentifie via OAuth 2.0. Ouvre un navigateur si nécessaire."""
    import pickle
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CLIENT_SECRETS.exists():
                raise FileNotFoundError(
                    f"Client secrets non trouvé: {CLIENT_SECRETS}\n"
                    "Créez un projet Google Cloud, activez YouTube Data API v3, "
                    "téléchargez client_secrets.json dans config/"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)


def _build_metadata(script: dict, lang: str, video_path: Path) -> dict:
    """Construit les métadonnées YouTube à partir du script pipeline."""
    lang_data = script.get(lang, {})
    titre = lang_data.get("titre", f"Video {lang}")

    # Description : utiliser le SEO si disponible, sinon les blocs
    seo = script.get("seo", {}).get(lang, {})
    description = seo.get("description", "")
    if not description:
        blocs = lang_data.get("blocs", {})
        ordre = {"fr": ["accroche", "fait", "pourquoi", "impact", "conclusion"],
                 "en": ["hook", "fact", "why", "impact", "conclusion"],
                 "es": ["gancho", "hecho", "por_que", "impacto", "conclusion"]}[lang]
        description = "\n\n".join(blocs.get(b, "") for b in ordre if blocs.get(b))

    # Tags
    tags = seo.get("tags", [])
    if not tags:
        tags = ["economie", "shorts", lang]

    # Thumbnail text (pour référence, pas uploadé automatiquement)
    pkg = script.get("package", {}).get(lang, {})
    thumb_text = pkg.get("thumbnail_text", "")

    return {
        "title": titre[:100],
        "description": description[:5000],
        "tags": tags[:15],
        "categoryId": YT_CATEGORY_ID,
        "privacyStatus": YT_PRIVACY,
        "thumb_text": thumb_text,
    }


def upload_video(youtube, video_path: Path, metadata: dict, playlist_title: str = None) -> str:
    """Upload une vidéo sur YouTube. Retourne le video_id."""
    from googleapiclient.http import MediaFileUpload

    body = {
        "snippet": {
            "title": metadata["title"],
            "description": metadata["description"],
            "tags": metadata["tags"],
            "categoryId": metadata["categoryId"],
            "defaultLanguage": lang_code(metadata.get("lang", "fr")),
            "defaultAudioLanguage": lang_code(metadata.get("lang", "fr")),
        },
        "status": {
            "privacyStatus": metadata["privacyStatus"],
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    log.info(f"Upload {video_path.name}...")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            log.info(f"  Progression: {int(status.progress() * 100)}%")

    video_id = response["id"]
    log.info(f"Video uploaded: https://youtu.be/{video_id}")

    if playlist_title:
        _add_to_playlist(youtube, video_id, playlist_title)

    return video_id


def _add_to_playlist(youtube, video_id: str, playlist_title: str):
    """Ajoute une vidéo à une playlist (la crée si nécessaire)."""
    playlists = youtube.playlists().list(part="snippet", mine=True, maxResults=50).execute()
    playlist_id = None
    for pl in playlists.get("items", []):
        if pl["snippet"]["title"] == playlist_title:
            playlist_id = pl["id"]
            break

    if not playlist_id:
        log.info(f"Creating playlist: {playlist_title}")
        pl_body = {"snippet": {"title": playlist_title}, "status": {"privacyStatus": "public"}}
        pl_response = youtube.playlists().insert(part="snippet,status", body=pl_body).execute()
        playlist_id = pl_response["id"]

    youtube.playlistItems().insert(
        part="snippet",
        body={"snippet": {"playlistId": playlist_id, "resourceId": {"kind": "youtube#video", "videoId": video_id}}},
    ).execute()
    log.info(f"Added to playlist: {playlist_title}")


def lang_code(lang: str) -> str:
    """Convertit le code langue interne en code YouTube."""
    return {"fr": "fr", "en": "en", "es": "es"}.get(lang, "en")


def upload_all(videos: dict, script: dict, playlist_map: dict = None) -> dict:
    """Upload toutes les vidéos d'un run. Retourne {lang: video_id}."""
    if playlist_map is None:
        playlist_map = {"fr": "Actualités économiques FR",
                        "en": "Economic News EN",
                        "es": "Noticias Económicas ES"}

    youtube = get_authenticated_service()
    results = {}
    for lang, video_path in videos.items():
        if not video_path or not Path(video_path).exists():
            log.warning(f"Video manquante pour {lang}: {video_path}")
            continue
        try:
            metadata = _build_metadata(script, lang, Path(video_path))
            metadata["lang"] = lang
            playlist = playlist_map.get(lang)
            video_id = upload_video(youtube, Path(video_path), metadata, playlist)
            results[lang] = video_id
        except Exception as e:
            log.error(f"Upload {lang} échoué: {e}")
            results[lang] = None
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    import sys
    if len(sys.argv) < 3:
        print("Usage: python upload.py <video_path> <script_json_path> [lang]")
        sys.exit(1)
    video_path = Path(sys.argv[1])
    script = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    lang = sys.argv[3] if len(sys.argv) > 3 else "fr"
    youtube = get_authenticated_service()
    metadata = _build_metadata(script, lang, video_path)
    metadata["lang"] = lang
    vid = upload_video(youtube, video_path, metadata, None)
    print(f"Uploaded: https://youtu.be/{vid}")