import discord
from discord.ext import commands
import sys, traceback
from datetime import datetime
import platform


initial_extensions = ['counting']
bot = commands.Bot(command_prefix="pls ", description=f'We count')

if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print(f'Failed to load extension {extension}.', file=sys.stderr)
            traceback.print_exc()

@bot.event
async def on_ready():
    """http://discordpy.readthedocs.io/en/rewrite/api.html#discord.on_ready"""
    print(f'\n\nLogged in as: {bot.user.name} - {bot.user.id}\nVersion: {discord.__version__}\n')
    print(f'[{datetime.now()}] Successfully logged in and booted...!')

bot.run("",reconnect=True)
