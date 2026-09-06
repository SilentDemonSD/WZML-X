from time import time

from pyrogram.errors import (
    ChannelPrivate,
    ChatAdminRequired,
    ChatSendMediaForbidden,
    ChatWriteForbidden,
    PeerIdInvalid,
    UserBannedInChannel,
)

from .... import LOGGER
from ...ext_utils.filter_utils import file_name_of, size_of
from ...telegram_helper.tg_copy import (
    CopyAborted,
    CopyRestricted,
    TgCopier,
    message_link,
)

MAX_CLONE_MESSAGES = 500
MAX_FLOOD_WAIT = 600
RESTRICTED_STREAK = 3

DEST_FATAL = (
    ChatWriteForbidden,
    ChatSendMediaForbidden,
    ChannelPrivate,
    PeerIdInvalid,
    ChatAdminRequired,
    UserBannedInChannel,
)


def restricted_runs(ids, cap=3):
    if not ids:
        return [], 0
    ordered = sorted(set(ids))
    runs = [[ordered[0], ordered[0]]]
    for one in ordered[1:]:
        if one == runs[-1][1] + 1:
            runs[-1][1] = one
        else:
            runs.append([one, one])
    return [(lo, hi) for lo, hi in runs[:cap]], len(runs)


async def build_units(client, chat_id, messages):
    units = []
    for message in messages:
        group = getattr(message, "media_group_id", None)
        if group and units and getattr(units[-1][-1], "media_group_id", None) == group:
            units[-1].append(message)
        else:
            units.append([message])
    if not messages:
        return units
    first_id = messages[0].id
    last_id = messages[-1].id
    checked = []
    for unit in units:
        if len(unit) > 1 and (unit[0].id == first_id or unit[-1].id == last_id):
            try:
                whole = await client.get_media_group(chat_id, unit[0].id)
            except Exception as err:
                LOGGER.debug(f"media group check failed for {unit[0].id}: {err}")
                whole = unit
            if len(whole) != len(unit):
                checked.extend([[one] for one in unit])
                continue
        checked.append(unit)
    return checked


class TelegramClone:
    def __init__(self, listener, client, units, dests, forward=False):
        self.listener = listener
        self._client = client
        self._units = units
        self._dests = list(dests)
        self._copier = TgCopier(
            client,
            cancel=lambda: self.listener.is_cancelled,
            max_wait=MAX_FLOOD_WAIT,
            forward=forward,
        )
        self._start = time()
        self.copied = 0
        self.processed_bytes = 0
        self.restricted = []
        self.failed = []
        self.dead_dests = []
        self.first_link = ""

    @property
    def total_units(self):
        return len(self._units)

    @property
    def live_dests(self):
        return len(self._dests)

    @staticmethod
    def _label(unit):
        if len(unit) > 1:
            return f"album of {len(unit)}"
        return file_name_of(unit[0]) or f"message {unit[0].id}"

    @staticmethod
    def _bytes(unit):
        return sum(size_of(one) for one in unit)

    def _protected(self, unit):
        return any(getattr(one, "has_protected_content", False) for one in unit)

    def _kill_dest(self, seat, reason):
        chat_id, _thread = seat
        self._dests.remove(seat)
        self.dead_dests.append((chat_id, reason))
        LOGGER.warning(f"clone destination dropped {chat_id}: {reason}")

    async def _fan_out(self, unit):
        landed = 0
        for seat in list(self._dests):
            if self.listener.is_cancelled:
                return False
            try:
                sent = await self._copier.send(seat[0], unit, seat[1])
            except CopyRestricted:
                self.restricted.extend(one.id for one in unit)
                return False
            except CopyAborted:
                raise
            except DEST_FATAL as err:
                self._kill_dest(seat, type(err).__name__)
                continue
            except Exception as err:
                self.failed.append((unit[0].id, str(err)))
                LOGGER.error(f"clone failed at {unit[0].id}: {err}")
                return False
            landed += 1
            if not self.first_link:
                self.first_link = message_link(sent)
        return landed > 0

    async def relay(self):
        streak = 0
        self.listener.files_to_proceed = self._units
        for done, unit in enumerate(self._units):
            if self.listener.is_cancelled or not self._dests:
                break
            self.listener.proceed_count = done
            self.listener.subname = self._label(unit)
            self.listener.subsize = self._bytes(unit)
            if self._protected(unit):
                self.restricted.extend(one.id for one in unit)
                streak += 1
                if streak >= RESTRICTED_STREAK:
                    LOGGER.info("clone stopped early, the source restricts forwarding")
                    break
                continue
            try:
                sent = await self._fan_out(unit)
            except CopyAborted:
                break
            if sent:
                streak = 0
                self.copied += len(unit)
                self.processed_bytes += self._bytes(unit)
            else:
                streak += 1
                if streak >= RESTRICTED_STREAK and not self.copied:
                    LOGGER.info("clone stopped early, nothing is copyable")
                    break
            self.listener.proceed_count = done + 1
        return self.copied

    def task(self):
        return self

    async def cancel_task(self):
        self.listener.is_cancelled = True
        LOGGER.info(f"Cancelling Clone: {self.listener.name}")
        await self.listener.on_upload_error("Telegram clone stopped by user!")
