# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2021-2022 Luiz Renato (ruizlenato@protonmail.com)

import html

import regex
from pyrogram import Client, filters
from pyrogram.types import Message

from smudge.locales.strings import tld


@Client.on_message(filters.regex(r"^s/(.+)?/(.+)?(/.+)?") & filters.reply)
async def sed(c: Client, m: Message):
    exp = regex.split(r"(?<![^\\]\\)/", m.text)
    pattern = exp[1]
    replace_with = exp[2].replace(r"\/", "/")
    flags = exp[3] if len(exp) > 3 else ""

    count = 1
    rflags = 0

    if "g" in flags:
        count = 0
    if "i" in flags and "s" in flags:
        rflags = regex.I | regex.S
    elif "i" in flags:
        rflags = regex.I
    elif "s" in flags:
        rflags = regex.S

    text = m.reply_to_message.text or m.reply_to_message.caption

    if not text:
        return

    try:
        res = regex.sub(
            pattern, replace_with, text, count=count, flags=rflags, timeout=1
        )
    except TimeoutError:
        await m.reply_text(await tld(m, "regex_timeout"))
    except regex.error as e:
        await m.reply_text(str(e))
    else:
        await c.send_message(
            m.chat.id,
            f"{html.escape(res)}",
            reply_to_message_id=m.reply_to_message.message_id,
        )
