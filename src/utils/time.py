import jdatetime
import asyncio
import pytz
from datetime import date, datetime, timedelta


def to_utc(date: date):
    gregorian_datetime = datetime(
        date.year, date.month, date.day)

    local_tz = pytz.timezone('UTC')

    return local_tz.localize(gregorian_datetime)


def substract_hour(date: date, hours: int):
    return date - timedelta(hours=abs(hours))


def add_hour(date: date, hours: int):
    return date + timedelta(hours=abs(hours))


def substract_minutes(date: date, minutes: int):
    return date - timedelta(minutes=abs(minutes))


class Timer:
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._task = asyncio.create_task(self._job())

    async def _job(self):
        await asyncio.sleep(self._timeout)
        await self._callback()

    def cancel(self):
        self._task.cancel()


def set_timeout(fn, ms, *args, **kwargs):
    return Timer(ms / 1000., fn)


def convert_to_jajali(date: date):
    return jdatetime.date.fromgregorian(date=date)
