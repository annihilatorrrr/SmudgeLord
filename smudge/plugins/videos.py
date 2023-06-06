# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2021-2022 Luiz Renato (ruizlenato@proton.me)

import io
import os
import re
import shutil
import datetime
import tempfile
import contextlib

from yt_dlp import YoutubeDL

from pyrogram import filters
from pyrogram.helpers import ikb
from pyrogram.enums import ChatAction, ChatType
from pyrogram.errors import BadRequest, UserNotParticipant
from pyrogram.raw.types import InputMessageID
from pyrogram.raw.functions import channels, messages
from pyrogram.types import CallbackQuery, Message, InputMediaPhoto, InputMediaVideo

from ..utils.videos import DownloadMedia, search_yt, extract_info
from ..utils import http, pretty_size
from ..database.videos import sdl_c
from ..locales import tld

from ..bot import Smudge

# Regex to get link
REGEX_LINKS = r"http(?:s)?:\/\/(?:www.|mobile.|m.|vm.)?(?:instagram|twitter|reddit|tiktok|facebook).com\/(?:\S*)"

# Regex to get the video ID from the URL
YOUTUBE_REGEX = re.compile(
    r"(?m)http(?:s?):\/\/(?:www\.)?(?:music\.)?youtu(?:be\.com\/(watch\?v=|shorts/|embed/)|\.be\/|)([\w\-\_]*)(&(amp;)?‌​[\w\?‌​=]*)?"
)

# Twitter regex
TWITTER_LINKS = (
    r"(http(s)?:\/\/(?:www\.)?(?:v\.)?(?:mobile.)?(?:twitter.com)\/(?:.*?))(?:\s|$)"
)


@Smudge.on_message(filters.command("yt"))
async def yt_search_cmd(c: Smudge, m: Message):
    if m.reply_to_message and m.reply_to_message.text:
        args = m.reply_to_message.text
    elif len(m.command) > 1:
        args = m.text.split(None, 1)[1]
    else:
        await m.reply_text(await tld(m, "Misc.noargs_yt"))
        return
    vids = [
        f'{num + 1}: <a href="{i["url"]}">{i["title"]}</a>'
        for num, i in enumerate(await search_yt(args))
    ]

    await m.reply_text(
        "\n".join(vids) if vids else r"¯\_(ツ)_/¯", disable_web_page_preview=True
    )


@Smudge.on_message(filters.command("ytdl"))
async def ytdlcmd(c: Smudge, m: Message):
    user = m.from_user.id

    if m.reply_to_message and m.reply_to_message.text:
        url = m.reply_to_message.text
    elif len(m.command) > 1:
        url = m.text.split(None, 1)[1]
    else:
        await m.reply_text(await tld(m, "Misc.noargs_ytdl"))
        return

    ydl = YoutubeDL({"noplaylist": True})
    if rege := YOUTUBE_REGEX.match(url):
        yt = await extract_info(ydl, rege.group(), download=False)

    else:
        yt = await extract_info(ydl, f"ytsearch:{url}", download=False)
        try:
            yt = yt["entries"][0]
        except IndexError:
            return
    for f in yt["formats"]:
        if f["format_id"] == "140":
            afsize = f["filesize"] or 0
        if f["ext"] == "mp4" and f["filesize"] is not None:
            vfsize = f["filesize"] or 0
            vformat = f["format_id"]

    keyboard = [
        [
            (
                await tld(m, "Misc.ytdl_audio_button"),
                f'_aud.{yt["id"]}|{afsize}|{vformat}|{user}|{m.id}',
            ),
            (
                await tld(m, "Misc.ytdl_video_button"),
                f'_vid.{yt["id"]}|{vfsize}|{vformat}|{user}|{m.id}',
            ),
        ]
    ]

    if " - " in yt["title"]:
        performer, title = yt["title"].rsplit(" - ", 1)
    else:
        performer = yt.get("creator") or yt.get("uploader")
        title = yt["title"]

    text = f"🎧 <b>{performer}</b> - <i>{title}</i>\n"
    text += f"💾 <code>{pretty_size(afsize)}</code> (audio) / <code>{pretty_size(int(vfsize))}</code> (video)\n"
    text += f"⏳ <code>{datetime.timedelta(seconds=yt.get('duration'))}</code>"

    await m.reply_text(text, reply_markup=ikb(keyboard))


@Smudge.on_callback_query(filters.regex("^(_(vid|aud))"))
async def cli_ytdl(c: Smudge, cq: CallbackQuery):
    try:
        data, fsize, vformat, userid, mid = cq.data.split("|")
    except ValueError:
        return print(cq.data)
    if cq.from_user.id != int(userid):
        return await cq.answer(await tld(cq, "Misc.ytdl_button_denied"), cache_time=60)
    if int(fsize) > 2147483648:
        return await cq.answer(
            await tld(cq, "Misc.ytdl_file_too_big"),
            show_alert=True,
            cache_time=60,
        )
    vid = re.sub(r"^\_(vid|aud)\.", "", data)
    url = f"https://www.youtube.com/watch?v={vid}"
    await cq.message.edit(await tld(cq, "Main.downloading"))

    with tempfile.TemporaryDirectory() as tempdir:
        path = os.path.join(tempdir, "ytdl")

    if "vid" in data:
        ydl = YoutubeDL(
            {
                "outtmpl": f"{path}/%(title)s-%(id)s.%(ext)s",
                "format": f"{vformat}+140",
                "max_filesize": 500000000,
                "noplaylist": True,
            }
        )

    else:
        ydl = YoutubeDL(
            {
                "outtmpl": f"{path}/%(title)s-%(id)s.%(ext)s",
                "format": "bestaudio[ext=m4a]",
                "max_filesize": 500000000,
                "noplaylist": True,
            }
        )

    try:
        yt = await extract_info(ydl, url, download=True)
    except BaseException as e:
        await c.send_logs(cq, e)
        await cq.message.edit((await tld(cq, "Misc.ytdl_send_error")).format(e))
        return
    await cq.message.edit(await tld(cq, "Main.sending"))
    await c.send_chat_action(cq.message.chat.id, ChatAction.UPLOAD_VIDEO)

    filename = ydl.prepare_filename(yt)
    thumb = io.BytesIO((await http.get(yt["thumbnail"])).content)
    thumb.name = "thumbnail.png"
    caption = f"<a href='{yt['webpage_url']}'>{yt['title']}</a></b>"
    if "vid" in data:
        try:
            await c.send_video(
                cq.message.chat.id,
                video=filename,
                width=1920,
                height=1080,
                caption=caption,
                duration=yt["duration"],
                thumb=thumb,
                reply_to_message_id=int(mid),
            )
            await cq.message.delete()
        except BadRequest as e:
            await c.send_logs(cq, e)
            await c.send_message(
                chat_id=cq.message.chat.id,
                text=(await tld(cq, "Misc.ytdl_send_error")).format(errmsg=e),
                reply_to_message_id=int(mid),
            )
    else:
        if " - " in yt["title"]:
            performer, title = yt["title"].rsplit(" - ", 1)
        else:
            performer = yt.get("creator") or yt.get("uploader")
            title = yt["title"]
        try:
            await c.send_audio(
                cq.message.chat.id,
                audio=filename,
                title=title,
                performer=performer,
                caption=caption,
                duration=yt["duration"],
                thumb=thumb,
                reply_to_message_id=int(mid),
            )
        except BadRequest as e:
            await cq.message.edit_text(
                await tld(cq, "ytdl_send_error").format(errmsg=e)
            )
        else:
            await cq.message.delete()

    shutil.rmtree(tempdir, ignore_errors=True)


@Smudge.on_message(filters.command(["dl", "sdl"]) | filters.regex(REGEX_LINKS), group=1)
async def sdl(c: Smudge, m: Message):
    if m.matches:
        if m.chat.type is ChatType.PRIVATE or await sdl_c("sdl_auto", m.chat.id):
            url = m.matches[0].group(0)
        else:
            return
    elif len(m.command) > 1:
        url = m.text.split(None, 1)[1]
    elif m.reply_to_message and m.reply_to_message.text:
        url = m.reply_to_message.text
    else:
        return await m.reply_text(await tld(m, "Misc.noargs_sdl"))

    if not re.match(REGEX_LINKS, url, re.M):
        return await m.reply_text(await tld(m, "Misc.sdl_invalid_link"))

    if re.match(TWITTER_LINKS, url, re.M) and m.chat.type is not ChatType.PRIVATE:
        with contextlib.suppress(UserNotParticipant):
            # To avoid conflict with @TwitterGramRobot
            return await m.chat.get_member(1703426201)

    path = f"{m.chat.id}.{m.id}"
    if m.chat.type == ChatType.PRIVATE:
        method = messages.GetMessages(id=[InputMessageID(id=(m.id))])
    else:
        method = channels.GetMessages(
            channel=await c.resolve_peer(m.chat.id), id=[InputMessageID(id=(m.id))]
        )
    rawM = (await c.invoke(method)).messages[0].media
    files, caption = await DownloadMedia().download(url, path)

    medias = []
    for media in files:
        if media["p"][-3:] == "mp4" and len(files) == 1:
            await c.send_chat_action(m.chat.id, ChatAction.UPLOAD_VIDEO)
            await m.reply_video(
                video=media["p"],
                width=media["w"],
                height=media["h"],
                caption=caption,
            )
            return shutil.rmtree(f"./downloads/{path}/", ignore_errors=True)

        if media["p"][-3:] == "mp4":
            if medias:
                medias.append(
                    InputMediaVideo(media["p"], width=media["w"], height=media["h"])
                )
            else:
                medias.append(
                    InputMediaVideo(
                        media["p"],
                        width=media["w"],
                        height=media["h"],
                        caption=caption,
                    )
                )
        elif not medias:
            medias.append(InputMediaPhoto(media["p"], caption=caption))
        else:
            medias.append(InputMediaPhoto(media["p"]))

    if medias:
        if (
            rawM
            and not re.search(r"instagram.com/", url)
            and len(medias) == 1
            and "InputMediaPhoto" in str(medias[0])
        ):
            return

        await c.send_chat_action(m.chat.id, ChatAction.UPLOAD_DOCUMENT)
        await m.reply_media_group(media=medias)
    return shutil.rmtree(f"./downloads/{path}/", ignore_errors=True)
