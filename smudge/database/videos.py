# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2021-2022 Luiz Renato (ruizlenato@proton.me)
from typing import Optional

from .core import database

conn = database.get_conn()


async def sdl_c(id: int) -> bool:
    cursor = await conn.execute("SELECT sdl_auto FROM groups WHERE id = ?", (id,))
    row = await cursor.fetchone()
    await cursor.close()
    return row[0]


async def isdl_c(id: int) -> bool:
    cursor = await conn.execute("SELECT sdl_images FROM groups WHERE id = ?", (id,))
    row = await cursor.fetchone()
    await cursor.close()
    return row[0]


async def sdl_t(id: int, mode: Optional[bool]) -> None:
    await conn.execute("UPDATE groups SET sdl_auto = ? WHERE id = ?", (mode, id))
    await conn.commit()


async def isdl_t(id: int, mode: Optional[bool]) -> None:
    await conn.execute("UPDATE groups SET sdl_images = ? WHERE id = ?", (mode, id))
    await conn.commit()
