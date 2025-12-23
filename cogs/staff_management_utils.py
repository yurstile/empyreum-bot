import discord
import sqlite3
import requests
from database import (
    get_role_by_name, get_staff_member, get_verified_user_by_roblox_id, 
    get_verified_user_by_discord_id, remove_staff_member, remove_verified_user, 
    add_staff_member, add_verified_user, update_staff_role, get_all_staff, 
    get_all_verified_users, get_staff_by_discord_id, RANK_HIERARCHY, 
    SPECIAL_ROLES, STAFF_ROLES
)
from .shared_utils import SharedUtils

class StaffManagementUtils(SharedUtils):
    def __init__(self, bot):
        super().__init__(bot)

    def determine_user_type(self, user_identifier: str) -> str:
        # Handle Discord mentions
        if user_identifier.startswith(('<@', '<@!')):
            return "discord_mention"
        
        # Handle numeric IDs
        if user_identifier.isdigit():
            # Discord IDs are typically 17-19 digits (snowflakes)
            if len(user_identifier) >= 17:
                return "discord_id"
            # Roblox IDs are typically 7-16 digits
            elif 7 <= len(user_identifier) <= 16:
                return "roblox_id"
            # Ambiguous short numbers default to roblox_id
            else:
                return "roblox_id"
        
        # Everything else is treated as Roblox username
        return "roblox_username"

    async def get_user_info(self, user_identifier: str, user_type: str):
        try:
            print(f"[DEBUG] Getting user info for: {user_identifier} (type: {user_type})")
            
            # Handle Discord mentions
            if user_identifier.startswith(('<@', '<@!')):
                discord_id = user_identifier.replace('<@', '').replace('<@!', '').replace('>', '')
                return await self.get_user_info(discord_id, "discord_id")
            
            # Check database for existing users
            if user_identifier.isdigit():
                # Try as Discord ID (17-19 digits)
                if len(user_identifier) >= 17:
                    staff = get_staff_by_discord_id(user_identifier)
                    if staff:
                        print(f"[DEBUG] Found in staff database by Discord ID: {staff[1]}")
                        return {
                            'roblox_user_id': staff[0],
                            'roblox_username': staff[1],
                            'discord_user_id': staff[2],
                            'in_database': True,
                            'type': 'staff'
                        }
                    
                    verified = get_verified_user_by_discord_id(user_identifier)
                    if verified:
                        print(f"[DEBUG] Found in verified users database by Discord ID: {verified[1]}")
                        return {
                            'roblox_user_id': verified[2],
                            'roblox_username': verified[1],
                            'discord_user_id': verified[0],
                            'in_database': True,
                            'type': 'verified'
                        }
                    
                    # Not in database - get Discord display name and search Roblox API
                    try:
                        guild = self.bot.get_guild(941998687779954708)
                        if guild:
                            member = guild.get_member(int(user_identifier))
                            if member:
                                display_name = member.display_name
                                print(f"[DEBUG] Found Discord member not in database: {display_name}, searching Roblox API")
                                
                                # Search Roblox API using display name
                                roblox_info = await self.get_roblox_user_info(display_name)
                                if roblox_info:
                                    print(f"[DEBUG] Found Roblox user via display name: {roblox_info['username']} (ID: {roblox_info['user_id']})")
                                    return {
                                        'roblox_user_id': roblox_info['user_id'],
                                        'roblox_username': roblox_info['username'],
                                        'discord_user_id': user_identifier,
                                        'in_database': False,
                                        'type': 'discord_with_roblox',
                                        'needs_manual_registration': True
                                    }
                                else:
                                    print(f"[DEBUG] No Roblox user found for display name: {display_name}")
                                    return {
                                        'roblox_user_id': None,
                                        'roblox_username': display_name,
                                        'discord_user_id': user_identifier,
                                        'in_database': False,
                                        'type': 'discord_only',
                                        'needs_manual_registration': False,
                                        'error': f"No Roblox user found with username '{display_name}'"
                                    }
                    except Exception as e:
                        print(f"[DEBUG] Error checking Discord member: {e}")
                
                # Try as Roblox ID
                staff = get_staff_member(user_identifier)
                if staff:
                    print(f"[DEBUG] Found in staff database by Roblox ID: {staff[1]}")
                    return {
                        'roblox_user_id': staff[0],
                        'roblox_username': staff[1],
                        'discord_user_id': staff[2],
                        'in_database': True,
                        'type': 'staff'
                    }
                
                verified = get_verified_user_by_roblox_id(user_identifier)
                if verified:
                    print(f"[DEBUG] Found in verified users database by Roblox ID: {verified[1]}")
                    return {
                        'roblox_user_id': verified[2],
                        'roblox_username': verified[1],
                        'discord_user_id': verified[0],
                        'in_database': True,
                        'type': 'verified'
                    }
                
                # Try Roblox API by ID
                if 7 <= len(user_identifier) <= 16:
                    roblox_info = await self.get_roblox_user_info_by_id(user_identifier)
                    if roblox_info:
                        print(f"[DEBUG] Found via Roblox API by ID: {roblox_info['username']}")
                        return {
                            'roblox_user_id': roblox_info['user_id'],
                            'roblox_username': roblox_info['username'],
                            'discord_user_id': None,
                            'in_database': False,
                            'type': 'roblox_only'
                        }
            else:
                # Try as username in database
                staff_members = get_all_staff()
                for staff in staff_members:
                    if staff[1].lower() == user_identifier.lower():
                        print(f"[DEBUG] Found in staff database by username: {staff[1]}")
                        return {
                            'roblox_user_id': staff[0],
                            'roblox_username': staff[1],
                            'discord_user_id': staff[2],
                            'in_database': True,
                            'type': 'staff'
                        }
                
                verified_users = get_all_verified_users()
                for user in verified_users:
                    if user[1].lower() == user_identifier.lower():
                        print(f"[DEBUG] Found in verified users database by username: {user[1]}")
                        return {
                            'roblox_user_id': user[2],
                            'roblox_username': user[1],
                            'discord_user_id': user[0],
                            'in_database': True,
                            'type': 'verified'
                        }
                
                # Try Roblox API by username
                roblox_info = await self.get_roblox_user_info(user_identifier)
                if roblox_info:
                    print(f"[DEBUG] Found via Roblox API: {roblox_info['username']}")
                    return {
                        'roblox_user_id': roblox_info['user_id'],
                        'roblox_username': roblox_info['username'],
                        'discord_user_id': None,
                        'in_database': False,
                        'type': 'roblox_only'
                    }
            
            print(f"[DEBUG] No user found for: {user_identifier}")
            return None
                
        except Exception as e:
            print(f"[ERROR] Error in get_user_info: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def get_current_rank_info(self, roblox_user_id, discord_user_id):
        if discord_user_id:
            guild = self.bot.get_guild(941998687779954708)
            if guild:
                member = guild.get_member(int(discord_user_id))
                if member:
                    true_staff_role = guild.get_role(int(SPECIAL_ROLES["true_staff"]))
                    true_patient_role = guild.get_role(int(SPECIAL_ROLES["true_patient"]))
                    
                    if true_staff_role and true_staff_role in member.roles:
                        staff = get_staff_by_discord_id(discord_user_id)
                        if staff:
                            return {
                                'type': 'staff',
                                'roblox_role_id': staff[5],
                                'category': staff[6]
                            }
                    
                    if true_patient_role and true_patient_role in member.roles:
                        return {
                            'type': 'patient',
                            'category': 'patient'
                        }
            
            staff = get_staff_by_discord_id(discord_user_id)
            if staff:
                return {
                    'type': 'staff',
                    'roblox_role_id': staff[5],
                    'category': staff[6]
                }
            
            verified = get_verified_user_by_discord_id(discord_user_id)
            if verified:
                return {
                    'type': 'patient',
                    'category': 'patient'
                }
        
        staff = get_staff_member(roblox_user_id)
        if staff:
            return {
                'type': 'staff',
                'roblox_role_id': staff[5],
                'category': staff[6]
            }
        
        verified = get_verified_user_by_roblox_id(roblox_user_id)
        if verified:
            return {
                'type': 'patient',
                'category': 'patient'
            }
        
        return None

    def get_current_rank_name(self, current_rank_info):
        if not current_rank_info:
            return None
        
        if current_rank_info.get('type') == 'staff' and current_rank_info.get('roblox_role_id'):
            return self.get_rank_name_by_roblox_role_id(current_rank_info['roblox_role_id'])
        elif current_rank_info.get('type') == 'patient':
            return "patient"
        return None

    def get_current_rank_name_from_discord_roles(self, guild, discord_user_id):
        try:
            member = guild.get_member(int(discord_user_id))
            if not member:
                return None
            
            rank_role_ids = self.get_all_rank_role_ids()
            
            for role_id in rank_role_ids:
                role = guild.get_role(int(role_id))
                if role and role in member.roles:
                    return self.get_rank_name_by_discord_role_id(role_id)
            
            return None
        except Exception as e:
            print(f"Error getting current rank name from Discord roles: {e}")
            return None

    def get_next_rank(self, current_rank_name):
        try:
            current_index = RANK_HIERARCHY.index(current_rank_name.lower())
            if current_index < len(RANK_HIERARCHY) - 1:
                return RANK_HIERARCHY[current_index + 1]
            return None
        except ValueError:
            print(f"Current rank '{current_rank_name}' not found in hierarchy")
            return None

    async def execute_rank_change(self, interaction, roblox_user_id, roblox_username, discord_user_id, current_rank_info, new_roblox_role_id, new_discord_role_id, new_category, in_database, user_info=None):
        try:
            print(f"[DEBUG] Starting rank change execution for {roblox_username}")
            print(f"[DEBUG] Parameters: roblox_user_id={roblox_user_id}, discord_user_id={discord_user_id}")
            print(f"[DEBUG] New role: roblox_id={new_roblox_role_id}, discord_id={new_discord_role_id}, category={new_category}")
            print(f"[DEBUG] In database: {in_database}")
            
            roblox_success = True
            if new_roblox_role_id and new_roblox_role_id != "None" and roblox_user_id:
                print(f"[DEBUG] Attempting to rank {roblox_username} on Roblox to role {new_roblox_role_id}")
                roblox_success = await self.rank_roblox_user(roblox_user_id, new_roblox_role_id)
                print(f"[DEBUG] Roblox ranking result: {roblox_success}")
                if not roblox_success:
                    error_msg = f"❌ Failed to rank user {roblox_username} on Roblox! Check console logs for details."
                    print(f"[ERROR] Roblox ranking failed for {roblox_username} (ID: {roblox_user_id}) to role {new_roblox_role_id}")
                    await interaction.followup.send(error_msg, ephemeral=True)
                    return False
                print(f"[DEBUG] Successfully ranked {roblox_username} on Roblox")

            discord_success = True
            if discord_user_id and new_discord_role_id:
                print(f"[DEBUG] Attempting to change Discord rank for user {discord_user_id} to role {new_discord_role_id}")
                discord_success = await self.change_discord_rank(interaction.guild, discord_user_id, new_discord_role_id, new_category, current_rank_info)
                print(f"[DEBUG] Discord ranking result: {discord_success}")
                if not discord_success:
                    error_msg = f"❌ Failed to change Discord rank for {roblox_username}! Check console logs for details."
                    print(f"[ERROR] Discord ranking failed for {roblox_username} (Discord ID: {discord_user_id}) to role {new_discord_role_id}")
                    await interaction.followup.send(error_msg, ephemeral=True)
                    return False
                print(f"[DEBUG] Successfully changed Discord rank for {roblox_username}")

            if discord_user_id:
                print(f"[DEBUG] Removing excellence roles for {discord_user_id}")
                await self.remove_excellence_roles(discord_user_id)

            db_success = True
            if in_database and roblox_user_id:
                print(f"[DEBUG] Updating database for {roblox_username}")
                db_success = await self.update_database(roblox_user_id, roblox_username, discord_user_id, current_rank_info, new_roblox_role_id, new_category)
                print(f"[DEBUG] Database update result: {db_success}")
                if not db_success:
                    error_msg = f"❌ Failed to update database for {roblox_username}! Check console logs for details."
                    print(f"[ERROR] Database update failed for {roblox_username}")
                    await interaction.followup.send(error_msg, ephemeral=True)
                    return False
                print(f"[DEBUG] Successfully updated database for {roblox_username}")
            elif not in_database and roblox_user_id:
                # Add new user to database
                print(f"[DEBUG] Adding new user to database: {roblox_username}")
                if new_category in ['staff', 'staff_silver']:
                    add_staff_member(roblox_user_id, roblox_username, discord_user_id, new_roblox_role_id, new_category)
                else:
                    if discord_user_id:
                        add_verified_user(discord_user_id, roblox_username, roblox_user_id)
                print(f"[DEBUG] Successfully added {roblox_username} to database")

            print(f"[DEBUG] Rank change completed successfully for {roblox_username}")
            return True

        except Exception as e:
            print(f"[ERROR] Unexpected error in execute_rank_change: {e}")
            import traceback
            traceback.print_exc()
            error_msg = f"❌ Unexpected error during rank change for {roblox_username}! Check console logs for details."
            try:
                await interaction.followup.send(error_msg, ephemeral=True)
            except:
                pass
            return False

    async def rank_roblox_user(self, roblox_user_id, new_roblox_role_id):
        try:
            print(f"[DEBUG] Starting Roblox ranking for user {roblox_user_id} to role {new_roblox_role_id}")
            result = await super().rank_roblox_user(roblox_user_id, new_roblox_role_id)
            print(f"[DEBUG] Roblox ranking result: {result}")
            return result
        except Exception as e:
            print(f"[ERROR] Error in rank_roblox_user: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def change_discord_rank(self, guild, discord_user_id, new_discord_role_id, new_category, current_rank_info):
        try:
            print(f"[DEBUG] Starting Discord rank change for user {discord_user_id} to role {new_discord_role_id}")
            member = await guild.fetch_member(int(discord_user_id))
            if not member:
                print(f"[ERROR] Discord member {discord_user_id} not found in guild")
                return False
            print(f"[DEBUG] Found Discord member: {member.display_name} (ID: {member.id})")
            
            new_role = guild.get_role(int(new_discord_role_id))
            if not new_role:
                return False

            current_discord_role_id = None
            
            if current_rank_info and current_rank_info.get('type') == 'staff' and current_rank_info.get('roblox_role_id'):
                current_discord_role_id = self.get_discord_role_id_by_roblox_role_id(current_rank_info['roblox_role_id'])
            
            if not current_discord_role_id:
                current_discord_role_id = self.find_current_rank_role_from_member(member)
            
            # For manual registration (current_rank_info is None), assume they're coming from admittee
            if not current_discord_role_id and not current_rank_info:
                admittee_role = get_role_by_name("admittee")
                if admittee_role:
                    current_discord_role_id = admittee_role[1]
                    print(f"[DEBUG] Assuming user is coming from admittee role for manual registration")
            
            roles_to_remove = []
            roles_to_add = [new_role]

            if current_discord_role_id:
                old_role = guild.get_role(int(current_discord_role_id))
                if old_role and old_role in member.roles:
                    roles_to_remove.append(old_role)
            
            true_staff_role = guild.get_role(int(SPECIAL_ROLES["true_staff"]))
            clinic_maids_role = guild.get_role(int(SPECIAL_ROLES["clinic_maids"]))
            true_patient_role = guild.get_role(int(SPECIAL_ROLES["true_patient"]))
            untrue_patient_role = guild.get_role(int(SPECIAL_ROLES["untrue_patient"]))

            current_category = current_rank_info.get('category') if current_rank_info else None
            new_rank_name = self.get_rank_name_by_discord_role_id(new_discord_role_id)
            
            # For manual registration, determine current category based on admittee role
            if not current_rank_info and current_discord_role_id:
                admittee_role = get_role_by_name("admittee")
                if admittee_role and current_discord_role_id == admittee_role[1]:
                    current_category = "admittee"
                    print(f"[DEBUG] Detected admittee role transition for manual registration")

            excellence_role_ids = [
                1401232544611176528,  # 1 excellence
                1401235996380627057,  # 2 excellence
                1401236077796266146,  # 3 excellence
                1401236156779073678,  # 4 excellence
                1401236230477185034   # 5 excellence
            ]

            patient_role_ids = ["942019598142828574", "942019597371056159", "948008718111490099", "942019596469280768"]
            staff_role_ids = ["942019594363756544", "953743887149695007", "942019593000611851", 
                             "942019592442765352", "942019591608102952", "942019590576275467", "943947575965405234"]

            if current_category in ['staff', 'staff_silver'] and new_category == 'patient':
                if true_staff_role and true_staff_role in member.roles:
                    roles_to_remove.append(true_staff_role)
                if clinic_maids_role and clinic_maids_role in member.roles:
                    roles_to_remove.append(clinic_maids_role)
                
                for role in member.roles:
                    if role.id in excellence_role_ids:
                        roles_to_remove.append(role)
                    if role.id in staff_role_ids:
                        roles_to_remove.append(role)
                
                if new_rank_name == "admittee":
                    if untrue_patient_role:
                        roles_to_add.append(untrue_patient_role)
                else:
                    if untrue_patient_role:
                        roles_to_add.append(untrue_patient_role)
                    if true_patient_role:
                        roles_to_add.append(true_patient_role)

            elif current_category in ['staff', 'staff_silver'] and new_category in ['staff', 'staff_silver']:
                for role in member.roles:
                    if role.id in excellence_role_ids:
                        roles_to_remove.append(role)
                    if role.id in staff_role_ids:
                        roles_to_remove.append(role)

            elif current_category in ['patient'] and new_category in ['staff', 'staff_silver']:
                if true_patient_role and true_patient_role in member.roles:
                    roles_to_remove.append(true_patient_role)
                if untrue_patient_role and untrue_patient_role in member.roles:
                    roles_to_remove.append(untrue_patient_role)
                
                for role in member.roles:
                    if role.id in patient_role_ids:
                        roles_to_remove.append(role)
                
                if true_staff_role:
                    roles_to_add.append(true_staff_role)
                if clinic_maids_role:
                    roles_to_add.append(clinic_maids_role)

            elif current_category == 'admittee' and new_category in ['staff', 'staff_silver']:
                # Transition from admittee to staff role
                print(f"[DEBUG] Transitioning from admittee to staff role: {new_rank_name}")
                
                # Remove admittee role
                if current_discord_role_id:
                    old_role = guild.get_role(int(current_discord_role_id))
                    if old_role and old_role in member.roles:
                        roles_to_remove.append(old_role)
                
                # Add staff-specific roles
                if true_staff_role:
                    roles_to_add.append(true_staff_role)
                if clinic_maids_role:
                    roles_to_add.append(clinic_maids_role)
                    
            elif current_category == 'admittee' and new_category == 'patient':
                # Transition from admittee to patient role
                print(f"[DEBUG] Transitioning from admittee to patient role: {new_rank_name}")
                
                # Remove admittee role
                if current_discord_role_id:
                    old_role = guild.get_role(int(current_discord_role_id))
                    if old_role and old_role in member.roles:
                        roles_to_remove.append(old_role)
                
                # Add patient-specific roles
                if new_rank_name == "admittee":
                    if untrue_patient_role:
                        roles_to_add.append(untrue_patient_role)
                else:
                    if untrue_patient_role:
                        roles_to_add.append(untrue_patient_role)
                    if true_patient_role:
                        roles_to_add.append(true_patient_role)

            elif current_category in ['patient'] and new_category == 'patient':
                if untrue_patient_role and untrue_patient_role in member.roles:
                    roles_to_remove.append(untrue_patient_role)
                if true_patient_role and true_patient_role in member.roles:
                    roles_to_remove.append(true_patient_role)
                
                if new_rank_name == "admittee":
                    if untrue_patient_role:
                        roles_to_add.append(untrue_patient_role)
                else:
                    if untrue_patient_role:
                        roles_to_add.append(untrue_patient_role)
                    if true_patient_role:
                        roles_to_add.append(true_patient_role)

            for role in roles_to_remove:
                try:
                    await member.remove_roles(role)
                except Exception as e:
                    print(f"Error removing role {role.name}: {e}")

            for role in roles_to_add:
                try:
                    await member.add_roles(role)
                except Exception as e:
                    print(f"Error adding role {role.name}: {e}")

            print(f"[DEBUG] Successfully changed Discord rank for {member.display_name}")
            return True

        except Exception as e:
            print(f"[ERROR] Error changing Discord rank for user {discord_user_id}: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def update_database(self, roblox_user_id, roblox_username, discord_user_id, current_rank_info, new_roblox_role_id, new_category):
        try:
            if new_category in ['staff', 'staff_silver']:
                if current_rank_info and current_rank_info.get('type') == 'patient':
                    remove_verified_user(roblox_user_id)
                
                if discord_user_id:
                    add_staff_member(roblox_user_id, roblox_username, discord_user_id, new_roblox_role_id, new_category)
                    update_staff_role(roblox_user_id, new_roblox_role_id, new_category)
                else:
                    add_staff_member(roblox_user_id, roblox_username, None, new_roblox_role_id, new_category)
                    update_staff_role(roblox_user_id, new_roblox_role_id, new_category)

            else:
                if current_rank_info and current_rank_info.get('type') == 'staff':
                    remove_staff_member(roblox_user_id)
                    if discord_user_id:
                        await self.remove_excellence_roles(discord_user_id)
                
                if discord_user_id:
                    add_verified_user(discord_user_id, roblox_username, roblox_user_id)
                else:
                    conn = sqlite3.connect('roles.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT OR REPLACE INTO verified_users (discord_id, username, roblox_user_id)
                        VALUES (?, ?, ?)
                    ''', (f"PLACEHOLDER_{roblox_user_id}", roblox_username, roblox_user_id))
                    conn.commit()
                    conn.close()

            if discord_user_id and current_rank_info and current_rank_info.get('type') == 'staff':
                await self.reset_excellence_data(roblox_user_id, discord_user_id)

            return True

        except Exception as e:
            print(f"Error updating database: {e}")
            return False

    async def remove_excellence_roles(self, discord_user_id):
        try:
            guild = self.bot.get_guild(941998687779954708)
            if not guild:
                print("Guild not found for excellence role removal")
                return
            
            member = await guild.fetch_member(int(discord_user_id))
            if not member:
                print(f"Member {discord_user_id} not found for excellence role removal")
                return
            
            excellence_role_ids = [
                1401232544611176528,  # 1 excellence
                1401235996380627057,  # 2 excellence
                1401236077796266146,  # 3 excellence
                1401236156779073678,  # 4 excellence
                1401236230477185034   # 5 excellence
            ]
            
            roles_to_remove = []
            for role_id in excellence_role_ids:
                role = guild.get_role(role_id)
                if role and role in member.roles:
                    roles_to_remove.append(role)
            
            for role in roles_to_remove:
                try:
                    await member.remove_roles(role)
                except Exception as e:
                    print(f"Error removing excellence role {role.name}: {e}")
                    
        except Exception as e:
            print(f"Error removing excellence roles: {e}")

    async def reset_excellence_data(self, roblox_user_id, discord_user_id):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE staff 
                SET excellence_score = 0, excellences = 0, evaluation = FALSE, evaluation_week_score = 0
                WHERE roblox_user_id = ?
            ''', (roblox_user_id,))
            
            conn.commit()
            conn.close()
            
            await self.remove_excellence_roles(discord_user_id)
            
        except Exception as e:
            print(f"Error resetting excellence data: {e}")

    def get_rank_name_by_discord_role_id(self, discord_role_id):
        return super().get_rank_name_by_discord_role_id(discord_role_id)

    def get_rank_name_by_roblox_role_id(self, roblox_role_id):
        return super().get_rank_name_by_roblox_role_id(roblox_role_id)

    def get_discord_role_id_by_roblox_role_id(self, roblox_role_id):
        return super().get_discord_role_id_by_roblox_role_id(roblox_role_id)

    def find_current_rank_role_from_member(self, member):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            cursor.execute('SELECT discord_role_id FROM roles')
            role_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            for role_id in role_ids:
                role = member.guild.get_role(int(role_id))
                if role and role in member.roles:
                    return role_id
            
            return None
        except Exception as e:
            print(f"Error finding current rank role from member: {e}")
            return None

    def get_all_rank_role_ids(self):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            cursor.execute('SELECT discord_role_id FROM roles')
            role_ids = [row[0] for row in cursor.fetchall()]
            conn.close()
            return role_ids
        except Exception as e:
            print(f"Error getting all rank role IDs: {e}")
            return []

    async def get_roblox_user_info(self, username):
        try:
            print(f"[DEBUG] Fetching Roblox user info for: {username}")
            
            if username.startswith(('@', '<@')) or (username.isdigit() and len(username) == 18):
                print(f"[DEBUG] Skipping Roblox API call for Discord ID/mention: {username}")
                return None
            
            # Use Roblox Users API v1 - POST method for username lookup
            response = requests.post(
                "https://users.roblox.com/v1/usernames/users",
                json={"usernames": [username], "excludeBannedUsers": False},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            print(f"[DEBUG] Roblox API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    user_data = data['data'][0]
                    if user_data.get('id'):
                        print(f"[DEBUG] Found Roblox user: {user_data.get('name')} (ID: {user_data.get('id')})")
                        return {
                            'user_id': str(user_data['id']),
                            'username': user_data.get('name', username)
                        }
            
            print(f"[DEBUG] User not found via Roblox API: {username}")
            return None
            
        except Exception as e:
            print(f"[ERROR] Error getting Roblox user info: {e}")
            import traceback
            traceback.print_exc()
            return None


    async def get_roblox_user_info_by_id(self, user_id):
        try:
            print(f"[DEBUG] Fetching Roblox user info by ID: {user_id}")
            response = requests.get(f"https://users.roblox.com/v1/users/{user_id}")
            print(f"[DEBUG] Roblox API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"[DEBUG] Found Roblox user by ID: {data.get('name')} (ID: {user_id})")
                return {
                    'user_id': str(user_id),
                    'username': data.get('name', 'Unknown')
                }
            else:
                print(f"[DEBUG] Roblox API error for ID {user_id}: {response.status_code} - {response.text}")
            return None
        except Exception as e:
            print(f"[ERROR] Error getting Roblox user info by ID: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def manual_register_user(self, discord_user_id, roblox_user_id, roblox_username, target_rank):
        """
        Manually register a user by adding them to appropriate database table
        """
        try:
            print(f"[DEBUG] Manual registration: Discord ID {discord_user_id}, Roblox user '{roblox_username}' (ID: {roblox_user_id}), target rank '{target_rank}'")
            
            # Get target role information
            target_role_info = get_role_by_name(target_rank)
            if not target_role_info:
                return {
                    'success': False,
                    'error': f"Target rank '{target_rank}' not found in database"
                }
            
            target_roblox_role_id = target_role_info[2]
            target_category = target_role_info[3]
            
            if not target_roblox_role_id or target_roblox_role_id == "None":
                return {
                    'success': False,
                    'error': f"Target rank '{target_rank}' has no Roblox role ID"
                }
            
            # Rank user on Roblox
            print(f"[DEBUG] Ranking {roblox_username} to {target_rank} (Roblox role ID: {target_roblox_role_id})")
            roblox_success = await self.rank_roblox_user(roblox_user_id, target_roblox_role_id)
            if not roblox_success:
                return {
                    'success': False,
                    'error': f"Failed to rank user {roblox_username} on Roblox"
                }
            
            print(f"[DEBUG] Successfully ranked {roblox_username} on Roblox")
            
            # Add to appropriate database table based on category
            if target_category in ['staff', 'staff_silver']:
                print(f"[DEBUG] Adding {roblox_username} to staff database (category: {target_category})")
                add_staff_member(roblox_user_id, roblox_username, discord_user_id, target_roblox_role_id, target_category)
            else:
                print(f"[DEBUG] Adding {roblox_username} to verified users database (category: {target_category})")
                add_verified_user(discord_user_id, roblox_username, roblox_user_id)
            
            return {
                'success': True,
                'roblox_user_id': roblox_user_id,
                'roblox_username': roblox_username,
                'target_rank': target_rank,
                'target_category': target_category
            }
            
        except Exception as e:
            print(f"[ERROR] Error in manual_register_user: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}"
            }


    async def get_staff_member_detailed(self, user_identifier):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            
            staff_member = None
            
            if user_identifier.isdigit():
                if len(user_identifier) == 18:
                    cursor.execute('''
                        SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at
                        FROM staff
                        WHERE discord_user_id = ?
                    ''', (user_identifier,))
                else:
                    cursor.execute('''
                        SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at
                        FROM staff
                        WHERE roblox_user_id = ?
                    ''', (user_identifier,))
            else:
                cursor.execute('''
                    SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at
                    FROM staff
                    WHERE roblox_username = ?
                ''', (user_identifier,))
            
            staff_member = cursor.fetchone()
            conn.close()
            
            return staff_member
            
        except Exception as e:
            print(f"Error getting detailed staff member: {e}")
            return None

    async def send_demotion_dm(self, guild, discord_user_id, old_rank, new_rank, reason, author_name):
        try:
            member = await guild.fetch_member(int(discord_user_id))
            if member:
                embed = discord.Embed(
                    title="Staff Demotion Notice",
                    description=f"You have been demoted from **{old_rank}** to **{new_rank}**.",
                    color=0xff0000,
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.add_field(name="Demoted By", value=author_name, inline=True)
                embed.set_footer(text="If you have any questions, please contact a higher-ranking staff member.")
                
                await member.send(embed=embed)
            else:
                print(f"Could not find member {discord_user_id} to send DM")
        except Exception as e:
            print(f"Error sending demotion DM: {e}")
