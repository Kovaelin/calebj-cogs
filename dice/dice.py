from discord.ext import commands
from .utils.chat_formatting import box, warning, pagify
from pyparsing import ParseBaseException

try:
    import dice
except (ImportError, AssertionError):
    raise ImportError('Please install the dice package from pypi.') from None

DICE_200 = dice.__version__ >= '2.0.0'
DICE_210 = dice.__version__ >= '2.1.0'
DICE_220 = dice.__version__ >= '2.2.0'

if DICE_220:
    from dice import DiceBaseException


__version__ = '1.1.0'

UPDATE_MSG = ("The version of the dice library installed on the bot (%s) is "
              "too old for the requested command. Please ask the bot owner "
              "to update it.\n\nOwners: you can install/update with:\n```\n"
              "[p]debug bot.pip_install('dice')\n```") % dice.__version__


class Dice:
    """A cog which uses the python-dice library to provide powerful dice
    expression parsing for your games!"""
    def __init__(self, bot):
        self.bot = bot


    @commands.group(pass_context=True, name='dice', invoke_without_command=True)
    async def _dice(self, ctx, *, expr: str = 'd20'):
        """Evaluates a dice expression. Defaults to roll a d20.

        Valid operations include the 'mdn' dice operator, which rolls m dice
        with n sides. If m is omitted, it is assumed to be 1.
        Modifiers include basic algebra, 't' to total a result,
        's' to sort multiple rolls, '^n' to only use the n highest rolls, and
        'vn' to use the lowest n rolls. This cog uses the dice library.

        The full list of operators can be found at:
        https://github.com/borntyping/python-dice#notation

        Examples: 4d20, d100, 6d6v2, 8d4t, 4d4 + 4, 6d8^2

        Note that some commands may be disabled, depending on the version of
        the dice library that is installed."""

        if ctx.invoked_subcommand is None:
            await self.roll_common(ctx, expr)

    @_dice.command(pass_context=True, name='min')
    async def dice_min(self, ctx, *, expr: str = 'd20'):
        "Evaluates the minimum of an expression."

        if not DICE_200:
            await self.bot.say(warning(UPDATE_MSG))
            return

        await self.roll_common(ctx, expr, dice.roll_min)

    @_dice.command(pass_context=True, name='max')
    async def dice_max(self, ctx, *, expr: str = 'd20'):
        "Evaluates the maximum of an expression."

        if not DICE_200:
            await self.bot.say(warning(UPDATE_MSG))
            return

        await self.roll_common(ctx, expr, dice.roll_max)

    @_dice.command(pass_context=True, name='verbose')
    async def dice_verbose(self, ctx, *, expr: str = 'd20'):
        "Shows the complete breakdown of an expression."

        if not DICE_200:
            await self.bot.say(warning(UPDATE_MSG))
            return

        await self.roll_common(ctx, expr, dice.roll, verbose=True)

    async def roll_common(self, ctx, expr, func=dice.roll, verbose=False):
        try:
            if DICE_210:
                roll, kwargs = func(expr, raw=True, return_kwargs=True)
                result = roll.evaluate_cached(**kwargs)
            elif DICE_200:
                roll = func(expr, raw=True)
                result = roll.evaluate_cached()
            else:
                result = func(expr)

        except ParseBaseException as e:
            msg = warning('An error occured while parsing your expression:\n')

            if DICE_220 and isinstance(e, DiceBaseException):
                msg += box(e.pretty_print())
            else:
                msg += str(e)
                msg += ('\n\nFor a more detailed explanation, ask the bot '
                        'owner to update to Dice v2.2.0 or greater.')

            await self.bot.say(msg)
            return

        if DICE_200 and verbose:
            if DICE_210:
                breakdown = dice.utilities.verbose_print(roll, **kwargs)
            else:
                breakdown = dice.utilities.verbose_print(roll)

            pages = list(map(box, pagify(breakdown)))

            for page in pages[:-1]:
                await self.bot.say(page)

        if isinstance(result, int):
            res = str(result)
        elif len(result) > 0:
            total = sum(result)
            res = ', '.join(map(str, result))

            if len(res) > 1970:
                res = '[result set too long to display]'
            if len(result) > 1:
                res += ' (total: %s)' % total
        else:
            res = 'Empty result!'

        res = ':game_die: %s' % res

        if DICE_200 and verbose:
            if len(res) + len(pages[-1]) >= (2000 - 1):
                await self.bot.say(pages[-1])
            else:
                res = pages[-1] + '\n' + res

        await self.bot.say(res)


def setup(bot):
    bot.add_cog(Dice(bot))
