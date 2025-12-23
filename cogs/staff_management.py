import discord
from discord.ext import commands
from discord import app_commands
from .staff_management_utils import StaffManagementUtils
from .staff_management_views import PromotionView, RankChangeView, DemotionView, StaffApprovalView
from database import get_role_by_name, RANK_HIERARCHY, SPECIAL_ROLES, ROBLOX_GROUP_ID, STAFF_ROLES

def hr_plus_only():
    async def predicate(interaction: discord.Interaction):
        hr_plus_role_ids = [
            942019580921008188,
            942019582741323826,
            943123573592195112,
            942019581986340864,
            942019588500127795
        ]
        
        user_roles = [role.id for role in interaction.user.roles]
        has_hr_plus = any(role_id in user_roles for role_id in hr_plus_role_ids)
        
        if not has_hr_plus:
            await interaction.response.send_message(
                "❌ You need HR+ permissions to use this command!", 
                ephemeral=True
            )
            return False
        
        return True
    
    return app_commands.check(predicate)

class StaffManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.utils = StaffManagementUtils(bot)

    @app_commands.command(name="changerank", description="Change a staff member's rank to a specific position")
    @app_commands.describe(user_identifier="Roblox username, Discord user ID, or Roblox user ID")
    @hr_plus_only()
    async def changerank(self, interaction: discord.Interaction, user_identifier: str):
        try:
            user_type = self.utils.determine_user_type(user_identifier)
            view = RankChangeView(user_identifier, user_type, self.utils)
            
            await interaction.response.send_message(
                f"Please select the new rank for **{user_identifier}**:",
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error processing rank change request: {str(e)}", 
                ephemeral=True
            )

    @app_commands.command(name="promote", description="Promote a staff member to the next rank in the hierarchy")
    @app_commands.describe(user_identifier="Roblox username, Discord user ID, or Roblox user ID")
    @hr_plus_only()
    async def promote(self, interaction: discord.Interaction, user_identifier: str):
        try:
            user_type = self.utils.determine_user_type(user_identifier)
            view = PromotionView(user_identifier, user_type, self.utils)
            
            await interaction.response.send_message(
                f"**{user_identifier}** will be promoted to the next rank. Do you want to proceed?",
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error processing promotion request: {str(e)}", 
                ephemeral=True
            )

    @app_commands.command(name="demote", description="Demote a staff member with a specified reason")
    @app_commands.describe(user_identifier="Roblox username, Discord user ID, or Roblox user ID", reason="Reason for demotion")
    @hr_plus_only()
    async def demote(self, interaction: discord.Interaction, user_identifier: str, reason: str):
        try:
            user_type = self.utils.determine_user_type(user_identifier)
            view = DemotionView(user_identifier, user_type, reason, self.utils)
            
            await interaction.response.send_message(
                f"**{user_identifier}** will be demoted. Do you want to proceed?",
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error processing demotion request: {str(e)}", 
                ephemeral=True
            )

    @app_commands.command(name="deletebadstreak", description="Remove bad streaks from a staff member's record")
    @app_commands.describe(user_identifier="Roblox username, Discord user ID, or Roblox user ID", count="Number of bad streaks to remove (1-2)")
    @hr_plus_only()
    async def deletebadstreak(self, interaction: discord.Interaction, user_identifier: str, count: int):
        try:
            await interaction.response.defer(ephemeral=True)
            
            if count < 1 or count > 2:
                await interaction.followup.send("❌ Count must be between 1 and 2", ephemeral=True)
                return
            
            staff_member = await self.utils.get_staff_member_detailed(user_identifier)
            
            if not staff_member:
                await interaction.followup.send("❌ Staff member not found", ephemeral=True)
                return
            
            roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at = staff_member
            
            if bad_streak <= 0:
                await interaction.followup.send(f"❌ {roblox_username} has no bad streaks to remove", ephemeral=True)
                return
            
            new_bad_streak = max(0, bad_streak - count)
            
            from database import update_bad_streak
            update_bad_streak(roblox_user_id, new_bad_streak)
            
            await interaction.followup.send(
                f"✅ Removed {count} bad streak(s) from {roblox_username}\n"
                f"Bad streaks: {bad_streak} → {new_bad_streak}",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Error in deletebadstreak: {e}")
            await interaction.followup.send(f"Error removing bad streaks: {str(e)}", ephemeral=True)

    @app_commands.command(name="speak", description="Make the bot send a message with full Discord markdown support")
    @app_commands.describe(message="The message content to send (supports Discord markdown, mentions, etc.)")
    @hr_plus_only()
    async def speak(self, interaction: discord.Interaction, message: str):
        try:
            await interaction.response.defer(ephemeral=True)
            
            if not message.strip():
                await interaction.followup.send("❌ Message content cannot be empty", ephemeral=True)
                return
            
            await interaction.channel.send(content=message)
            await interaction.followup.send("✅ Message sent successfully", ephemeral=True)
            
        except discord.Forbidden:
            await interaction.followup.send("❌ Bot doesn't have permission to send messages in this channel", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"❌ Failed to send message: {str(e)}", ephemeral=True)
        except Exception as e:
            print(f"Error in speak command: {e}")
            await interaction.followup.send(f"❌ Error sending message: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(StaffManagement(bot))
