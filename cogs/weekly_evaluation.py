import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
from datetime import datetime, timezone, timedelta
from database import (
    get_all_staff, update_staff_role, get_role_by_name, RANK_HIERARCHY,
    increment_excellence_score, increment_bad_streak, increment_minimum_streak,
    reset_bad_streak, reset_all_evaluation_week_scores, update_staff_role,
    get_all_server_player_counts, get_active_server_count
)
import asyncio
import requests
from .weekly_evaluation_utils import WeeklyEvaluationUtils

def hr_plus_only():
    """Decorator to restrict commands to HR+ roles only"""
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


def yurstile_only():
    async def predicate(interaction: discord.Interaction):
        me_role_id = [
            1409201856806129756,
            942019580921008188
        ]
        
        user_roles = [role.id for role in interaction.user.roles]
        has_hr_plus = any(role_id in user_roles for role_id in me_role_id)
        
        if not has_hr_plus:
            await interaction.response.send_message(
                "Do not dare to do it!", 
                ephemeral=True
            )
            return False
        
        return True
    
    return app_commands.check(predicate)

class WeeklyEvaluation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.utils = WeeklyEvaluationUtils(bot)
        self.server_status_message_id = None
        self.server_status_channel_id = None
        self.patient_channel_id = 1421849016039117000
        self.staff_channel_id = 1421849060549201940
        self.server_status_message_is_embed = False

    def cog_unload(self):
        if self.weekly_evaluation.is_running():
            self.weekly_evaluation.cancel()
        if self.server_status_updater.is_running():
            self.server_status_updater.cancel()

    @tasks.loop(seconds=1)
    async def weekly_evaluation(self):
        print(f"[DEBUG] Weekly evaluation task triggered at {datetime.now(timezone.utc)}")
        try:
            await self.run_weekly_evaluation_cycle()
        except Exception as e:
            print(f"[ERROR] Weekly evaluation task failed: {e}")
            import traceback
            traceback.print_exc()

    @tasks.loop(seconds=60)
    async def server_status_updater(self):
        """Update server status message and channel names every 60 seconds"""
        if not self.server_status_message_id or not self.server_status_channel_id:
            return
        
        try:
            # Add small delay to avoid conflicts with cleanup task
            await asyncio.sleep(2)
            await self.update_server_status()
        except Exception as e:
            print(f"[ERROR] Server status update failed: {e}")
            import traceback
            traceback.print_exc()

    async def run_weekly_evaluation_cycle(self):
        next_friday = self.utils.get_next_friday_16_00()
        now = datetime.now(timezone.utc)
        time_to_sleep = (next_friday - now).total_seconds()
        
        if time_to_sleep > 0:
            await asyncio.sleep(time_to_sleep)
        
        try:
            await self.utils.process_weekly_evaluation()
        except Exception as e:
            print(f"[ERROR] Evaluation cycle failed: {e}")
            import traceback
            traceback.print_exc()

    async def update_server_status(self):
        """Update the server status message and channel names"""
        try:
            # Run cleanup first to remove inactive servers
            try:
                from database import cleanup_inactive_servers
                inactive_count = cleanup_inactive_servers()
                if inactive_count > 0:
                    print(f"Cleaned up {inactive_count} inactive servers")
            except Exception as e:
                print(f"Cleanup error: {e}")
            
            # Get player data from database
            try:
                player_data = get_all_server_player_counts()
                active_server_count = get_active_server_count()
            except Exception as e:
                print(f"Database error: {e}")
                return
            
            # Organize data by server and ward
            servers = {}
            total_patients = 0
            total_staff = 0
            
            for row in player_data:
                job_id = row[0]
                registered_at = row[1]
                last_ping = row[2]
                player_type = row[3]
                ward_name = row[4]
                count = row[5]
                updated_at = row[6]
                
                if job_id not in servers:
                    servers[job_id] = {
                        "job_id": job_id,
                        "registered_at": registered_at,
                        "last_ping": last_ping,
                        "wards": {}
                    }
                
                if player_type and count is not None and ward_name:
                    if ward_name not in servers[job_id]["wards"]:
                        servers[job_id]["wards"][ward_name] = {"patients": 0, "staff": 0}
                    
                    if player_type == "patient":
                        servers[job_id]["wards"][ward_name]["patients"] = count
                        total_patients += count
                    elif player_type == "staff":
                        servers[job_id]["wards"][ward_name]["staff"] = count
                        total_staff += count
            
            # Build embed
            embed = discord.Embed(
                title="Ward Status",
                description="UPDATED EVERY 60 SECONDS",
                color=0x2b6cb0,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Active Wards", value=str(active_server_count), inline=True)
            embed.add_field(name="Total Patients", value=str(total_patients), inline=True)
            embed.add_field(name="Total Staff", value=str(total_staff), inline=True)
            
            ward_lines = []
            for server_id, server_data in servers.items():
                for ward_name, ward_data in server_data["wards"].items():
                    staff_count = ward_data["staff"]
                    patient_count = ward_data["patients"]
                    ward_lines.append(f"{ward_name} - 🩺 Patients: {patient_count} | 🔑 Staff: {staff_count}")
            
            if ward_lines:
                joined = "\n".join(ward_lines)
                if len(joined) > 1024:
                    joined = joined[:1000] + "\n…"
                embed.add_field(name="Wards", value=joined, inline=False)
            else:
                embed.add_field(name="Wards", value="No active servers", inline=False)
            
            # Update the message
            try:
                channel = self.bot.get_channel(self.server_status_channel_id)
                print(f"DEBUG: Channel found: {channel is not None}")
                print(f"DEBUG: Message ID: {self.server_status_message_id}")
                
                if channel and self.server_status_message_id:
                    try:
                        message = await channel.fetch_message(self.server_status_message_id)
                        print(f"DEBUG: Message found: {message is not None}")
                        print(f"DEBUG: Message author: {message.author}")
                        print(f"DEBUG: Bot user: {self.bot.user}")
                        print(f"DEBUG: Can edit: {message.author == self.bot.user}")
                        
                        await message.edit(content=None, embed=embed)
                        self.server_status_message_is_embed = True
                        print("DEBUG: Message edited successfully")
                    except discord.NotFound:
                        print("ERROR: Server status message not found")
                    except discord.Forbidden as e:
                        print(f"ERROR: Forbidden to edit message: {e}")
                    except Exception as e:
                        print(f"ERROR: Other error editing message: {e}")
                else:
                    print("ERROR: Missing channel or message ID")
            except Exception as e:
                print(f"ERROR: General error updating server status message: {e}")
            
            # Update channel names
            try:
                print(f"DEBUG: Updating channel names - Patients: {total_patients}, Staff: {total_staff}")
                
                # Update patient channel name
                patient_channel = self.bot.get_channel(self.patient_channel_id)
                if patient_channel:
                    new_name = f"🩺 IN-GAME PATIENTS: {total_patients}"
                    print(f"DEBUG: Patient channel current name: {patient_channel.name}")
                    print(f"DEBUG: Patient channel new name: {new_name}")
                    if patient_channel.name != new_name:
                        await patient_channel.edit(name=new_name)
                        print("DEBUG: Patient channel name updated")
                    else:
                        print("DEBUG: Patient channel name unchanged")
                else:
                    print("ERROR: Patient channel not found")
                
                # Update staff channel name
                staff_channel = self.bot.get_channel(self.staff_channel_id)
                if staff_channel:
                    new_name = f"🔑 IN-GAME STAFF: {total_staff}"
                    print(f"DEBUG: Staff channel current name: {staff_channel.name}")
                    print(f"DEBUG: Staff channel new name: {new_name}")
                    if staff_channel.name != new_name:
                        await staff_channel.edit(name=new_name)
                        print("DEBUG: Staff channel name updated")
                    else:
                        print("DEBUG: Staff channel name unchanged")
                else:
                    print("ERROR: Staff channel not found")
                        
            except Exception as e:
                print(f"Error updating channel names: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"Error in update_server_status: {e}")
            import traceback
            traceback.print_exc()

    @app_commands.command(name="evaluatenow")
    @yurstile_only()
    async def evaluatenow(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            await self.utils.process_weekly_evaluation()
            
            await interaction.followup.send(
                "✅ Weekly evaluation completed successfully!",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Error in evaluatenow: {e}")
            await interaction.followup.send(f"Error running evaluation: {str(e)}", ephemeral=True)

    @app_commands.command(name="resetscoresnow")
    @yurstile_only()
    async def resetscoresnow(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            await self.utils.reset_weekly_scores()
            
            await interaction.followup.send(
                "✅ Weekly scores reset successfully!",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Error in resetscoresnow: {e}")
            await interaction.followup.send(f"Error resetting scores: {str(e)}", ephemeral=True)

    @app_commands.command(name="addexcellencescore")
    @app_commands.describe(roblox_user_id="Roblox User ID", score="Excellence score to add")
    @yurstile_only()
    async def addexcellencescore(self, interaction: discord.Interaction, roblox_user_id: str, score: int):
        try:
            await interaction.response.defer(ephemeral=True)
            
            from database import increment_excellence_score
            
            increment_excellence_score(roblox_user_id, score)
            
            await interaction.followup.send(
                f"✅ Added {score} excellence score to user {roblox_user_id}",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Error in addexcellencescore: {e}")
            await interaction.followup.send(f"Error adding excellence score: {str(e)}", ephemeral=True)


    @app_commands.command(name="serverstatus", description="...")
    @yurstile_only()
    async def serverstatus_slash(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=False)
            self.server_status_channel_id = interaction.channel.id
            
            embed = discord.Embed(
                title="Server Status",
                description="Live player counts across active wards",
                color=0x2b6cb0,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Active Wards", value="0", inline=True)
            embed.add_field(name="Total Patients", value="0", inline=True)
            embed.add_field(name="Total Staff", value="0", inline=True)
            embed.add_field(name="Wards", value="No active servers with player data", inline=False)
            
            message = await interaction.followup.send(embed=embed, wait=True)
            self.server_status_message_id = message.id
            self.server_status_message_is_embed = True
            
            if not self.server_status_updater.is_running():
                self.server_status_updater.start()
        except Exception as e:
            await interaction.followup.send(f"❌ Error starting server status: {str(e)}", ephemeral=True)

    @app_commands.command(name="addevaluationweekscore")
    @app_commands.describe(roblox_user_id="Roblox User ID", score="Evaluation week score to add")
    @yurstile_only()
    async def addevaluationweekscore(self, interaction: discord.Interaction, roblox_user_id: str, score: int):
        try:
            await interaction.response.defer(ephemeral=True)
            
            from database import increment_evaluation_week_score
            
            increment_evaluation_week_score(roblox_user_id, score)
            
            await interaction.followup.send(
                f"✅ Added {score} evaluation week score to user {roblox_user_id}",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Error in addevaluationweekscore: {e}")
            await interaction.followup.send(f"Error adding evaluation week score: {str(e)}", ephemeral=True)

    @app_commands.command(name="addexcellence", description="Add excellence points to a staff member's record")
    @app_commands.describe(user_identifier="Roblox username, Roblox User ID, or Discord ID", points="Excellence points to add (1-5)")
    @hr_plus_only()
    async def addexcellence(self, interaction: discord.Interaction, user_identifier: str, points: int):
        try:
            await interaction.response.defer(ephemeral=True)
            
            if points < 1 or points > 5:
                await interaction.followup.send("❌ Excellence points must be between 1 and 5", ephemeral=True)
                return
            
            staff_member = await self.utils.get_staff_member_by_identifier(user_identifier)
            
            if not staff_member:
                await interaction.followup.send("❌ Staff member not found", ephemeral=True)
                return
            
            roblox_user_id, roblox_username, discord_user_id, current_excellences, evaluation = staff_member
            
            new_excellences = min(current_excellences + points, 5)
            should_mark_evaluation = new_excellences >= 5 and not evaluation
            
            success = await self.utils.update_excellence_points(
                roblox_user_id, new_excellences, should_mark_evaluation, 
                discord_user_id, current_excellences
            )
            
            if success:
                evaluation_status = " (marked for evaluation)" if should_mark_evaluation else ""
                await interaction.followup.send(
                    f"✅ Added {points} excellence points to {roblox_username}\n"
                    f"Total excellence points: {new_excellences}/5{evaluation_status}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send("❌ Error updating excellence points", ephemeral=True)
            
        except Exception as e:
            print(f"Error in addexcellence: {e}")
            await interaction.followup.send(f"Error adding excellence points: {str(e)}", ephemeral=True)

    @app_commands.command(name="removeexcellence", description="Remove excellence points from a staff member's record")
    @app_commands.describe(user_identifier="Roblox username, Roblox User ID, or Discord ID", points="Excellence points to remove (1-5)")
    @hr_plus_only()
    async def removeexcellence(self, interaction: discord.Interaction, user_identifier: str, points: int):
        try:
            await interaction.response.defer(ephemeral=True)
            
            if points < 1 or points > 5:
                await interaction.followup.send("❌ Excellence points must be between 1 and 5", ephemeral=True)
                return
            
            staff_member = await self.utils.get_staff_member_by_identifier(user_identifier)
            
            if not staff_member:
                await interaction.followup.send("❌ Staff member not found", ephemeral=True)
                return
            
            roblox_user_id, roblox_username, discord_user_id, current_excellences, evaluation = staff_member
            
            new_excellences = max(current_excellences - points, 0)
            should_unmark_evaluation = new_excellences < 5 and evaluation
            
            success = await self.utils.update_excellence_points(
                roblox_user_id, new_excellences, not should_unmark_evaluation, 
                discord_user_id, current_excellences
            )
            
            if success:
                evaluation_status = " (unmarked from evaluation)" if should_unmark_evaluation else ""
                await interaction.followup.send(
                    f"✅ Removed {points} excellence points from {roblox_username}\n"
                    f"Total excellence points: {new_excellences}/5{evaluation_status}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send("❌ Error updating excellence points", ephemeral=True)
            
        except Exception as e:
            print(f"Error in removeexcellence: {e}")
            await interaction.followup.send(f"Error removing excellence points: {str(e)}", ephemeral=True)

    @app_commands.command(name="staffreport", description="Generate a detailed report for a specific staff member")
    @app_commands.describe(user_identifier="Roblox username, Roblox User ID, or Discord ID")
    @hr_plus_only()
    async def staffreport(self, interaction: discord.Interaction, user_identifier: str):
        try:
            await interaction.response.defer(ephemeral=True)
            
            staff_member = await self.utils.get_staff_member_detailed(user_identifier)
            
            if not staff_member:
                await interaction.followup.send("❌ Staff member not found", ephemeral=True)
                return
            
            roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at = staff_member
            
            current_rank_name = self.utils.get_rank_name_by_roblox_role_id(roblox_role_id)
            
            embed = discord.Embed(
                title=f"Staff Report - {roblox_username}",
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(
                name="Basic Information",
                value=f"**Roblox ID:** {roblox_user_id}\n"
                      f"**Discord ID:** {discord_user_id or 'Not linked'}\n"
                      f"**Current Rank:** {current_rank_name}\n"
                      f"**Category:** {category}",
                inline=False
            )
            
            embed.add_field(
                name="Excellence System",
                value=f"**Excellence Points:** {excellences}/5\n"
                      f"**Evaluation Status:** {'✅ Marked' if evaluation else '❌ Not marked'}\n"
                      f"**Weekly Excellence Score:** {excellence_score}",
                inline=True
            )
            
            embed.add_field(
                name="Performance Tracking",
                value=f"**Bad Streak:** {bad_streak}\n"
                      f"**Minimum Achieved Streak:** {minimum_streak}\n"
                      f"**Evaluation Week Score:** {evaluation_week_score}\n",
                inline=True
            )
            
            embed.add_field(
                name="Account Information",
                value=f"**Joined Staff:** {created_at}",
                inline=False
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Error in staffreport: {e}")
            await interaction.followup.send(f"Error generating staff report: {str(e)}", ephemeral=True)

    @app_commands.command(name="weekreport", description="Generate a comprehensive weekly report for all staff members")
    @hr_plus_only()
    async def weekreport(self, interaction: discord.Interaction, page: int = 1):
        try:
            await interaction.response.defer(ephemeral=True)
            
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at
                FROM staff
                ORDER BY roblox_username
            ''')
            
            all_staff = cursor.fetchall()
            conn.close()
            
            demotions = []
            promotions = []
            excellence_earnings = []
            
            excellence_emojis = {
                1: "<:1_Excellence_Point:1405303696975200297>",
                2: "<:2_Excellence_Points:1405303760531624098>",
                3: "<:3_Excellence_Points:1405303839191597167>",
                4: "<:4_Excellence_Points:1405303885631062048>",
                5: "<:5_Excellence_Points:1405303933366304929>"
            }
            
            for staff in all_staff:
                roblox_user_id = staff[0]
                roblox_username = staff[1]
                discord_user_id = staff[2]
                excellences = staff[3]
                evaluation = staff[4]
                roblox_role_id = staff[5]
                category = staff[6]
                bad_streak = staff[9]
                evaluation_week_score = staff[11]
                excellence_score = staff[8]
                
                current_rank_name = self.utils.get_rank_name_by_roblox_role_id(roblox_role_id)
                
                if current_rank_name == "undocumented":
                    continue
                
                if bad_streak >= 3:
                    next_rank_name = self.utils.get_demotion_rank(current_rank_name)
                    if next_rank_name:
                        demotions.append({
                            'username': roblox_username,
                            'current_rank': current_rank_name,
                            'next_rank': next_rank_name
                        })
                
                if excellences >= 6:
                    next_rank_name = self.utils.get_promotion_rank(current_rank_name)
                    if next_rank_name:
                        promotions.append({
                            'username': roblox_username,
                            'current_rank': current_rank_name,
                            'next_rank': next_rank_name
                        })
                
                if excellence_score > 0:
                    earned_points = 0
                    if excellence_score >= 400:
                        earned_points = 5
                    elif excellence_score >= 350:
                        earned_points = 4
                    elif excellence_score >= 300:
                        earned_points = 3
                    elif excellence_score >= 200:
                        earned_points = 2
                    elif excellence_score >= 100:
                        earned_points = 1
                    
                    if earned_points > 0:
                        emoji = excellence_emojis.get(earned_points, "")
                        new_excellences = min(excellences + earned_points, 5)
                        excellence_earnings.append({
                            'username': roblox_username,
                            'earned_points': earned_points,
                            'emoji': emoji,
                            'current_excellences': excellences,
                            'new_excellences': new_excellences
                        })
            
            items_per_page = 20
            total_items = len(demotions) + len(promotions) + len(excellence_earnings)
            total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
            
            if page < 1 or page > total_pages:
                page = 1
            
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            
            all_changes = demotions + promotions + excellence_earnings
            page_items = all_changes[start_idx:end_idx]
            
            embed = discord.Embed(
                title="Weekly Report",
                description=f"Showing page {page}/{total_pages}",
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            
            if not page_items:
                embed.add_field(
                    name="No Changes",
                    value="No promotions, demotions, or excellence earnings this week.",
                    inline=False
                )
            else:
                demotion_text = ""
                promotion_text = ""
                excellence_text = ""
                
                for item in page_items:
                    if item in demotions:
                        demotion_text += f"**{item['username']}**: {item['current_rank']} → {item['next_rank']}\n"
                    elif item in promotions:
                        promotion_text += f"**{item['username']}**: {item['current_rank']} → {item['next_rank']}\n"
                    elif item in excellence_earnings:
                        excellence_text += f"**{item['username']}**: {item['emoji']} {item['current_excellences']} → {item['new_excellences']} Excellence Points\n"
                
                if demotion_text:
                    embed.add_field(
                        name="Demotions",
                        value=demotion_text,
                        inline=False
                    )
                
                if promotion_text:
                    embed.add_field(
                        name="Promotions",
                        value=promotion_text,
                        inline=False
                    )
                
                if excellence_text:
                    embed.add_field(
                        name="Excellence Earnings",
                        value=excellence_text,
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"Error in weekreport: {e}")
            await interaction.followup.send(f"Error generating report: {str(e)}", ephemeral=True)

    @app_commands.command(name="deletestaff", description="Delete a staff member from the database (YURSTILE ONLY)")
    @app_commands.describe(user_identifier="Roblox username, Roblox User ID, or Discord ID")
    @yurstile_only()
    async def deletestaff(self, interaction: discord.Interaction, user_identifier: str):
        try:
            await interaction.response.defer(ephemeral=True)
            
            staff_member = await self.utils.get_staff_member_detailed(user_identifier)
            
            if not staff_member:
                await interaction.followup.send("❌ Staff member not found in database", ephemeral=True)
                return
            
            roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at = staff_member
            
            from database import remove_staff_member
            remove_staff_member(roblox_user_id)
            
            await interaction.followup.send(
                f"✅ Successfully deleted {roblox_username} (ID: {roblox_user_id}) from staff database",
                ephemeral=True
            )
            
        except Exception as e:
            print(f"Error in deletestaff: {e}")
            await interaction.followup.send(f"Error deleting staff member: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(WeeklyEvaluation(bot))
