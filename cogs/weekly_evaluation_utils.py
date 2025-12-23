import discord
import sqlite3
from datetime import datetime, timezone, timedelta
from database import (
    get_all_staff, update_staff_role, get_role_by_name, RANK_HIERARCHY,
    increment_excellence_score, increment_bad_streak, increment_minimum_streak,
    reset_bad_streak, reset_all_evaluation_week_scores, update_staff_role
)
from .shared_utils import SharedUtils

class WeeklyEvaluationUtils(SharedUtils):
    def __init__(self, bot):
        super().__init__(bot)

    def get_next_friday_16_00(self):
        now = datetime.now(timezone.utc)
        
        days_until_friday = (4 - now.weekday()) % 7
        if days_until_friday == 0 and now.hour >= 16:
            days_until_friday = 7
        
        target_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
        if days_until_friday > 0:
            target_time += timedelta(days=days_until_friday)
        
        return target_time

    def get_next_friday_16_00(self):
        now = datetime.now(timezone.utc)
        
        days_until_friday = (4 - now.weekday()) % 7
        if days_until_friday == 0 and now.hour >= 16:
            days_until_friday = 7
        
        target_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
        if days_until_friday > 0:
            target_time += timedelta(days=days_until_friday)
        
        return target_time

    async def process_weekly_evaluation(self):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at
                FROM staff
            ''')
            
            staff_members = cursor.fetchall()
            newly_marked_users = set()
            
            for staff in staff_members:
                roblox_user_id = staff[0]
                roblox_username = staff[1]
                discord_user_id = staff[2]
                current_excellences = staff[3]
                evaluation = staff[4]
                excellence_score = staff[8]
                bad_streak = staff[9]
                minimum_streak = staff[10]
                roblox_role_id = staff[5]
                category = staff[6]
                
                current_rank_name = self.get_rank_name_by_roblox_role_id(roblox_role_id)
                
                if current_rank_name == "undocumented":
                    continue
                
                if current_rank_name == "lecturer":
                    cursor.execute('''
                        UPDATE staff 
                        SET excellence_score = 0, evaluation_week_score = 0
                        WHERE roblox_user_id = ?
                    ''', (roblox_user_id,))
                    conn.commit()
                    continue
                
                if current_excellences >= 5 and not evaluation:
                    cursor.execute('UPDATE staff SET evaluation = TRUE WHERE roblox_user_id = ?', (roblox_user_id,))
                    newly_marked_users.add(roblox_user_id)
                    conn.commit()
                
                if evaluation:
                    cursor.execute('''
                        UPDATE staff 
                        SET evaluation_week_score = 0
                        WHERE roblox_user_id = ?
                    ''', (roblox_user_id,))
                    conn.commit()
                
                new_excellence_points = 0
                new_bad_streak = bad_streak
                new_minimum_streak = minimum_streak
                
                if excellence_score >= 400:
                    new_excellence_points = 5
                    if new_bad_streak > 0:
                        new_minimum_streak += 1
                elif excellence_score >= 350:
                    new_excellence_points = 4
                    if new_bad_streak > 0:
                        new_minimum_streak += 1
                elif excellence_score >= 300:
                    new_excellence_points = 3
                    if new_bad_streak > 0:
                        new_minimum_streak += 1
                elif excellence_score >= 200:
                    new_excellence_points = 2
                    if new_bad_streak > 0:
                        new_minimum_streak += 1
                elif excellence_score >= 100:
                    new_excellence_points = 1
                    if new_bad_streak > 0:
                        new_minimum_streak += 1
                elif excellence_score >= 50:
                    new_excellence_points = 0
                    new_minimum_streak += 1
                else:
                    new_bad_streak += 1
                
                if new_minimum_streak >= 2:
                    if new_bad_streak > 0:
                        new_bad_streak = 0
                        new_minimum_streak = 0
                    else:
                        new_minimum_streak = 0
                
                if new_excellence_points > 0:
                    total_excellences = min(current_excellences + new_excellence_points, 5)
                    should_mark_evaluation = total_excellences >= 5 and not current_excellences >= 5
                    
                    cursor.execute('''
                        UPDATE staff 
                        SET excellences = ?, bad_streak = ?, minimum_streak = ?
                        WHERE roblox_user_id = ?
                    ''', (total_excellences, new_bad_streak, new_minimum_streak, roblox_user_id))
                    
                    if should_mark_evaluation:
                        cursor.execute('UPDATE staff SET evaluation = TRUE WHERE roblox_user_id = ?', (roblox_user_id,))
                        newly_marked_users.add(roblox_user_id)

                    conn.commit()
                    
                    if discord_user_id:
                        await self.update_discord_excellence_roles(discord_user_id, current_excellences, total_excellences)
                else:
                    cursor.execute('''
                        UPDATE staff 
                        SET bad_streak = ?, minimum_streak = ?
                        WHERE roblox_user_id = ?
                    ''', (new_bad_streak, new_minimum_streak, roblox_user_id))
                    conn.commit()
            
            conn.commit()
            
            await self.handle_failed_evaluations(newly_marked_users)
            
            conn.close()
            
            await self.send_evaluation_completion_message()
            await self.reset_weekly_scores()
            
        except Exception as e:
            print(f"[ERROR] Error in weekly evaluation: {e}")
            import traceback
            traceback.print_exc()
            if 'conn' in locals():
                conn.close()

    async def handle_failed_evaluations(self, newly_marked_users=None):
        if newly_marked_users is None:
            newly_marked_users = set()
            
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation_week_score
                FROM staff
                WHERE evaluation = TRUE
            ''')
            
            evaluation_staff = cursor.fetchall()
            
            for staff in evaluation_staff:
                roblox_user_id = staff[0]
                roblox_username = staff[1]
                discord_user_id = staff[2]
                current_excellences = staff[3]
                evaluation_week_score = staff[4]
                
                if roblox_user_id in newly_marked_users:
                    continue
                
                if evaluation_week_score < 50:
                    cursor.execute('''
                        UPDATE staff 
                        SET evaluation = FALSE, excellences = 0, evaluation_week_score = 0
                        WHERE roblox_user_id = ?
                    ''', (roblox_user_id,))
                    
                    if discord_user_id:
                        await self.update_discord_excellence_roles(discord_user_id, current_excellences, 0)
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error handling failed evaluations: {e}")
            if 'conn' in locals():
                conn.close()

    async def update_discord_excellence_roles(self, discord_user_id, old_excellences, new_excellences):
        try:
            guild = self.bot.get_guild(941998687779954708)
            if not guild:
                print("Guild not found for excellence role update")
                return
            
            member = await guild.fetch_member(int(discord_user_id))
            if not member:
                print(f"Member {discord_user_id} not found for excellence role update")
                return
            
            excellence_role_ids = {
                1: 1401232544611176528,
                2: 1401235996380627057,
                3: 1401236077796266146,
                4: 1401236156779073678,
                5: 1401236230477185034
            }
            
            roles_to_remove = []
            roles_to_add = []
            
            for excellence_level, role_id in excellence_role_ids.items():
                role = guild.get_role(role_id)
                if role:
                    if excellence_level <= old_excellences and role in member.roles:
                        roles_to_remove.append(role)
            
            if new_excellences > 0:
                highest_role_id = excellence_role_ids.get(new_excellences)
                if highest_role_id:
                    highest_role = guild.get_role(highest_role_id)
                    if highest_role:
                        if highest_role not in member.roles:
                            roles_to_add.append(highest_role)
            
            for role in roles_to_remove:
                try:
                    await member.remove_roles(role)
                except Exception as e:
                    print(f"Error removing excellence role {role.name}: {e}")
            
            for role in roles_to_add:
                try:
                    await member.add_roles(role)
                except Exception as e:
                    print(f"Error adding excellence role {role.name}: {e}")
                    
        except Exception as e:
            print(f"Error updating Discord excellence roles: {e}")
            import traceback
            traceback.print_exc()

    async def sync_excellence_roles_for_member(self, discord_user_id):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT excellences FROM staff WHERE discord_user_id = ?
            ''', (discord_user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                excellences = result[0]
                await self.update_discord_excellence_roles(discord_user_id, 0, excellences)
                return True
            return False
            
        except Exception as e:
            print(f"Error syncing excellence roles for member {discord_user_id}: {e}")
            return False

    async def reset_weekly_scores(self):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE staff 
                SET excellence_score = 0, evaluation_week_score = 0
                WHERE roblox_role_id != '80133700'
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Error resetting weekly scores: {e}")

    async def send_evaluation_completion_message(self):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT roblox_username, excellences, roblox_role_id, excellence_score
                FROM staff
                WHERE excellence_score > 0 AND roblox_role_id != '80133700'
                ORDER BY 
                    CASE roblox_role_id
                        WHEN '81474749' THEN 1
                        WHEN '79840232' THEN 2
                        WHEN '79840296' THEN 3
                        WHEN '79840262' THEN 4
                        WHEN '80133627' THEN 5
                        ELSE 6
                    END,
                    roblox_username
            ''')
            
            staff_with_excellences = cursor.fetchall()
            conn.close()
            
            if not staff_with_excellences:
                return
            
            excellence_emojis = {
                1: "<:1_Excellence_Point:1405303696975200297>",
                2: "<:2_Excellence_Points:1405303760531624098>",
                3: "<:3_Excellence_Points:1405303839191597167>",
                4: "<:4_Excellence_Points:1405303885631062048>",
                5: "<:5_Excellence_Points:1405303933366304929>"
            }
            
            rank_categories = {
                "81474749": "🗝️ Clinic Noviciate",
                "79840232": "🗝️ Clinic Attendant", 
                "79840296": "🗝️ Clinic Warden",
                "79840262": "🗝️ Clinic Custodian",
                "80133627": "🕊️ Clinic Concierge"
            }
            
            rank_order = {
                "81474749": 1,
                "79840232": 2,
                "79840296": 3,
                "79840262": 4,
                "80133627": 5
            }
            
            worthy_members = []
            for username, excellences, roblox_role_id, excellence_score in staff_with_excellences:
                if excellence_score <= 0:
                    continue
                
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
                    worthy_members.append((username, excellences, roblox_role_id, excellence_score, earned_points))
            
            if not worthy_members:
                message_parts = [
                    "# ︶✧︶𝑀𝒶𝒾𝒹 𝑅𝑒𝒻𝑜𝓇𝓂𝓈 + ˚₊︶✧︶₊⊹ #",
                    "",
                    "Another week has passed, but it seems like I can't find anyone worthy of earning such prestige excellence points! Maybe next time...",
                    "",
                    "{ <@&942445410381873222> }"
                ]
            else:
                message_parts = [
                    "# ︶✧︶𝑀𝒶𝒾𝒹 𝑅𝑒𝒻𝑜𝓇𝓂𝓈 + ˚₊︶✧︶₊⊹ #",
                    "Ah! Another week has passed, and your hard work has not gone unnoticed, and the following individuals have earned their prestigious excellence points!\n"
                ]
                
                current_category = None
                category_members = []
                
                for username, excellences, roblox_role_id, excellence_score, earned_points in worthy_members:
                    category_name = rank_categories.get(roblox_role_id, "🗝️ Other Staff")
                    
                    if category_name != current_category:
                        if category_members:
                            message_parts.append(f"## {current_category} ##\n")
                            message_parts.extend(category_members)
                            message_parts.append("")
                        
                        current_category = category_name
                        category_members = []
                    
                    emoji = excellence_emojis.get(earned_points, "")
                    category_members.append(f"{username} - {emoji} {earned_points} Excellence Points")
                
                if category_members:
                    message_parts.append(f"## {current_category} ##\n")
                    message_parts.extend(category_members)
                    message_parts.append("")
                
                message_parts.extend([
                    "︶✧︶˚₊︶✧︶₊︶✧︶˚₊︶✧︶₊︶✧︶˚₊︶✧︶₊",
                    "",
                    "Congratulations once more, may your excellence points continue guiding you on your prestigious path!",
                    "",
                    "{ <@&942445410381873222> }"
                ])
            
            channel = self.bot.get_channel(942577578391257208)
            if channel:
                await channel.send("\n".join(message_parts))
                
        except Exception as e:
            print(f"Error sending evaluation completion message: {e}")

    def get_rank_name_by_roblox_role_id(self, roblox_role_id):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM roles WHERE roblox_role_id = ?', (roblox_role_id,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else "Unknown"
        except Exception as e:
            print(f"Error getting rank name: {e}")
            return "Unknown"

    def get_demotion_rank(self, current_rank_name):
        try:
            if current_rank_name == "undocumented":
                return "admittee"
            elif current_rank_name in ["concierge", "lecturer"]:
                return "custodian"
            else:
                return "admittee"
        except Exception as e:
            print(f"Error getting demotion rank: {e}")
            return None

    def get_promotion_rank(self, current_rank_name):
        try:
            current_index = RANK_HIERARCHY.index(current_rank_name.lower())
            if current_index < len(RANK_HIERARCHY) - 1:
                return RANK_HIERARCHY[current_index + 1]
            return None
        except ValueError:
            return None

    async def get_staff_member_by_identifier(self, user_identifier):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            
            staff_member = None
            
            if user_identifier.isdigit():
                if len(user_identifier) == 18:
                    cursor.execute('''
                        SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation
                        FROM staff
                        WHERE discord_user_id = ?
                    ''', (user_identifier,))
                else:
                    cursor.execute('''
                        SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation
                        FROM staff
                        WHERE roblox_user_id = ?
                    ''', (user_identifier,))
            else:
                cursor.execute('''
                    SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation
                    FROM staff
                    WHERE roblox_username = ?
                ''', (user_identifier,))
            
            staff_member = cursor.fetchone()
            conn.close()
            
            return staff_member
            
        except Exception as e:
            print(f"Error getting staff member: {e}")
            return None

    async def get_staff_member_detailed(self, user_identifier):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            
            staff_member = None
            
            # Check database directly for ALL possible matches regardless of input type
            # This is the most reliable method - check all database columns for exact matches
            
            # 1. Try as Discord ID in staff table
            if user_identifier.isdigit():
                cursor.execute('''
                    SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, 
                           roblox_role_id, category, warnings, excellence_score, bad_streak, 
                           minimum_streak, evaluation_week_score, created_at
                    FROM staff
                    WHERE discord_user_id = ?
                ''', (user_identifier,))
                staff_member = cursor.fetchone()
                if staff_member:
                    conn.close()
                    return staff_member
            
            # 2. Try as Roblox ID in staff table
            if user_identifier.isdigit():
                cursor.execute('''
                    SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, 
                           roblox_role_id, category, warnings, excellence_score, bad_streak, 
                           minimum_streak, evaluation_week_score, created_at
                    FROM staff
                    WHERE roblox_user_id = ?
                ''', (user_identifier,))
                staff_member = cursor.fetchone()
                if staff_member:
                    conn.close()
                    return staff_member
            
            # 3. Try as username (case-insensitive search) in staff table
            cursor.execute('''
                SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, 
                       roblox_role_id, category, warnings, excellence_score, bad_streak, 
                       minimum_streak, evaluation_week_score, created_at
                FROM staff
                WHERE LOWER(roblox_username) = LOWER(?)
            ''', (user_identifier,))
            staff_member = cursor.fetchone()
            if staff_member:
                conn.close()
                return staff_member
            
            conn.close()
            return None
            
        except Exception as e:
            print(f"Error getting staff member detailed: {e}")
            return None

    async def update_excellence_points(self, roblox_user_id, new_excellences, should_mark_evaluation, discord_user_id=None, current_excellences=0):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE staff 
                SET excellences = ?, evaluation = ?
                WHERE roblox_user_id = ?
            ''', (new_excellences, should_mark_evaluation, roblox_user_id))
            
            conn.commit()
            conn.close()
            
            if discord_user_id:
                await self.update_discord_excellence_roles(discord_user_id, current_excellences, new_excellences)
            
            return True
            
        except Exception as e:
            print(f"Error updating excellence points: {e}")
            return False
