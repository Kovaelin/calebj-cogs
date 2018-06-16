from discord.ext import commands
from .utils.chat_formatting import box, pagify, warning
from .utils.dataIO import dataIO
from .utils import checks
import asyncio
import os
from copy import copy

__version__ = '1.3.0'

PATH = 'data/galias/'
JSON = PATH + 'aliases.json'


class GlobalAlias:
    def __init__(self, bot):
        self.bot = bot
        self.aliases = dataIO.load_json(JSON)


    def save(self):
        dataIO.save_json(JSON, self.aliases)

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def galias(self, ctx):
        """Manage global aliases for commands"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @galias.command(name="add", pass_context=True)
    async def _add_alias(self, ctx, command, *, to_execute):
        """
        Add a global alias for a command

        Example: !galias add test flip @Twentysix
        """

        command = command.lower()
        server = ctx.message.server
        if ' ' in command:
            await self.bot.say("Aliases can't contain spaces.")
            return

        existing = self.servers_with_alias(command)
        if existing:
            this_server = server in existing
            incl = ", including this one" if this_server else ""

            await self.bot.say(warning("{} is already a regular alias in "
                                       "{} servers{}. In those servers, the "
                                       "existing alias will take priority."
                                       ).format(command, len(existing), incl))

        new_message = copy(ctx.message)
        new_message.content = to_execute
        prefix = await self.get_prefix(new_message)

        if prefix is not None:
            to_execute = to_execute[len(prefix):]

        if command in self.bot.commands:
            await self.bot.say(warning("Cannot add '{}', because it's a real "
                                       "bot command.".format(command)))
        elif command in self.aliases:
            await self.bot.say(warning("The alias '{0}' already exists. "
                                       "Remove it first, or use `{1}galias "
                                       "edit {0} ...`".format(command, prefix)
                                       ))
        else:
            self.aliases[command] = to_execute
            self.save()
            await self.bot.say("Global alias '{}' added.".format(command))

    @galias.command(name="edit", pass_context=True)
    async def _edit_alias(self, ctx, command, *, to_execute):
        """Edits an alias"""

        new_message = copy(ctx.message)
        new_message.content = to_execute
        prefix = await self.get_prefix(new_message)

        if prefix is not None:
            to_execute = to_execute[len(prefix):]

        if command in self.aliases:
            self.aliases[command] = to_execute
            self.save()
            await self.bot.say("Global alias '{}' updated.".format(command))
        else:
            await self.bot.say(warning("That alias doesn't exist."))

    @galias.command(name="rename", pass_context=True)
    async def _rename_alias(self, ctx, old_name, new_name):
        """Edits an alias"""

        server = ctx.message.server
        if ' ' in new_name:
            await self.bot.say("Aliases can't contain spaces.")
            return

        existing = self.servers_with_alias(new_name)
        if existing:
            this_server = server in existing
            incl = ", including this one" if this_server else ""

            await self.bot.say(warning("{} is already a regular alias in "
                                       "{} servers{}. In those servers, the "
                                       "existing alias will take priority."
                                       ).format(new_name, len(existing), incl))

        if new_name in self.bot.commands:
            await self.bot.say(warning("Cannot rename to '{}', because it's a"
                                       " real bot command.".format(new_name)))
        elif new_name in self.aliases:
            await self.bot.say(warning("The alias '{}' already exists.".format(new_name)))
        elif old_name in self.aliases:
            self.aliases[new_name] = self.aliases.pop(old_name)
            self.save()
            await self.bot.say("Global alias '{}' renamed to '{}'."
                               .format(old_name, new_name))
        else:
            await self.bot.say(warning("Alias '{}' doesn't exist.".format(old_name)))

    @galias.command(name="help", pass_context=True)
    async def _help_alias(self, ctx, command):
        """Tries to execute help for the base command of the alias"""
        if command in self.aliases:
            help_cmd = self.aliases[command].split(" ")[0]
            new_content = ctx.prefix
            new_content += "help "
            new_content += help_cmd[len(ctx.prefix):]
            message = ctx.message
            message.content = new_content
            await self.bot.process_commands(message)
        else:
            await self.bot.say(warning("That alias doesn't exist."))

    @galias.command(name="show")
    async def _show_alias(self, command):
        """Shows what command the alias executes."""
        if command in self.aliases:
            await self.bot.say(box(self.aliases[command]))
        else:
            await self.bot.say(warning("That alias doesn't exist."))

    @galias.command(name="del", pass_context=True, aliases=['remove'])
    async def _del_alias(self, ctx, command):
        """Deletes an alias"""
        command = command.lower()
        if command in self.aliases:
            self.aliases.pop(command, None)
            self.save()
            await self.bot.say("Global alias '{}' deleted.".format(command))
        else:
            await self.bot.say(warning("That alias doesn't exist."))

    @galias.command(name="list", pass_context=True)
    async def _alias_list(self, ctx):
        """Lists global command aliases"""
        header = "Alias list:\n"
        shorten = len(header) + 8
        alias_list = ""

        if not self.aliases:
            await self.bot.say("There are no global aliases.")
            return

        for alias in sorted(self.aliases):
            alias_list += alias + '\n'

        pages = pagify(alias_list, shorten_by=shorten)
        for i, page in enumerate(pages):
            if i == 0:
                page = header + box(page)
            else:
                page = box(page)
            await self.bot.say(page)

    @galias.command(name="overrides")
    async def _show_overrides(self, alias):
        """Shows which servers have a regular alias set."""

        if not self.bot.get_cog('Alias'):
            await self.bot.say(warning("The alias cog must be loaded to "
                                       "check for local overrides."))
            return

        servers = self.servers_with_alias(alias)

        if not servers:
            await self.bot.say("No servers have '{}' as a local alias.".format(alias))
            return

        servers = sorted(servers, key=lambda s: s.name)
        servers_str = '      Server ID      | Server Name\n'
        servers_str += '\n'.join('{0.id:>20} | {0.name}'.format(s) for s in servers)
        for page in pagify(servers_str):
            await self.bot.say(box(page))

    async def on_message(self, message):
        if not self.bot.user_allowed(message):
            return

        server = message.server

        prefix = await self.get_prefix(message)
        msg = message.content

        if prefix:
            alias = self.first_word(msg[len(prefix):]).lower()

            if alias not in self.aliases:
                return
            elif alias in self.bot.commands:
                return
            if server and alias in self.get_existing_aliases(server):
                return

            new_command = self.aliases[alias]
            args = message.content[len(prefix + alias):]
            new_message = copy(message)
            new_message.content = prefix + new_command + args
            await self.bot.process_commands(new_message)


    def part_of_existing_command(self, alias):
        '''Command or alias'''
        for command in self.bot.commands:
            if alias.lower() == command.lower():
                return True
        return False

    def get_existing_aliases(self, server):
        if server is None:
            return {}
        try:
            alias_cog = self.bot.get_cog('Alias')
            return alias_cog.aliases[server.id]
        except Exception:
            return {}

    def servers_with_alias(self, alias):
        servers = set()
        try:
            alias_cog = self.bot.get_cog('Alias')
            aliases = alias_cog.aliases

            for sid, alias_map in aliases.items():
                server = self.bot.get_server(sid)
                if server and alias in alias_map:
                    servers.add(server)

        except Exception:
            pass
        finally:
            return servers

    def first_word(self, msg):
        return msg.split(" ")[0]

    async def get_prefix(self, msg):
        prefixes = self.bot.command_prefix
        if callable(prefixes):
            prefixes = prefixes(self.bot, msg)
            if asyncio.iscoroutine(prefixes):
                prefixes = await prefixes

        for p in prefixes:
            if msg.content.startswith(p):
                return p
        return None


def check_folder():
    if not os.path.exists(PATH):
        print("Creating data/galias folder...")
        os.makedirs(PATH)


def check_file():
    if not dataIO.is_valid_json(JSON):
        print("Creating aliases.json...")
        dataIO.save_json(JSON, {})


def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(GlobalAlias(bot))
