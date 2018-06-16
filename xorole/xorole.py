import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from .utils.chat_formatting import box, pagify, warning
import asyncio
from collections import defaultdict

"""XORoles (exclusive-or roles) cog by GrumpiestVulcan
Commissioned 2017-07-27 by QuietRepentance (Quiet#8251) for discord.gg/pokken"""

__author__ = "Caleb Johnson <me@calebj.io> (calebj#0001)"
__copyright__ = "Copyright 2017, Holocor LLC"
__version__ = '1.2.0'

JSON = 'data/xorole.json'


class XORoleException(Exception):
    pass

class RolesetAlreadyExists(XORoleException):
    pass

class RolesetNotFound(XORoleException):
    pass

class NoRolesetsFound(XORoleException):
    pass

class RoleNotFound(XORoleException):
    pass

class PermissionsError(XORoleException):
    pass


class XORole:
    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json(JSON)


    def save(self):
        dataIO.save_json(JSON, self.settings)

    def get_settings(self, server):
        sid = server.id
        return self.settings.get(sid, {})

    def update_settings(self, server, settings):
        self.settings[server.id] = settings
        self.save()

    def add_roles(self, server, roleset, *roles):
        rsn, rsl = self.get_roleset(server, roleset)

        rslset = set(rsl)
        newset = set(r.id for r in roles)

        self.update_roleset(server, roleset, list(newset | rslset))

        return [r for r in roles if r.id not in rslset]

    def remove_roles(self, server, roleset, *roles):
        rsn, rsl = self.get_roleset(server, roleset)

        rslset = set(rsl)
        rmset = set(r.id for r in roles)

        self.update_roleset(server, roleset, list(rslset - rmset))

        return [r for r in roles if r.id in rslset]

    def get_rolesets(self, server):
        return self.get_settings(server).get('ROLESETS', {})

    def update_rolesets(self, server, rolesets):
        settings = self.get_settings(server)
        settings['ROLESETS'] = rolesets
        self.update_settings(server, settings)

    def get_roleset(self, server, name, notfound_ok=False):
        current = self.get_rolesets(server)
        if name in current:
            return name, current[name]

        searchname = name.lower().strip()
        for k, v in current.items():
            if k.lower().strip() == searchname:
                return k, v

        if not notfound_ok:
            raise RolesetNotFound("Roleset '%s' does not exist." % name)

    def add_roleset(self, server, name):
        if self.get_roleset(server, name, notfound_ok=True):
            raise RolesetAlreadyExists('A roleset with that name already exists.')

        current = self.get_rolesets(server)
        current[name] = []
        self.update_rolesets(server, current)

    def remove_roleset(self, server, name):
        name, roles = self.get_roleset(server, name)  # Raises RolesetNotFound

        current = self.get_rolesets(server)
        current.pop(name)
        self.update_rolesets(server, current)

    def update_roleset(self, server, name, role_ids):
        rolesets = self.get_rolesets(server)
        name, old_roles = self.get_roleset(server, name)  # Raises RolesetNotFound
        rolesets[name] = role_ids
        self.update_rolesets(server, rolesets)

    def roleset_of_role(self, role, notfound_ok=False):
        rid = role.id
        for rsn, rsl in self.get_rolesets(role.server).items():
            if rid in rsl:
                return rsn
        if not notfound_ok:
            raise NoRolesetsFound("The '%s' role doesn't belong to any "
                                  "rolesets" % role.name)

    def get_roleset_memberships(self, member, roleset):
        rsn, rsl = self.get_roleset(member.server, roleset)

        rslset = set(rsl)
        current_roles = []

        for role in member.roles:
            if role.id in rslset:
                current_roles.append(role)

        return current_roles

    @staticmethod
    def find_role(server, query, notfound_ok=False):
        stripped = query.strip().lower()

        for role in server.roles:
            if role.name.strip().lower() == stripped:  # Ignore case and spaces
                return role
            elif role.id == stripped:  # also work with role IDs
                return role

        if not notfound_ok:
            raise RoleNotFound("Could not find role '%s'." % query)

    @classmethod
    def find_roles(cls, server, *queries):
        found = []
        notfound = []

        for q in queries:
            role = cls.find_role(server, q, notfound_ok=True)
            if role:
                found.append(role)
            else:
                notfound.append(q)

        return found, notfound

    async def role_add_remove(self, member, to_add=(), to_remove=()):

        roles = set(member.roles)
        replace_with = (roles | set(to_add)) - set(to_remove)

        if roles != replace_with:
            try:
                await self.bot.replace_roles(member, *list(replace_with))
            except discord.errors.Forbidden:
                if not (member.server.me.server_permissions.manage_roles or
                        member.server.me.server_permissions.administrator):
                    err = "I don't have permission to manage roles."
                else:
                    err = ('a role I tried to assign or remove is too high '
                           'for me to do so.')
                raise PermissionsError('Error updating roles: ' + err)

    @commands.group(pass_context=True, invoke_without_command=True, no_pm=True)
    async def xorole(self, ctx, *, role: str = None):
        if ctx.invoked_subcommand is None:
            if role:
                await ctx.invoke(self.xorole_add, role=role)
            else:
                await self.bot.send_cmd_help(ctx)

    @xorole.command(name='list', pass_context=True)
    async def xorole_list(self, ctx, *, roleset: str = None):
        "Shows the available roles to in the server or a specific roleset."
        server = ctx.message.server
        try:
            if roleset:
                name, roles = self.get_roleset(server, roleset)
                rs_dict = {name: roles}
            else:
                rs_dict = self.get_rolesets(server)

            lines = ['=== Available roles: ===']

            for i, k in enumerate(sorted(rs_dict.keys())):
                roles = rs_dict[k]
                roles = (discord.utils.get(server.roles, id=r) for r in roles)
                roles = sorted(filter(None, roles))

                lines.append(k + ':')
                if roles:
                    lines.extend((' - %s' % rn) for rn in roles)
                else:
                    lines.append('- (there are no roles in this roleset)')

                if i + 1 < len(rs_dict):
                    lines.append('\n')

            if len(lines) == 1:
                await self.bot.say('No roles are available to assign.')
                return

            for page in pagify('\n'.join(lines)):
                await self.bot.say(box(page))

        except XORoleException as e:
            await self.bot.say(warning(*e.args))

    @xorole.command(name='add', pass_context=True)
    async def xorole_add(self, ctx, *, role: str):
        "Assigns a role to you, removing any others in the same roleset."
        server = ctx.message.server
        member = ctx.message.author

        try:
            role = self.find_role(server, role)
            roleset = self.roleset_of_role(role)
            existing = self.get_roleset_memberships(member, roleset)

            if role in member.roles and len(existing) == 1:
                await self.bot.say('You already have that role; nothing to do.')
                return

            to_add = [role]
            to_remove = [r for r in existing if r != role]

            await self.role_add_remove(member, to_add, to_remove)

            await self.bot.say("Role in roleset %s switched to %s."
                               % (roleset, role.name))

        except XORoleException as e:
            await self.bot.say(warning(*e.args))

    @xorole.command(name='remove', pass_context=True)
    async def xorole_remove(self, ctx, *, role_or_roleset: str):
        "Removes a specific role or any in a roleset from you."
        server = ctx.message.server
        member = ctx.message.author

        try:
            role = self.find_role(server, role_or_roleset, notfound_ok=True)
            if role:
                if role not in member.roles:
                    await self.bot.say("You don't have that role; nothing to do.")
                    return

                to_remove = [role]

            else:
                to_remove = self.get_roleset_memberships(member, role_or_roleset)

            if to_remove:
                await self.role_add_remove(member, to_remove=to_remove)
                plural = 'roles' if len(to_remove) > 1 else 'role'
                rlist = ', '.join(r.name for r in to_remove)
                await self.bot.say('Removed the %s: %s.' % (plural, rlist))
            else:
                await self.bot.say("You don't belong to any roles in the %s "
                                   "roleset." % role_or_roleset)

        except XORoleException as e:
            await self.bot.say(warning(*e.args))

    @xorole.command(name='toggle', pass_context=True)
    async def xorole_toggle(self, ctx, *, role_or_roleset: str):
        "Toggles a role in a single-role roleset on or off, or between two roles in a roleset."
        server = ctx.message.server
        member = ctx.message.author
        try:
            role = self.find_role(server, role_or_roleset, notfound_ok=True)
            if role:
                role_or_roleset = self.roleset_of_role(role)

            roleset, rsl = self.get_roleset(server, role_or_roleset)
            roles = (discord.utils.get(server.roles, id=r) for r in rsl)
            roles = list(filter(None, roles))

            if not 0 < len(roles) <= 2:
                await self.bot.say(warning("Cannot toggle within the '%s' "
                                           "roleset." % roleset))
                return

            if len(roles) == 1:
                single_role = roles[0]
                if single_role in member.roles:
                    to_add = []
                    to_remove = [single_role]
                else:
                    to_add = [single_role]
                    to_remove = []

            elif len(roles) == 2:
                to_remove = self.get_roleset_memberships(member, roleset)
                if len(to_remove) != 1:
                    await self.bot.say(warning("You must have one role in %s "
                                               "to toggle it." % roleset))
                    return

                to_add = roles.copy()
                to_add.remove(to_remove[0])

            await self.role_add_remove(member, to_add, to_remove)
            if to_add and to_remove:
                await self.bot.say('Toggled from %s to %s.'
                                   % (to_remove[0], to_add[0]))
            elif to_add:
                await self.bot.say("Role '%s' added." % to_add[0])
            elif to_remove:
                await self.bot.say("Role '%s' removed." % to_remove[0])

        except XORoleException as e:
            await self.bot.say(warning(*e.args))

    @commands.group(pass_context=True, no_pm=True)
    async def xoroleset(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @checks.mod_or_permissions(administrator=True)
    @xoroleset.command(name='addroleset', pass_context=True)
    async def xoroleset_addroleset(self, ctx, *, name: str):
        "Adds a roleset."
        server = ctx.message.server
        try:
            if len(name.split()) > 1:
                await self.bot.say('For usability reasons, whitespace is not '
                                   'permitted in roleset names. Try again.')
                return

            self.add_roleset(server, name)
            await self.bot.say("Roleset '%s' created." % name)
        except XORoleException as e:
            await self.bot.say(warning(*e.args))

    @checks.mod_or_permissions(administrator=True)
    @xoroleset.command(name='rmroleset', pass_context=True)
    async def xoroleset_rmroleset(self, ctx, *, name: str):
        "Removes a roleset."
        server = ctx.message.server
        try:
            self.remove_roleset(server, name)
            await self.bot.say("Roleset '%s' removed." % name)
        except XORoleException as e:
            await self.bot.say(warning(*e.args))

    @checks.mod_or_permissions(administrator=True)
    @xoroleset.command(name='renroleset', pass_context=True)
    async def xoroleset_renroleset(self, ctx, oldname: str, newname: str):
        "Renames a roleset."
        server = ctx.message.server
        try:
            if len(newname.split()) > 1:
                await self.bot.say('For usability reasons, whitespace is not '
                                   'permitted in roleset names. Try again.')
                return

            rsn, rsl = self.get_roleset(server, oldname)
            rolesets = self.get_rolesets(server)
            rolesets[newname] = rolesets.pop(rsn)
            self.update_rolesets(server, rolesets)
            await self.bot.say("Rename successful.")
        except XORoleException as e:
            await self.bot.say(warning(*e.args))

    @checks.mod_or_permissions(administrator=True)
    @xoroleset.command(name='audit', pass_context=True)
    async def xoroleset_audit(self, ctx):
        "Shows members with more than one role in a xorole roleset"
        lines = []
        server = ctx.message.server
        try:
            for rsn, rsl in self.get_rolesets(server).items():
                member_role_pairs = []
                for member in server.members:
                    memberships = self.get_roleset_memberships(member, rsn)
                    if len(memberships) > 1:
                        member_role_pairs.append((member, memberships))

                if not member_role_pairs:
                    continue

                lines.append(rsn + ':')
                for member, roles in member_role_pairs:
                    lines.append(' - %s : %s'
                                 % (member.display_name,
                                    ', '.join(r.name for r in roles)
                                    )
                                 )
                lines.append('\n')

            if not lines:
                await self.bot.say('All roleset memberships are singular.')
                return

            if lines[-1] == '\n':
                lines.pop()

            for page in pagify('\n'.join(lines)):
                await self.bot.say(box(page))

        except XORoleException as e:
            await self.bot.say(warning(*e.args))

        except XORoleException as e:
            await self.bot.say(warning(*e.args))

    @checks.mod_or_permissions(administrator=True)
    @xoroleset.command(name='addroles', aliases=['addrole'], pass_context=True)
    async def xoroleset_addroles(self, ctx, roleset: str, *, roles: str):
        """Adds one or more roles to a xorole roleset.

        Takes names or IDs seperated by commas."""
        server = ctx.message.server
        msg = []
        try:
            roles = roles.split(',')
            found, notfound = self.find_roles(server, *roles)
            rsn, rsl = self.get_roleset(server, roleset)
            to_add = []
            too_high = []
            already_in_roleset = defaultdict(lambda: list())

            for role in found:
                role_rsn = self.roleset_of_role(role, notfound_ok=True)
                if role_rsn and rsn != role_rsn:
                    already_in_roleset[role_rsn].append(role)
                elif role < ctx.message.author.top_role:
                    to_add.append(role)
                else:
                    too_high.append(role)

            if to_add:
                added = self.add_roles(server, roleset, *to_add)
                if added:
                    msg.append('Added these roles to the %s roleset: %s.'
                               % (roleset, ', '.join(r.name for r in added)))
                else:
                    msg.append('All found roles already added; nothing to do.')

            if already_in_roleset:
                msg.append('Some roles are already in other rolesets:')
                for rsn, roles in already_in_roleset.items():
                    rolelist = ', '.join(r.name for r in roles)
                    msg.append(' - %s: %s' % (rsn, rolelist))

            if too_high:
                msg.append('These roles are too high for you to manage: %s.'
                           % ', '.join(r.name for r in too_high))

            if notfound:
                msg.append('Could not find these role(s): %s.'
                           % ', '.join(("'%s'" % x) for x in notfound))

            await self.bot.say('\n'.join(msg))

        except XORoleException as e:
            await self.bot.say(warning(*e.args))

    @checks.mod_or_permissions(administrator=True)
    @xoroleset.command(name='rmroles', aliases=['rmrole'], pass_context=True)
    async def xoroleset_rmroles(self, ctx, roleset: str, *, roles: str):
        """Removes one or more roles from a xorole roleset.

        Takes role names or IDs seperated by commas."""
        server = ctx.message.server
        msg = []
        try:
            roles = roles.split(',')
            found, notfound = self.find_roles(server, *roles)
            to_remove = []
            too_high = []

            for role in found:
                if role < ctx.message.author.top_role:
                    to_remove.append(role)
                else:
                    too_high.append(role)

            if found:
                removed = self.remove_roles(server, roleset, *found)
                if removed:
                    msg.append('Removed these roles from the %s roleset: %s.'
                               % (roleset, ', '.join(r.name for r in removed)))
                else:
                    msg.append('None of the found roles are in the list; nothing to do.')

            if too_high:
                msg.append('These roles are too high for you to manage: %s.'
                           % ', '.join(r.name for r in too_high))

            if notfound:
                msg.append('Could not find these role(s): %s.'
                           % ', '.join(("'%s'" % x) for x in notfound))

            await self.bot.say('\n'.join(msg))

        except XORoleException as e:
            await self.bot.say(warning(*e.args))



def setup(bot):
    if not dataIO.is_valid_json(JSON):
        print("Creating %s..." % JSON)
        dataIO.save_json(JSON, {})

    bot.add_cog(XORole(bot))
