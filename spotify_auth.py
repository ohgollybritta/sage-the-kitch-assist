import os

with open(os.path.expanduser('~/.sage_credentials')) as f:
    for line in f:
        if '=' in line:
            key, val = line.strip().split('=', 1)
            os.environ[key] = val

import spotipy
from spotipy.oauth2 import SpotifyOAuth

auth_manager = SpotifyOAuth(
    client_id=os.environ['SPOTIPY_CLIENT_ID'],
    client_secret=os.environ['SPOTIPY_CLIENT_SECRET'],
    redirect_uri='http://127.0.0.1:8888/callback',
    scope='user-modify-playback-state user-read-playback-state',
    cache_path=os.path.expanduser('~/spotipy.cache'),
    open_browser=False
)

# Print the auth URL for the user to open manually
auth_url = auth_manager.get_authorize_url()
print(f"\nOpen this URL in your browser:\n\n{auth_url}\n")
print("After logging in, you'll be redirected to a URL that won't load.")
print("Copy the ENTIRE URL from your browser's address bar and paste it here:\n")

response_url = input("Paste URL here: ").strip()
code = auth_manager.parse_response_code(response_url)
auth_manager.get_access_token(code)

sp = spotipy.Spotify(auth_manager=auth_manager)
user = sp.me()
print(f"\nConnected as: {user['display_name']}")
print("Token cached at ~/spotipy.cache — Sage is ready to use Spotify.")
