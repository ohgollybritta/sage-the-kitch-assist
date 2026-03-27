import os

with open(os.path.expanduser('~/.sage_credentials')) as f:
    for line in f:
        key, val = line.strip().split('=', 1)
        os.environ[key] = val

import spotipy
from spotipy.oauth2 import SpotifyOAuth

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.environ['SPOTIPY_CLIENT_ID'],
    client_secret=os.environ['SPOTIPY_CLIENT_SECRET'],
    redirect_uri='http://localhost:8888/callback',
    scope='user-modify-playback-state user-read-playback-state'
))

print(sp.me()['display_name'])
