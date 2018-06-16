import asyncio
import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
import re

__version__ = '1.2.0'

JSON = 'data/purgepins.json'
MAX_PINS = 50


UNIT_TABLE = (
    (('weeks', 'wks', 'w'), 60 * 60 * 24 * 7),
    (('days', 'dys', 'd'), 60 * 60 * 24),
    (('hours', 'hrs', 'h'), 60 * 60),
    (('minutes', 'mins', 'm'), 60),
    (('seconds', 'secs', 's'), 1),
)

class BadTimeExpr(Exception):
    pass


def _find_unit(unit):
    for names, length in UNIT_TABLE:
        if any(n.startswith(unit) for n in names):
            return names, length
    raise BadTimeExpr("Invalid unit: %s" % unit)


def _parse_time(time):
    time = time.lower()
    if not time.isdigit():
        time = re.split(r'\s*([\d.]+\s*[^\d\s,;]*)(?:[,;\s]|and)*', time)
        time = sum(map(_timespec_sec, filter(None, time)))
    return int(time)


def _timespec_sec(expr):
    atoms = re.split(r'([\d.]+)\s*([^\d\s]*)', expr)
    atoms = list(filter(None, atoms))

    if len(atoms) > 2:  # This shouldn't ever happen
        raise BadTimeExpr("invalid expression: '%s'" % expr)
    elif len(atoms) == 2:
        names, length = _find_unit(atoms[1])
        if atoms[0].count('.') > 1 or \
                not atoms[0].replace('.', '').isdigit():
            raise BadTimeExpr("Not a number: '%s'" % atoms[0])
    else:
        names, length = _find_unit('seconds')

    return float(atoms[0]) * length


def _generate_timespec(sec, short=False, micro=False):
    timespec = []

    for names, length in UNIT_TABLE:
        n, sec = divmod(sec, length)

        if n:
            if micro:
                s = '%d%s' % (n, names[2])
            elif short:
                s = '%d%s' % (n, names[1])
            else:
                s = '%d %s' % (n, names[0])
            if n <= 1:
                s = s.rstrip('s')
            timespec.append(s)

    if len(timespec) > 1:
        if micro:
            return ''.join(timespec)

        segments = timespec[:-1], timespec[-1:]
        return ' and '.join(', '.join(x) for x in segments)

    return timespec[0]


class PurgePins:
    """Automatically rotates pins and deletes notifications."""
    def __init__(self, bot):
        self.bot = bot
        self.handles = {}

        self.settings = dataIO.load_json(JSON)
        if any(type(x) is not list for x in self.settings.values()):
            self.upgrade_settings(self.settings)
            dataIO.save_json(JSON, self.settings)


        self.task_handle = self.bot.loop.create_task(self.start_task())

    def __unload(self):
        self.task_handle.cancel()

    async def start_task(self):
        await self.bot.wait_until_ready()
        for cid in self.settings:
            channel = self.bot.get_channel(cid)
            if channel:
                await self.do_pin_rotate(channel)

    def upgrade_settings(self, settings):
        for k, v in settings.items():
            if type(v) is not dict:
                settings[k] = {'PURGE_DELAY': v}

    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def purgepins(self, ctx, wait: str = None):
        """Set delay for deletion of pin messages, or disable it.

        Accepted time units are s(econds), m(inutes), h(ours).
        Example: !purgepins 1h30m
        To disable purepins, run !purgepins off"""
        channel = ctx.message.channel
        if wait is not None:
            if wait.strip().lower() in ['none', 'off']:
                wait = False
            else:
                try:
                    wait = _parse_time(wait)
                except BadTimeExpr as e:
                    await self.bot.say("Error parsing duration: %s." % e.args)
                    return

            if channel.id not in self.settings:
                self.settings[channel.id] = {}
            self.settings[channel.id]['PURGE_DELAY'] = wait

            dataIO.save_json(JSON, self.settings)
        else:
            wait = self.settings.get(channel.id, {}).get('PURGE_DELAY', False)

        if wait is False:
            msg = ('Pin notifications in this channel will not be '
                   'automatically deleted.')
        else:
            msg = 'Pin notifications in this channel are set to be deleted '
            if wait > 0:
                msg += 'after %s.' % _generate_timespec(wait)
            else:
                msg += 'immediately.'

        if not channel.permissions_for(channel.server.me).manage_messages:
            msg += ("\n**Warning:** I don't have permissions to delete "
                    "messages in this channel!")

        await self.bot.say(msg)

    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def rotatepins(self, ctx, on_off: bool = None):
        "Sets whether the oldest pin is automatically removed at 50."
        channel = ctx.message.channel
        msg = 'Pin auto-rotation %s in this channel.'

        current = self.settings.get(channel.id, {}).get('ROTATE_PINS')

        if on_off is None:
            on_off = current
            status = 'is currently '
        elif on_off == current:
            status = 'was already '
        else:
            if channel.id not in self.settings:
                self.settings[channel.id] = {}
            self.settings[channel.id]['ROTATE_PINS'] = on_off
            dataIO.save_json(JSON, self.settings)
            status = 'is now '
            await self.do_pin_rotate(channel)

        if not channel.permissions_for(channel.server.me).manage_messages:
            msg += ("\n**Warning:** I don't have permissions to manage "
                    "messages in this channel!")

        status += 'enabled' if on_off else 'disabled'
        await self.bot.say(msg % status)

    async def on_message(self, message):
        channel = message.channel

        if channel.is_private or channel.id not in self.settings:
            return
        if not channel.permissions_for(channel.server.me).manage_messages:
            return

        settings = self.settings[channel.id]
        if message.type is discord.MessageType.pins_add:
            timeout = settings.get('PURGE_DELAY', False)
            if timeout is not False:
                task = self.delete_task(message, timeout)
                self.handles[message.id] = self.bot.loop.create_task(task)

    async def on_message_delete(self, message):
        if message.id in self.handles:
            self.handles[message.id].cancel()
            del self.handles[message.id]

    async def on_message_edit(self, before, after):
        channel = after.channel
        if channel.is_private or channel.id not in self.settings:
            return
        if after.pinned and not before.pinned:
            await self.do_pin_rotate(channel)

    async def do_pin_rotate(self, channel):
        if not channel.permissions_for(channel.server.me).manage_messages:
            return

        settings = self.settings[channel.id]
        if settings.get('ROTATE_PINS', False):
            pins = await self.bot.pins_from(channel)
            if len(pins) >= MAX_PINS:
                await self.bot.unpin_message(pins[-1])

    async def delete_task(self, message, timeout):
        await asyncio.sleep(timeout)
        try:
            await self.bot.delete_message(message)
        except Exception:
            pass

        if message.id in self.handles:
            self.handles.pop(message.id)

def check_files(bot):
    if not dataIO.is_valid_json(JSON):
        print("Creating default purgepins json...")
        dataIO.save_json(JSON, {})


def setup(bot):
    check_files(bot)
    n = PurgePins(bot)
    bot.add_cog(n)
