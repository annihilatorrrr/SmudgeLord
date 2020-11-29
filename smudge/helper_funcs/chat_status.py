from functools import wraps

from telegram import User, Chat, ChatMember, Update, Bot

from smudge import DEL_CMDS, SUDO_USERS, WHITELIST_USERS
import smudge.modules.sql.admin_sql as admin_sql
from smudge.modules.translations.strings import tld


def can_delete(chat: Chat, bot_id: int) -> bool:
    return chat.get_member(bot_id).can_delete_messages


def is_user_ban_protected(chat: Chat,
                          user_id: int,
                          member: ChatMember = None) -> bool:
    if chat.type == 'private' \
            or user_id in SUDO_USERS \
            or user_id in WHITELIST_USERS \
            or chat.all_members_are_administrators:
        return True

    if not member:
        member = chat.get_member(user_id)
    return member.status in ('administrator', 'creator')


def is_user_admin(chat: Chat, user_id: int, member: ChatMember = None) -> bool:
    if chat.type == 'private' \
            or user_id in SUDO_USERS \
            or user_id == int(777000) \
            or chat.all_members_are_administrators:
        return True

    if not member:
        member = chat.get_member(user_id)
    return member.status in ('administrator', 'creator')


def is_bot_admin(chat: Chat,
                 bot_id: int,
                 bot_member: ChatMember = None) -> bool:
    if chat.type == 'private' \
            or chat.all_members_are_administrators:
        return True

    if not bot_member:
        bot_member = chat.get_member(bot_id)
    return bot_member.status in ('administrator', 'creator')


def is_user_in_chat(chat: Chat, user_id: int) -> bool:
    member = chat.get_member(user_id)
    return member.status not in ('left', 'kicked')


def bot_can_delete(func):
    @wraps(func)
    def delete_rights(bot: Bot, update: Update, *args, **kwargs):
        chat = update.effective_chat

        if can_delete(update.effective_chat, bot.id):
            return func(bot, update, *args, **kwargs)
        update.effective_message.reply_text(
            tld(chat.id, 'helpers_bot_cant_delete'))

    return delete_rights


def can_pin(func):
    @wraps(func)
    def pin_rights(bot: Bot, update: Update, *args, **kwargs):
        chat = update.effective_chat

        if update.effective_chat.get_member(bot.id).can_pin_messages:
            return func(bot, update, *args, **kwargs)
        update.effective_message.reply_text(
            tld(chat.id, 'helpers_bot_cant_pin'))

    return pin_rights


def can_promote(func):
    @wraps(func)
    def promote_rights(bot: Bot, update: Update, *args, **kwargs):
        chat = update.effective_chat

        if update.effective_chat.get_member(bot.id).can_promote_members:
            return func(bot, update, *args, **kwargs)
        update.effective_message.reply_text(
            tld(chat.id, 'helpers_bot_cant_pro_demote'))

    return promote_rights


def can_restrict(func):
    @wraps(func)
    def promote_rights(bot: Bot, update: Update, *args, **kwargs):
        chat = update.effective_chat

        if update.effective_chat.get_member(bot.id).can_restrict_members:
            return func(bot, update, *args, **kwargs)
        update.effective_message.reply_text(
            tld(chat.id, 'helpers_bot_cant_restrict'))

    return promote_rights


def bot_admin(func):
    @wraps(func)
    def is_admin(bot: Bot, update: Update, *args, **kwargs):
        chat = update.effective_chat

        if is_bot_admin(update.effective_chat, bot.id):
            return func(bot, update, *args, **kwargs)
        update.effective_message.reply_text(
            tld(chat.id, 'helpers_bot_not_admin'))

    return is_admin


def user_admin(func):
    @wraps(func)
    def is_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user
        chat = update.effective_chat
        if user and is_user_admin(update.effective_chat, user.id):
            try:
                return func(bot, update, *args, **kwargs)
            except Exception:
                return

        elif not user:
            pass

        elif DEL_CMDS and " " not in update.effective_message.text:
            update.effective_message.delete()

        elif (admin_sql.command_reaction(chat.id) is True):
            update.effective_message.reply_text(
                tld(chat.id, 'helpers_user_not_admin'))

    return is_admin


def user_admin_no_reply(func):
    @wraps(func)
    def is_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user
        if user and is_user_admin(update.effective_chat, user.id):
            return func(bot, update, *args, **kwargs)

        if not user:
            pass

        elif DEL_CMDS and " " not in update.effective_message.text:
            update.effective_message.delete()

    return is_admin


def user_not_admin(func):
    @wraps(func)
    def is_not_admin(bot: Bot, update: Update, *args, **kwargs):
        user = update.effective_user
        if user and not is_user_admin(update.effective_chat, user.id):
            return func(bot, update, *args, **kwargs)

    return is_not_admin

# This module has been ported from SkyleeBot


def user_can_promote(chat: Chat, user: User, bot_id: int) -> bool:
    return chat.get_member(user.id).can_promote_members and (int(user.id) in SUDO_USERS)


def user_can_ban(chat: Chat, user: User, bot_id: int) -> bool:
    return chat.get_member(user.id).can_restrict_members and (int(user.id) in SUDO_USERS)


def user_can_pin(chat: Chat, user: User, bot_id: int) -> bool:
    return chat.get_member(user.id).can_pin_messages and (int(user.id) in SUDO_USERS)


def user_can_changeinfo(chat: Chat, user: User, bot_id: int) -> bool:
    return chat.get_member(user.id).can_change_info and (int(user.id) in SUDO_USERS)


def user_can_restrict_members(chat: Chat, user: User, bot_id: int) -> bool:
    return chat.get_member(user.id).can_restrict_members and (int(user.id) in SUDO_USERS)