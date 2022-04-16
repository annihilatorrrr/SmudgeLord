from pyrogram.types import Message
from pyrogram import Client, filters
from pyrogram.errors import BadRequest, Forbidden

from smudge.plugins import tld


@Client.on_message(filters.command("cleanup", prefixes="/"))
async def cleanup(c: Client, m: Message):
    if m.chat.type == "private":
        return await m.reply_text(await tld(m, "Admin.err_private"))
    else:
        bot = await c.get_chat_member(chat_id=m.chat.id, user_id=(await c.get_me()).id)
        member = await c.get_chat_member(chat_id=m.chat.id, user_id=m.from_user.id)
        if member.status in ["administrator", "creator"]:
            if bot.status in ["administrator"]:
                pass
            else:
                return await m.reply_text(await tld(m, "Admin.botnotadmin"))
        else:
            return await m.reply_text(await tld(m, "Admin.noadmin"))
    deleted_users = []
    sent = await m.reply_text(await tld(m, "Admin.cleanup_start"))
    async for a in c.iter_chat_members(chat_id=m.chat.id, filter="all"):
        if a.user.is_deleted:
            try:
                await c.ban_chat_member(m.chat.id, a.user.id)
                deleted_users.append(a)
                await sent.edit_text(await tld(m, "Admin.cleanup_start_d")).format(
                    {len(deleted_users)}
                )
            except BadRequest:
                pass
            except Forbidden as e:
                return await m.reply_text(f"<b>Erro:</b> {e}")
        else:
            await sent.edit_text(await tld(m, "Admin.cleanup_no_deleted"))
