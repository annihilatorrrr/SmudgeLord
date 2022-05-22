# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2021-2022 Luiz Renato (ruizlenato@protonmail.com)

import spotipy
import orjson

from spotipy.client import SpotifyException

from smudge.database.music import set_spot_user, get_spot_user, unreg_spot
from smudge.config import SPOTIFY_BASIC
from smudge.utils import http


async def gen_spotify_token(user_id, token):
    r = await http.post(
        "https://accounts.spotify.com/api/token",
        headers=dict(Authorization=f"Basic {SPOTIFY_BASIC}"),
        data=dict(
            grant_type="authorization_code",
            code=token,
            redirect_uri="https://ruizlenato.github.io/Smudge/go",
        ),
    )
    b = orjson.loads(r.content)
    if b.get("error"):
        return False, b["error"]
    else: 
        await set_spot_user(user_id, b["access_token"], b["refresh_token"])
        return True, b["access_token"]


async def get_spoti_session(user_id):
    try:
        new_token = await refresh_token(user_id)
    except SpotifyException:
        await unreg_spot(user_id)
        return False
    a = spotipy.Spotify(auth=new_token)
    return a


async def refresh_token(user_id):
    usr = await get_spot_user(user_id)
    r = await http.post(
        "https://accounts.spotify.com/api/token",
        headers=dict(Authorization=f"Basic {SPOTIFY_BASIC}"),
        data=dict(grant_type="refresh_token", refresh_token=usr),
    )
    b = orjson.loads(r.content)
    await set_spot_user(user_id, b["access_token"], usr)
    return b["access_token"]
