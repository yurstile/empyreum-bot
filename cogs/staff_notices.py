import discord
from discord.ext import commands, tasks
from discord import app_commands
import re
import sqlite3
from datetime import datetime, timezone, timedelta
from database import (
    get_staff_member, remove_staff_member, add_verified_user,
    get_role_by_name, add_staff_to_inactivity, get_staff_inactivity_by_roblox_id,
    get_staff_inactivity_by_discord_id, get_all_inactive_staff,
    remove_staff_from_inactivity, can_submit_inactivity_request,
    add_staff_member, update_staff_role, restore_staff_member_from_inactivity,
    update_staff_username, get_staff_by_discord_id
)
from .staff_notices_utils import StaffNoticesUtils

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

def only_staff():
    async def predicate(interaction: discord.Interaction):
        hr_plus_role_ids = [
            943124878834425866,
        ]
        
        user_roles = [role.id for role in interaction.user.roles]
        has_hr_plus = any(role_id in user_roles for role_id in hr_plus_role_ids)
        
        if not has_hr_plus:
            await interaction.response.send_message(
                "❌ You need to be a staff member to use this command!", 
                ephemeral=True
            )
            return False
        
        return True
    
    return app_commands.check(predicate)

class StaffNotices(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.utils = StaffNoticesUtils(bot)
        self.inactivity_checker.start()

    def cog_unload(self):
        self.inactivity_checker.cancel()

    @tasks.loop(seconds=60)
    async def inactivity_checker(self):
        try:
            print(f"[DEBUG] Inactivity checker running at {datetime.now(timezone.utc)}")
            await self.check_inactivity_dates()
        except Exception as e:
            print(f"Error in inactivity checker: {e}")

    async def check_inactivity_dates(self):
        try:
            inactive_staff = get_all_inactive_staff()
            current_time = datetime.now(timezone.utc)
            
            for staff in inactive_staff:
                try:
                    activity_end = staff[13] 
                    if not activity_end:
                        continue
                    
                    print(f"[DEBUG] Checking inactivity for {staff[1]}: activity_end={activity_end}, type={type(activity_end)}")
                    
                    if isinstance(activity_end, str):
                        if 'Manual inactivity for' in activity_end:
                            print(f"[DEBUG] Skipping string-based inactivity for {staff[1]}")
                            continue
                        try:
                            activity_end_dt = datetime.fromisoformat(activity_end.replace('Z', '+00:00'))
                            print(f"[DEBUG] Parsed string datetime for {staff[1]}: {activity_end_dt}")
                        except:
                            print(f"[DEBUG] Failed to parse string datetime for {staff[1]}: {activity_end}")
                            continue
                    else:
                        activity_end_dt = activity_end
                        print(f"[DEBUG] Using datetime object for {staff[1]}: {activity_end_dt}")
                    
                    print(f"[DEBUG] Comparing: current_time={current_time} >= activity_end_dt={activity_end_dt} = {current_time >= activity_end_dt}")
                    
                    if current_time >= activity_end_dt:
                        print(f"Inactivity ended for {staff[1]} - processing end_inactivity")
                        await self.end_inactivity(
                            staff[2], staff[0], staff[1], staff[3], staff[4],
                            staff[5], staff[6], staff[7], staff[8], staff[9],
                            staff[10], staff[11]
                        )
                except Exception as e:
                    print(f"Error processing inactivity record for {staff[1]}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error checking inactivity dates: {e}")

    async def start_inactivity(self, discord_user_id, roblox_user_id, roblox_username, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, reason, days=30, minutes=0):
        try:
            guild = self.bot.get_guild(941998687779954708)
            if not guild:
                print("Guild not found for inactivity start")
                return False
            
            member = await guild.fetch_member(int(discord_user_id))
            if not member:
                print(f"Member {discord_user_id} not found for inactivity start")
                return False
            
            activity_start = datetime.now(timezone.utc)
            activity_end = activity_start + timedelta(days=days, minutes=minutes)
            
            print(f"[DEBUG] Setting inactivity for {roblox_username}: start={activity_start}, end={activity_end}, duration={days}d {minutes}m")
            
            add_staff_to_inactivity(
                roblox_user_id, roblox_username, discord_user_id, excellences,
                evaluation, roblox_role_id, category, warnings, excellence_score,
                bad_streak, minimum_streak, evaluation_week_score, activity_start,
                activity_end, reason
            )
            
            remove_staff_member(roblox_user_id)
            
            inactivity_rank_id = "79840093"
            roblox_ranking_success = await self.utils.rank_roblox_user(roblox_user_id, inactivity_rank_id)
            if roblox_ranking_success:
                print(f"Successfully ranked {roblox_username} to inactivity rank on Roblox")
            else:
                print(f"Failed to rank {roblox_username} to inactivity rank on Roblox")
            
            await self.utils.change_inactivity_roles(member, is_starting_inactivity=True)
            await self.utils.send_inactivity_start_dm(member, roblox_username, reason)
            
            return True
            
        except Exception as e:
            print(f"Error starting inactivity: {e}")
            return False

    async def end_inactivity(self, discord_user_id, roblox_user_id, roblox_username, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score):
        try:
            print(f"[DEBUG] Attempting to end inactivity for {roblox_username} (Discord ID: {discord_user_id})")
            
            guild = self.bot.get_guild(941998687779954708)
            if not guild:
                print("Guild not found for inactivity end")
                return False
            
            print(f"[DEBUG] Found guild: {guild.name} (ID: {guild.id})")
            print(f"[DEBUG] Guild member count: {guild.member_count}")
            print(f"[DEBUG] Bot guilds: {[g.name for g in self.bot.guilds]}")
            print(f"[DEBUG] Bot guild IDs: {[g.id for g in self.bot.guilds]}")
            print(f"[DEBUG] Bot ready: {self.bot.is_ready()}")
            print(f"[DEBUG] Bot user: {self.bot.user}")
            print(f"[DEBUG] Bot permissions in guild: {guild.me.guild_permissions}")
            
            try:
                member = await guild.fetch_member(int(discord_user_id))
                print(f"[DEBUG] Successfully fetched member: {member.display_name} (ID: {member.id})")
            except discord.NotFound:
                print(f"[DEBUG] Member {discord_user_id} not found in guild - they may have left")
                return False
            except discord.Forbidden:
                print(f"[DEBUG] Bot doesn't have permission to fetch member {discord_user_id}")
                return False
            except Exception as e:
                print(f"[DEBUG] Error fetching member {discord_user_id}: {e}")
                return False
            
            if not member:
                print(f"Member {discord_user_id} not found for inactivity end")
                return False
            
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            cursor.execute('''
                SELECT activity_end FROM staff_inactivity
                WHERE roblox_user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (roblox_user_id,))
            result = cursor.fetchone()
            activity_end = result[0] if result else None
            conn.close()
            
            remove_staff_from_inactivity(roblox_user_id)
            
            last_inactivity_date = None
            if activity_end:
                if isinstance(activity_end, str):
                    if 'Manual inactivity for' in activity_end:
                        last_inactivity_date = int(datetime.now().timestamp())
                    else:
                        try:
                            dt = datetime.fromisoformat(activity_end.replace('Z', '+00:00'))
                            last_inactivity_date = int(dt.timestamp())
                        except:
                            last_inactivity_date = int(datetime.now().timestamp())
                else:
                    last_inactivity_date = int(datetime.now().timestamp())
            else:
                last_inactivity_date = int(datetime.now().timestamp())
            
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO staff (
                    roblox_user_id, roblox_username, discord_user_id, excellences, evaluation,
                    roblox_role_id, category, warnings, excellence_score, bad_streak,
                    minimum_streak, evaluation_week_score, last_inactivity_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (roblox_user_id, roblox_username, discord_user_id, excellences, evaluation,
                  roblox_role_id, category, warnings, excellence_score, bad_streak,
                  minimum_streak, evaluation_week_score, last_inactivity_date))
            conn.commit()
            conn.close()
            
            rank_name = self.utils.get_rank_name_by_roblox_role_id(roblox_role_id)
            original_role = get_role_by_name(rank_name)
            if original_role:
                original_role_obj = guild.get_role(int(original_role[1]))
                if original_role_obj:
                    await member.add_roles(original_role_obj)
                
                roblox_ranking_success = await self.utils.rank_roblox_user(roblox_user_id, roblox_role_id)
                if roblox_ranking_success:
                    print(f"Successfully ranked {roblox_username} back to original role {roblox_role_id} on Roblox")
                else:
                    print(f"Failed to rank {roblox_username} back to original role {roblox_role_id} on Roblox")
            
            await self.utils.change_inactivity_roles(member, is_starting_inactivity=False)
            await self.utils.restore_excellence_roles(member, excellences)
            await self.utils.send_inactivity_end_dm(member, roblox_username)
            
            return True
            
        except Exception as e:
            print(f"Error ending inactivity: {e}")
            return False

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        if message.channel.id != 947955845742854214:
            return
        
        content = message.content.lower()
        
        if await self.utils.is_resignation_notice(content):
            await self.process_resignation_notice(message)
        elif await self.utils.is_inactivity_notice(content):
            await self.process_inactivity_notice(message)

    async def process_resignation_notice(self, message):
        try:
            content = message.content
            discord_user_id = str(message.author.id)
            
            username_match = re.search(r'Username:\s*(.*?)(?:\n|$)', content, re.IGNORECASE)
            if not username_match:
                await message.add_reaction('<:e_cross:963172261391650837>')
                try:
                    await message.author.send("❌ **Resignation Notice Failed**\n\nCould not parse the username from your message. Please use the format:\n\n**Resignation Notice**\n**Username:** [your username]\n**Roblox ID:** [your roblox id]\n**Reason:** [optional reason]")
                except:
                    pass
                return
            
            username = username_match.group(1).strip()
            
            roblox_id_match = re.search(r'Roblox ID:\s*(.*?)(?:\n|$)', content, re.IGNORECASE)
            if not roblox_id_match:
                await message.add_reaction('<:e_cross:963172261391650837>')
                try:
                    await message.author.send("❌ **Resignation Notice Failed**\n\nCould not parse the Roblox ID from your message. Please use the format:\n\n**Resignation Notice**\n**Username:** [your username]\n**Roblox ID:** [your roblox id]\n**Reason:** [optional reason]")
                except:
                    pass
                return
            
            roblox_user_id = roblox_id_match.group(1).strip()
            
            reason = "Resignation"
            reason_match = re.search(r'Reason:\s*(.*?)(?:\n|$)', content, re.IGNORECASE)
            if reason_match:
                reason = reason_match.group(1).strip()
            
            user_info = await self.utils.get_user_info(discord_user_id)
            if not user_info or user_info['type'] != 'staff':
                await message.add_reaction('<:e_cross:963172261391650837>')
                try:
                    await message.author.send("❌ **Resignation Notice Failed**\n\nYou are not a staff member or your account is not properly linked. Please contact an administrator if you believe this is an error.")
                except:
                    pass
                return
            
            if user_info['roblox_user_id'] != roblox_user_id:
                await message.add_reaction('<:e_cross:963172261391650837>')
                try:
                    await message.author.send("❌ **Resignation Notice Failed**\n\nThe Roblox ID provided does not match your linked account. Please check your Roblox ID and try again.")
                except:
                    pass
                return
            
            if user_info['roblox_username'].lower() != username.lower():
                await message.add_reaction('<:e_cross:963172261391650837>')
                try:
                    await message.author.send("❌ **Resignation Notice Failed**\n\nThe username provided does not match your linked account. Please check your username and try again.")
                except:
                    pass
                return
            
            success = await self.handle_resignation(discord_user_id, roblox_user_id, username)
            
            if success:
                await message.add_reaction('<:e_check:963172261630718002>')
            else:
                await message.add_reaction('<:e_cross:963172261391650837>')
                try:
                    await message.author.send("❌ **Resignation Notice Failed**\n\nAn error occurred while processing your resignation notice. Please try again or contact an administrator.")
                except:
                    pass
            
        except Exception as e:
            print(f"Error processing resignation notice: {e}")
            await message.add_reaction('<:e_cross:963172261391650837>')
            try:
                await message.author.send("❌ **Resignation Notice Failed**\n\nAn unexpected error occurred while processing your resignation notice. Please try again or contact an administrator.")
            except:
                pass

    async def process_inactivity_notice(self, message):
        try:
            content = message.content
            username = message.author.display_name
            discord_user_id = str(message.author.id)
            
            user_info = await self.utils.get_user_info(discord_user_id)
            
            if not user_info or user_info['type'] != 'staff':
                await message.add_reaction('<:e_cross:963172261391650837>')
                try:
                    await message.author.send("❌ **Inactivity Notice Failed**\n\nYou are not a staff member or your account is not properly linked. Please contact an administrator if you believe this is an error.")
                except:
                    pass
                return
            
            roblox_user_id = user_info['roblox_user_id']
            roblox_username = user_info['roblox_username']
            
            start_date_match = re.search(r'Start Date:\s*(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))', content, re.IGNORECASE)
            end_date_match = re.search(r'End Date:\s*(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))', content, re.IGNORECASE)
            
            if start_date_match and end_date_match:
                start_date = self.utils.parse_date(start_date_match.group(1))
                end_date = self.utils.parse_date(end_date_match.group(1))
            else:
                date_pattern = r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b'
                dates = re.findall(date_pattern, content, re.IGNORECASE)
                
                if len(dates) >= 2:
                    start_date = self.utils.parse_date(dates[0])
                    end_date = self.utils.parse_date(dates[1])
                else:
                    await message.add_reaction('<:e_cross:963172261391650837>')
                    try:
                        await message.author.send("❌ **Inactivity Notice Failed**\n\nCould not parse the start and end dates from your message. Please use the format:\n\n**Inactivity Notice**\n**Username:** [your username]\n**Roblox ID:** [your roblox id]\n**Start Date:** [date]\n**End Date:** [date]")
                    except:
                        pass
                    return
            
            if start_date and end_date:
                current_time = datetime.now(timezone.utc)
                today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)
                
                if start_date < today_start or start_date >= today_end:
                    await message.add_reaction('<:e_cross:963172261391650837>')
                    try:
                        await message.author.send("❌ **Inactivity Notice Failed**\n\nStart date must be today's date. Only current date is accepted.")
                    except:
                        pass
                    return
                

                
                days = (end_date - start_date).days
                if days < 7:
                    await message.add_reaction('<:e_cross:963172261391650837>')
                    try:
                        await message.author.send(f"❌ **Inactivity Notice Failed**\n\nInactivity period must be at least 7 days. Your requested period is {days} days.")
                    except:
                        pass
                    return
                
                reason = "Inactivity notice"
                if "Reason:" in content:
                    reason_match = re.search(r'Reason:\s*(.*?)(?:\n|$)', content, re.IGNORECASE)
                    if reason_match:
                        reason = reason_match.group(1).strip()
                
                result = await self.handle_inactivity_notice(
                    discord_user_id, roblox_user_id, roblox_username,
                    start_date, end_date, reason, username
                )
                
                if result == "success":
                    await message.add_reaction('<:e_check:963172261630718002>')
                    try:
                        start_date_str = start_date.strftime("%B %d, %Y")
                        end_date_str = end_date.strftime("%B %d, %Y")
                        await message.author.send(f"✅ **Inactivity Notice Accepted**\n\n**Username:** {roblox_username}\n**Start Date:** {start_date_str}\n**End Date:** {end_date_str}\n**Duration:** {days} days\n\nYour inactivity notice has been processed successfully.")
                    except:
                        pass
                elif result == "cooldown":
                    await message.add_reaction('<:e_cross:963172261391650837>')
                else:
                    await message.add_reaction('<:e_cross:963172261391650837>')
                    try:
                        await message.author.send("❌ **Inactivity Notice Failed**\n\nAn error occurred while processing your inactivity notice. Please try again or contact an administrator.")
                    except:
                        pass
            else:
                await message.add_reaction('<:e_cross:963172261391650837>')
                try:
                    await message.author.send("❌ **Inactivity Notice Failed**\n\nCould not parse the dates from your message. Please use the format:\n\n**Inactivity Notice**\n**Username:** [your username]\n**Roblox ID:** [your roblox id]\n**Start Date:** [date]\n**End Date:** [date]")
                except:
                    pass
            
        except Exception as e:
            print(f"Error processing inactivity notice: {e}")
            import traceback
            traceback.print_exc()
            await message.add_reaction('<:e_cross:963172261391650837>')
            try:
                await message.author.send("❌ **Inactivity Notice Failed**\n\nAn unexpected error occurred while processing your inactivity notice. Please try again or contact an administrator.")
            except:
                pass

    async def handle_resignation(self, discord_user_id, roblox_user_id, username):
        try:
            guild = self.bot.get_guild(941998687779954708)
            if not guild:
                return False
            
            member = await guild.fetch_member(int(discord_user_id))
            if not member:
                return False
            
            staff = get_staff_member(roblox_user_id)
            if not staff:
                return False
            
            admittee_role = get_role_by_name("admittee")
            if not admittee_role:
                return False
            
            admittee_roblox_role_id = admittee_role[2]
            
            remove_staff_member(roblox_user_id)
            add_verified_user(discord_user_id, username, roblox_user_id)
            
            success = await self.utils.rank_roblox_user(roblox_user_id, admittee_roblox_role_id)
            if not success:
                print(f"Failed to rank {username} to admittee on Roblox")
            
            await self.utils.change_resignation_roles(member)
            await self.utils.send_resignation_dm(member, username)
            
            return True
            
        except Exception as e:
            print(f"Error handling resignation: {e}")
            return False

    async def handle_inactivity_notice(self, discord_user_id, roblox_user_id, username, start_date, end_date, reason, staff_member):
        try:
            if not can_submit_inactivity_request(discord_user_id):
                try:
                    await self.bot.get_user(int(discord_user_id)).send("❌ **Inactivity Notice Failed**\n\nYou must wait at least 14 days after your last inactivity period before submitting a new one.")
                except:
                    pass
                return "cooldown"
            
            staff = get_staff_member(roblox_user_id)
            if not staff:
                return "error"
            
            current_time = datetime.now(timezone.utc)
            today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today_start + timedelta(days=1)
            
            if start_date < today_start or start_date >= today_end:
                return "error"
        
            
            days = (end_date - start_date).days
            if days <= 0:
                return "error"
            
            inactivity_record = get_staff_inactivity_by_roblox_id(roblox_user_id)
            if inactivity_record:
                conn = sqlite3.connect('roles.db')
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE staff_inactivity
                    SET activity_start = ?, activity_end = ?, reason = ?
                    WHERE roblox_user_id = ?
                ''', (start_date, end_date, reason, roblox_user_id))
                conn.commit()
                conn.close()
                return "success"
            else:
                success = await self.start_inactivity(
                    discord_user_id, roblox_user_id, username, staff[3], staff[4],
                    staff[5], staff[6], staff[7], staff[8], staff[9], staff[10], staff[11], 
                    f"Manual inactivity for {days} days", days, 0
                )
                return "success" if success else "error"
            
        except Exception as e:
            print(f"Error handling inactivity notice: {e}")
            return "error"

    @app_commands.command(name="extendinactivity", description="Extend a staff member's current inactivity period by additional days")
    @app_commands.describe(user_identifier="Roblox username, Roblox ID, or Discord ID", days="Number of days to extend inactivity (use negative for shortening)")
    @hr_plus_only()
    async def extendinactivity(self, interaction: discord.Interaction, user_identifier: str, days: int):
        try:
            await interaction.response.defer(ephemeral=True)
            
            user_info = await self.utils.get_user_info(user_identifier)
            if not user_info:
                await interaction.followup.send("❌ User not found!", ephemeral=True)
                return
            
            roblox_user_id = user_info['roblox_user_id']
            roblox_username = user_info['roblox_username']
            
            inactivity_record = get_staff_inactivity_by_roblox_id(roblox_user_id)
            if not inactivity_record:
                await interaction.followup.send("❌ User is not on inactivity!", ephemeral=True)
                return
            
            current_activity_end = inactivity_record[13]
            if not current_activity_end:
                await interaction.followup.send("❌ Invalid inactivity record - missing activity end date!", ephemeral=True)
                return
            
            from datetime import datetime, timezone
            try:
                if isinstance(current_activity_end, str):
                    if 'Manual inactivity for' in current_activity_end:
                        await interaction.followup.send("❌ Cannot extend manual inactivity periods!", ephemeral=True)
                        return
                    current_end_dt = datetime.fromisoformat(current_activity_end.replace('Z', '+00:00'))
                else:
                    current_end_dt = datetime.fromtimestamp(current_activity_end, tz=timezone.utc)
                
                new_end_dt = current_end_dt.replace(tzinfo=timezone.utc) + timedelta(days=days)
                
                if new_end_dt <= datetime.now(timezone.utc):
                    await interaction.followup.send("❌ New inactivity end date would be in the past!", ephemeral=True)
                    return
                
                conn = sqlite3.connect('roles.db')
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE staff_inactivity
                    SET activity_end = ?
                    WHERE roblox_user_id = ?
                ''', (new_end_dt.isoformat(), roblox_user_id))
                conn.commit()
                conn.close()
                
                action = "extended" if days > 0 else "shortened"
                await interaction.followup.send(f"✅ {action.title()} inactivity for {roblox_username} by {abs(days)} days.", ephemeral=False)
                
            except ValueError as e:
                await interaction.followup.send(f"❌ Error parsing date: {str(e)}", ephemeral=True)
            except Exception as e:
                await interaction.followup.send(f"❌ Error updating inactivity: {str(e)}", ephemeral=True)
            
        except Exception as e:
            print(f"Error extending inactivity: {e}")
            await interaction.followup.send("❌ Error extending inactivity.", ephemeral=True)

    @app_commands.command(name="addinactivity", description="Add a staff member to inactivity for a specified duration [DONT USE MINUTES]")
    @app_commands.describe(user_identifier="Roblox username, Roblox ID, or Discord ID", days="Number of days for inactivity (0 for minutes only)", minutes="Number of minutes for inactivity (0 for days only)")
    @hr_plus_only()
    async def addinactivity(self, interaction: discord.Interaction, user_identifier: str, days: int = 0, minutes: int = 0):
        try:
            await interaction.response.defer(ephemeral=True)
            
            if days == 0 and minutes == 0:
                await interaction.followup.send("❌ Please specify either days or minutes (or both)!", ephemeral=True)
                return
            
            if days < 0 or minutes < 0:
                await interaction.followup.send("❌ Days and minutes must be positive numbers!", ephemeral=True)
                return
            
            user_info = await self.utils.get_user_info(user_identifier)
            if not user_info:
                await interaction.followup.send("❌ User not found!", ephemeral=True)
                return
            
            roblox_user_id = user_info['roblox_user_id']
            roblox_username = user_info['roblox_username']
            discord_user_id = user_info['discord_user_id']
            
            if user_info['type'] != 'staff':
                await interaction.followup.send("❌ User is not a staff member!", ephemeral=True)
                return
            
            staff = get_staff_member(roblox_user_id)
            if not staff:
                await interaction.followup.send("❌ Staff member not found in database!", ephemeral=True)
                return
            
            inactivity_record = get_staff_inactivity_by_roblox_id(roblox_user_id)
            if inactivity_record:
                await interaction.followup.send("❌ User is already on inactivity!", ephemeral=True)
                return
            
            duration_text = ""
            if days > 0 and minutes > 0:
                duration_text = f"Manual inactivity for {days} days and {minutes} minutes"
            elif days > 0:
                duration_text = f"Manual inactivity for {days} days"
            else:
                duration_text = f"Manual inactivity for {minutes} minutes"
            
            success = await self.start_inactivity(
                discord_user_id, roblox_user_id, roblox_username, staff[3], staff[4],
                staff[5], staff[6], staff[7], staff[8], staff[9], staff[10], staff[11], 
                duration_text, days, minutes
            )
            
            if success:
                await interaction.followup.send(f"✅ Added {roblox_username} to inactivity for {duration_text}.", ephemeral=False)
            else:
                await interaction.followup.send("❌ Failed to add user to inactivity.", ephemeral=True)
            
        except Exception as e:
            print(f"Error adding inactivity: {e}")
            await interaction.followup.send("❌ Error adding inactivity.", ephemeral=True)

    @app_commands.command(name="removeinactivity", description="Remove a staff member from inactivity and restore their previous status")
    @app_commands.describe(user_identifier="Roblox username, Roblox ID, or Discord ID")
    @hr_plus_only()
    async def removeinactivity(self, interaction: discord.Interaction, user_identifier: str):
        try:
            await interaction.response.defer(ephemeral=True)
            
            user_info = await self.utils.get_user_info(user_identifier)
            if not user_info:
                await interaction.followup.send("❌ User not found!", ephemeral=True)
                return
            roblox_user_id = user_info['roblox_user_id']
            roblox_username = user_info['roblox_username']
            discord_user_id = user_info['discord_user_id']
            
            inactivity_record = get_staff_inactivity_by_roblox_id(roblox_user_id)
            if not inactivity_record:
                await interaction.followup.send("❌ User is not on inactivity!", ephemeral=True)
                return
            success = await self.end_inactivity(
                discord_user_id, roblox_user_id, roblox_username, inactivity_record[3],
                inactivity_record[4],
                inactivity_record[5],
                inactivity_record[6],
                inactivity_record[7],
                inactivity_record[8],
                inactivity_record[9],
                inactivity_record[10],
                inactivity_record[11]
            )
            
            if success:
                await interaction.followup.send(f"✅ Removed {roblox_username} from inactivity.", ephemeral=False)
            else:
                await interaction.followup.send("❌ Failed to remove user from inactivity.", ephemeral=True)
            
        except Exception as e:
            print(f"Error removing inactivity: {e}")
            await interaction.followup.send("❌ Error removing inactivity.", ephemeral=True)

    @app_commands.command(name="changeusername", description="Update a staff member's Roblox username in the system")
    @app_commands.describe(olduser="Roblox username, Roblox ID, or Discord ID", newuser="New Roblox username")
    @hr_plus_only()
    async def changeusername(self, interaction: discord.Interaction, olduser: str, newuser: str):
        try:
            await interaction.response.defer(ephemeral=True)
            
            user_info = await self.utils.get_user_info(olduser)
            if not user_info:
                await interaction.followup.send("❌ User not found!", ephemeral=True)
                return
            
            roblox_user_id = user_info['roblox_user_id']
            roblox_username = user_info['roblox_username']
            discord_user_id = user_info['discord_user_id']
            
            if user_info['type'] != 'staff':
                await interaction.followup.send("❌ User is not a staff member!", ephemeral=True)
                return
            
            if not re.match(r'^[a-zA-Z0-9_]{3,20}$', newuser):
                await interaction.followup.send("❌ New username must be between 3 and 20 characters and can only contain letters, numbers, and underscores.", ephemeral=True)
                return
            
            update_staff_username(roblox_user_id, newuser)
            
            await interaction.followup.send(f"✅ Changed {roblox_username}'s username to `{newuser}`.", ephemeral=False)
            
        except Exception as e:
            print(f"Error changing username: {e}")
            await interaction.followup.send("❌ Error changing username.", ephemeral=True)

    @app_commands.command(name="mystatus", description="Check your current bad streak status")
    @only_staff()
    async def mystatus(self, interaction: discord.Interaction):
        try:
            discord_user_id = str(interaction.user.id)
            staff_member = get_staff_by_discord_id(discord_user_id)
            
            if not staff_member:
                await interaction.response.send_message("❌ You are not registered as a staff member in the system.", ephemeral=True)
                return
            
            bad_streak = staff_member[9]
            
            if bad_streak == 0:
                message = f"Your current bad streak is **{bad_streak}** in weeks.\nYou're currently **not** under risk of a demotion, keep it up!"
            elif bad_streak == 1:
                message = f"Your current bad streak is **{bad_streak}** in weeks.\nYou're currently **not** under risk of a demotion, however, you may be subject to demotion if you don't reduce your bad streak."
            elif bad_streak == 2:
                message = f"Your current bad streak is **{bad_streak}** in weeks.\nYou're currently **under** risk of a demotion, if you have a proper reason then reach out to any HR."
            else:
                message = f"Your current bad streak is **{bad_streak}** in weeks.\nYou're currently **under** risk of a demotion, if you have a proper reason then reach out to any HR."
            
            await interaction.response.send_message(message, ephemeral=True)
            
        except Exception as e:
            print(f"Error checking mystatus: {e}")
            await interaction.response.send_message("❌ Error checking your status.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(StaffNotices(bot))
