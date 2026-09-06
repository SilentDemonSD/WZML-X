from asyncio import sleep
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
from ....core.config_manager import Config
from ...ext_utils.filter_utils import file_name_of, size_of
from ...telegram_helper.tg_copy import (
    FORWARD_BATCH,
    CopyAborted,
    CopyRestricted,
    TgCopier,
    message_link,
)

MAX_FLOOD_WAIT = 600
RESTRICTED_STREAK = 3
PACE_MAX = 4.0
PACE_STEP = 0.25
PACE_COOL = 20
FAILED_KEEP = 200

DEST_FATAL = (
    ChatWriteForbidden,
    ChatSendMediaForbidden,
    ChannelPrivate,
    PeerIdInvalid,
    ChatAdminRequired,
    UserBannedInChannel,
)


def clone_limit():
    return Config.CLONE_TG_LIMIT or 0


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


def group_runs(messages):
    units = []
    for message in messages:
        group = getattr(message, "media_group_id", None)
        if group and units and getattr(units[-1][-1], "media_group_id", None) == group:
            units[-1].append(message)
        else:
            units.append([message])
    return units


class UnitStream:
    def __init__(self, client, chat, batches):
        self._client = client
        self._chat = chat
        self._batches = batches
        self._first_done = False
        self.fetched = 0

    async def _whole(self, unit):
        if len(unit) < 2:
            return [unit]
        try:
            whole = await self._client.get_media_group(self._chat, unit[0].id)
        except Exception as err:
            LOGGER.debug(f"media group check failed for {unit[0].id}: {err}")
            return [[one] for one in unit]
        if len(whole) != len(unit):
            return [[one] for one in unit]
        return [unit]

    async def _emit(self, unit, last):
        edge = last or not self._first_done
        self._first_done = True
        if edge:
            return await self._whole(unit)
        return [unit]

    async def units(self):
        held = None
        carry = []
        async for batch in self._batches:
            self.fetched += len(batch)
            runs = group_runs(carry + batch)
            carry = []
            if runs and getattr(runs[-1][0], "media_group_id", None):
                carry = runs.pop()
            for run in runs:
                if held is not None:
                    for one in await self._emit(held, False):
                        yield one
                held = run
        if carry:
            if held is not None:
                for one in await self._emit(held, False):
                    yield one
            held = carry
        if held is not None:
            for one in await self._emit(held, True):
                yield one


class FilteredStream:
    def __init__(self, stream, keep):
        self._stream = stream
        self._keep = keep
        self.dropped = 0

    @property
    def fetched(self):
        return self._stream.fetched

    async def units(self):
        async for unit in self._stream.units():
            passed = [one for one in unit if self._keep(one)]
            if not passed:
                self.dropped += len(unit)
                continue
            if len(passed) == len(unit):
                yield unit
                continue
            self.dropped += len(unit) - len(passed)
            for one in passed:
                yield [one]


class TelegramClone:
    def __init__(self, listener, client, stream, dests, total, forward=False):
        self.listener = listener
        self._client = client
        self._stream = stream
        self._dests = list(dests)
        self._total = max(1, total)
        self._copier = TgCopier(
            client,
            cancel=lambda: self.listener.is_cancelled,
            max_wait=MAX_FLOOD_WAIT,
            forward=forward,
        )
        self._start = time()
        self._pace = 0.0
        self._clean = 0
        self._flooded_at = 0
        self.seen = 0
        self.units = 0
        self.planned = 0
        self.copied = 0
        self.processed_bytes = 0
        self.restricted = []
        self.failed = []
        self.failures = 0
        self.dead_dests = []
        self.first_link = ""

    @property
    def total_units(self):
        return self._total

    @property
    def live_dests(self):
        return len(self._dests)

    @property
    def floods(self):
        return self._copier.floods

    @staticmethod
    def _label(units):
        if len(units) > 1:
            span = sum(len(unit) for unit in units)
            return f"batch of {span}"
        unit = units[0]
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

    async def _breathe(self):
        seen = self._copier.floods
        if seen > self._flooded_at:
            self._flooded_at = seen
            self._pace = min(PACE_MAX, self._pace + PACE_STEP)
            self._clean = 0
            LOGGER.info(f"clone pacing raised to {self._pace:.2f}s after a flood wait")
        elif self._pace:
            self._clean += 1
            if self._clean >= PACE_COOL:
                self._clean = 0
                self._pace = max(0.0, self._pace - PACE_STEP)
        if self._pace:
            await sleep(self._pace)

    async def _fan_out(self, units):
        landed = 0
        ids = [one.id for unit in units for one in unit]
        source = units[0][0].chat.id
        for seat in list(self._dests):
            if self.listener.is_cancelled:
                return False
            try:
                if len(units) > 1:
                    sent = await self._copier.batch(seat[0], source, ids, seat[1])
                    sent = sent[0] if sent else None
                else:
                    sent = await self._copier.send(seat[0], units[0], seat[1])
            except CopyRestricted:
                self.restricted.extend(ids)
                return False
            except CopyAborted:
                raise
            except DEST_FATAL as err:
                self._kill_dest(seat, type(err).__name__)
                continue
            except Exception as err:
                self.failures += 1
                if len(self.failed) < FAILED_KEEP:
                    self.failed.append((ids[0], str(err)))
                LOGGER.error(f"clone failed at {ids[0]}: {err}")
                return False
            landed += 1
            if not self.first_link:
                self.first_link = message_link(sent)
        return landed > 0

    async def _jobs(self):
        if not self._copier.forward:
            async for unit in self._stream.units():
                yield [unit]
            return
        held = []
        count = 0
        async for unit in self._stream.units():
            if self._protected(unit):
                if held:
                    yield held
                    held, count = [], 0
                yield [unit]
                continue
            if held and count + len(unit) > FORWARD_BATCH:
                yield held
                held, count = [], 0
            held.append(unit)
            count += len(unit)
        if held:
            yield held

    async def relay(self):
        streak = 0
        jobs = self._jobs()
        try:
            async for units in jobs:
                if self.listener.is_cancelled or not self._dests:
                    break
                span = sum(len(unit) for unit in units)
                weight = sum(self._bytes(unit) for unit in units)
                self.units += len(units)
                self.planned += weight
                self.listener.size = self.planned
                self.listener.subname = self._label(units)
                self.listener.subsize = weight
                if self._protected(units[0]):
                    self.restricted.extend(one.id for unit in units for one in unit)
                    self.seen += span
                    self.listener.proceed_count = self.seen
                    streak += 1
                    if streak >= RESTRICTED_STREAK and not self.copied:
                        LOGGER.info(
                            "clone stopped early, the source forbids forwarding"
                        )
                        break
                    continue
                try:
                    sent = await self._fan_out(units)
                except CopyAborted:
                    break
                if sent:
                    streak = 0
                    self.copied += span
                    self.processed_bytes += weight
                else:
                    streak += 1
                    if streak >= RESTRICTED_STREAK and not self.copied:
                        LOGGER.info("clone stopped early, nothing is copyable")
                        break
                self.seen += span
                self.listener.proceed_count = self.seen
                await self._breathe()
        finally:
            await jobs.aclose()
        return self.copied

    def task(self):
        return self

    async def cancel_task(self):
        self.listener.is_cancelled = True
        LOGGER.info(f"Cancelling Clone: {self.listener.name}")
        await self.listener.on_upload_error("Telegram clone stopped by user!")
