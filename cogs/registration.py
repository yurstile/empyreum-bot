import discord
from discord.ext import commands
from discord import app_commands
from database import get_role_by_name, add_pending_verification, is_user_pending

class Registration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="register", description="Register as a patient, join ranking centre and get the role.")
    async def register(self, interaction: discord.Interaction):
        admittee_role = get_role_by_name("admittee")
        if not admittee_role:
            await interaction.response.send_message("Admittee role not found in database.", ephemeral=True)
            return
        
        discord_role_id = admittee_role[1]
        member = interaction.user
        
        has_admittee_role = any(role.id == int(discord_role_id) for role in member.roles)
        
        if not has_admittee_role:
            await interaction.response.send_message("You need the Admittee role to register.", ephemeral=True)
            return
        
        username = member.display_name
        discord_id = str(member.id)
        
        if is_user_pending(discord_id):
            add_pending_verification(discord_id, username)
            await interaction.response.send_message(
                f"> **{username}**, your pending registration has been updated. Please visit our [ranking centre](https://www.roblox.com/games/15159914168/Lunatic-Ranking-Service) to complete the registration.",
                ephemeral=False
            )
        else:
            add_pending_verification(discord_id, username)
            await interaction.response.send_message(
                f"> **{username}**, please visit our [ranking centre](https://www.roblox.com/games/15159914168/Lunatic-Ranking-Service) to complete the registration.",
                ephemeral=False
            )

async def setup(bot):
    await bot.add_cog(Registration(bot))
