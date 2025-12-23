import discord
from discord.ext import commands
from database import GUILD_ID

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='e!', intents=intents)

bot_ready = False

@bot.event
async def on_ready():
    global bot_ready
    bot_ready = True
    
    guild = bot.get_guild(GUILD_ID)
    if guild:
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)

def get_bot():
    global bot_ready
    if bot_ready and bot.is_ready():
        return bot
    return None
