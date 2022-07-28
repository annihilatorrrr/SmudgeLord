# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2021-2022 Luiz Renato (ruizlenato@protonmail.com)
import html
import orjson

from typing import Union
from gpytranslate import Translator

from smudge.utils import http
from smudge.utils.locales import tld
from smudge.utils.misc import get_tr_lang, cssworker_url, dicio_def

from pyrogram.helpers import ikb
from pyrogram.enums import ParseMode
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery

tr = Translator()


@Client.on_message(filters.command(["tr", "tl"]))
async def translate(c: Client, m: Message):
    text = m.text[4:]
    lang = get_tr_lang(text)

    text = text.replace(lang, "", 1).strip() if text.startswith(lang) else text

    if not text and m.reply_to_message:
        text = m.reply_to_message.text or m.reply_to_message.caption

    if not text:
        return await m.reply_text(await tld(m, "Misc.noargs_tr"))
    sent = await m.reply_text(await tld(m, "Misc.tr_translating"))
    langs = {}

    if len(lang.split("-")) > 1:
        langs["sourcelang"] = lang.split("-")[0]
        langs["targetlang"] = lang.split("-")[1]
    else:
        to_lang = langs["targetlang"] = lang

    trres = await tr.translate(text, **langs)
    text = trres.text

    res = html.escape(text)
    await sent.edit_text(
        ("<b>{from_lang}</b> -> <b>{to_lang}:</b>\n<code>{translation}</code>").format(
            from_lang=trres.lang, to_lang=to_lang, translation=res
        )
    )


@Client.on_message(filters.command("dicio"))
async def dicio(c: Client, m: Message):
    txt = m.text.split(" ", 1)[1]
    if a := await dicio_def(txt):
        frase = f'<b>{a[0]["title"]}:</b>\n{a[0]["tit"]}\n\n<i>{a[0]["desc"]}</i>'
    else:
        frase = "sem resultado"
    await m.reply(frase)


@Client.on_message(filters.command(["print", "ss"]))
async def prints(c: Client, m: Message):
    msg = m.text
    the_url = msg.split(" ", 1)
    wrong = False

    if len(the_url) == 1:
        wrong = True
    else:
        the_url = the_url[1]

    if wrong:
        await m.reply_text(await tld(m, "Misc.noargs_print"))
        return

    try:
        sent = await m.reply_text(await tld(m, "Misc.print_printing"))
        res_json = await cssworker_url(target_url=the_url)
    except BaseException as e:
        await m.reply(f"<b>Error:</b> <code>{e}</code>")
        return

    if res_json:
        if image_url := res_json["url"]:
            try:
                await m.reply_photo(image_url)
                await sent.delete()
            except BaseException as e:
                await m.reply(f"<b>Error:</b> <code>{e}</code>")
                return
        else:
            await m.reply(
                "couldn't get url value, most probably API is not accessible."
            )
    else:
        await m.reply(await tld(m, "Misc.print_api_dead"))


@Client.on_message(filters.command("cep"))
async def cep(c: Client, m: Message):
    try:
        if len(m.command) > 1:
            cep = m.text.split(None, 1)[1]
        elif m.reply_to_message and m.reply_to_message.text:
            cep = m.reply_to_message.text
    except IndexError:
        await m.reply_text(await tld(m, "Misc.noargs_cep"))
        return

    base_url = "https://brasilapi.com.br/api/cep/v1"
    res = await http.get(f"{base_url}/{cep}")
    db = orjson.loads(res.content)
    try:
        city = db["city"]
        state = db["state"]
    except KeyError:
        return await m.reply_text((await tld(m, "Misc.cep_error")))
    state_name = orjson.loads(
        (await http.get(f"https://brasilapi.com.br/api/ibge/uf/v1/{state}")).content
    )["nome"]
    neighborhood = db["neighborhood"]
    street = db["street"]

    if res.status_code == 404:
        return await m.reply_text((await tld(m, "Misc.cep_error")))
    else:
        rep = (await tld(m, "Misc.cep_strings")).format(
            cep, city, state_name, state, neighborhood, street
        )
        await m.reply_text(rep)


@Client.on_message(filters.command("ddd"))
@Client.on_callback_query(filters.regex("ddd_(?P<num>.+)"))
async def ddd(c: Client, m: Union[Message, CallbackQuery]):
    try:
        if isinstance(m, CallbackQuery):
            ddd = m.matches[0]["num"]
        else:
            ddd = m.text.split(maxsplit=1)[1]
    except IndexError:
        await m.reply_text(await tld(m, "Misc.noargs_ddd"))
        return
    res = await http.get(f"https://brasilapi.com.br/api/ddd/v1/{ddd}")
    db = orjson.loads(res.content)
    try:
        state = db["state"]
    except KeyError:
        return await m.reply_text((await tld(m, "Misc.ddd_error")))
    if res.status_code == 404:
        return await m.reply_text((await tld(m, "Misc.ddd_error")))
    state_name = orjson.loads(
        (await http.get(f"https://brasilapi.com.br/api/ibge/uf/v1/{state}")).content
    )["nome"]
    cities = db["cities"]
    if isinstance(m, CallbackQuery):
        cities.reverse()
        cities = (
            str(cities)
            .replace("'", "")
            .replace("]", "")
            .replace("[", "")
            .lower()
            .title()
        )
        await m.edit_message_text(
            (await tld(m, "Misc.fddd_strings")).format(ddd, state_name, state, cities)
        )
    else:
        rep = (await tld(m, "Misc.ddd_strings")).format(ddd, state_name, state)
        keyboard = [[(await tld(m, "Misc.ddd_cities"), f"ddd_{ddd}")]]
        await m.reply_text(rep, reply_markup=ikb(keyboard))


@Client.on_message(filters.command(["gitr", "ghr"]))
async def git_on_message(c: Client, m: Message):
    if len(m.command) != 2:
        await m.reply_text(await tld(m, "Misc.noargs_gitr"))
        return
    repo = m.command[1]
    page = await http.get(f"https://api.github.com/repos/{repo}/releases/latest")
    if page.status_code != 200:
        return await m.reply_text((await tld(m, "Misc.gitr_noreleases")).format(repo))
    else:
        await git(c, m, repo, page)


async def git(c: Client, m: Message, repo, page):
    db = orjson.loads(page.content)
    date = db["published_at"]
    message = (
        f"<b>Name:</b> <i>{db['name']}</i>\n"
        + f"<b>Tag:</b> <i>{db['tag_name']}</i>\n"
        + f"<b>Released on:</b> <i>{date[: date.rfind('T')]}</i>\n"
        + f"<b>By:</b> <i>{repo.split('/')[0]}@github.com</i>\n"
    )
    keyboard = []
    for i in range(len(db)):
        try:
            file_name = db["assets"][i]["name"]
            url = db["assets"][i]["browser_download_url"]
            dls = db["assets"][i]["download_count"]
            size_bytes = db["assets"][i]["size"]
            size = float("{:.2f}".format((size_bytes / 1024) / 1024))
            text = "{}\n💾 {}MB | 📥 {}".format(file_name, size, dls)
            keyboard += [[(text, url, "url")]]

        except IndexError:
            continue
    await m.reply_text(message, reply_markup=ikb(keyboard))

__help__ = "Misc"