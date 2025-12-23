import discord
import re
from datetime import datetime, timezone, timedelta
from database import (
    get_staff_member, remove_staff_member, add_verified_user,
    get_role_by_name, add_staff_to_inactivity, get_staff_inactivity_by_roblox_id,
    get_staff_inactivity_by_discord_id, get_all_inactive_staff,
    remove_staff_from_inactivity, can_submit_inactivity_request,
    add_staff_member, update_staff_role, get_all_staff, get_all_verified_users,
    get_staff_by_discord_id, get_verified_user_by_discord_id, get_verified_user_by_roblox_id,
    SPECIAL_ROLES
)
from .shared_utils import SharedUtils

class StaffNoticesUtils(SharedUtils):
    def __init__(self, bot):
        super().__init__(bot)

    def get_rank_name_by_roblox_role_id(self, roblox_role_id):
        return super().get_rank_name_by_roblox_role_id(roblox_role_id)

    async def rank_roblox_user(self, roblox_user_id, new_roblox_role_id):
        return await super().rank_roblox_user(roblox_user_id, new_roblox_role_id)

    async def send_inactivity_start_dm(self, member, username, reason):
        try:
            embed = discord.Embed(
                title="Staff Inactivity Notice",
                description=f"You have been placed on inactivity.",
                color=0xffa500,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Username", value=username, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_footer(text="Please contact a higher-ranking staff member if you have any questions.")
            
            await member.send(embed=embed)
        except Exception as e:
            print(f"Error sending inactivity start DM: {e}")

    async def send_inactivity_end_dm(self, member, username):
        try:
            embed = discord.Embed(
                title="Staff Inactivity End Notice",
                description=f"Your inactivity period has ended. Welcome back!",
                color=0x00ff00,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Username", value=username, inline=True)
            embed.set_footer(text="You can now resume your staff duties.")
            
            await member.send(embed=embed)
        except Exception as e:
            print(f"Error sending inactivity end DM: {e}")

    async def send_resignation_dm(self, member, username):
        try:
            embed = discord.Embed(
                title="Staff Resignation Notice",
                description=f"You have resigned from your staff position.",
                color=0xff0000,
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Username", value=username, inline=True)
            embed.set_footer(text="Thank you for your service. You can reapply in the future if you wish to return.")
            
            await member.send(embed=embed)
        except Exception as e:
            print(f"Error sending resignation DM: {e}")

    async def change_inactivity_roles(self, member, is_starting_inactivity=True):
        try:
            guild = member.guild
            
            true_staff_role = guild.get_role(int(SPECIAL_ROLES["true_staff"]))
            clinic_maids_role = guild.get_role(int(SPECIAL_ROLES["clinic_maids"]))
            true_patient_role = guild.get_role(int(SPECIAL_ROLES["true_patient"]))
            untrue_patient_role = guild.get_role(int(SPECIAL_ROLES["untrue_patient"]))
            inactivity_role = guild.get_role(1262042442883006464)
            additional_inactivity_role = guild.get_role(1408916656935145724)
            
            excellence_role_ids = [
                1401232544611176528,  # 1 excellence
                1401235996380627057,  # 2 excellence
                1401236077796266146,  # 3 excellence
                1401236156779073678,  # 4 excellence
                1401236230477185034   # 5 excellence
            ]
            
            staff_role_ids = [942019594363756544, 953743887149695007, 942019593000611851, 
                             942019592442765352, 942019591608102952, 942019590576275467, 943947575965405234]
            
            if is_starting_inactivity:
                roles_to_remove = []
                roles_to_add = []
                
                for role in member.roles:
                    if role.id in excellence_role_ids:
                        roles_to_remove.append(role)
                    if role.id in staff_role_ids:
                        roles_to_remove.append(role)
                
                if clinic_maids_role and clinic_maids_role in member.roles:
                    roles_to_remove.append(clinic_maids_role)
                
                if untrue_patient_role:
                    roles_to_add.append(untrue_patient_role)
                if inactivity_role:
                    roles_to_add.append(inactivity_role)
                if additional_inactivity_role:
                    roles_to_add.append(additional_inactivity_role)
                
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
            
            else:
                roles_to_remove = []
                roles_to_add = []
                
                if untrue_patient_role and untrue_patient_role in member.roles:
                    roles_to_remove.append(untrue_patient_role)
                if inactivity_role and inactivity_role in member.roles:
                    roles_to_remove.append(inactivity_role)
                if additional_inactivity_role and additional_inactivity_role in member.roles:
                    roles_to_remove.append(additional_inactivity_role)
                
                if clinic_maids_role:
                    roles_to_add.append(clinic_maids_role)
                
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
                        
        except Exception as e:
            print(f"Error changing inactivity roles: {e}")

    async def change_resignation_roles(self, member):
        try:
            guild = member.guild
            
            true_staff_role = guild.get_role(int(SPECIAL_ROLES["true_staff"]))
            clinic_maids_role = guild.get_role(int(SPECIAL_ROLES["clinic_maids"]))
            untrue_patient_role = guild.get_role(int(SPECIAL_ROLES["untrue_patient"]))
            admittee_role = guild.get_role(942019598142828574)
            
            excellence_role_ids = [
                1401232544611176528,  # 1 excellence
                1401235996380627057,  # 2 excellence
                1401236077796266146,  # 3 excellence
                1401236156779073678,  # 4 excellence
                1401236230477185034   # 5 excellence
            ]
            
            staff_role_ids = [942019594363756544, 953743887149695007, 942019593000611851, 
                             942019592442765352, 942019591608102952, 942019590576275467, 943947575965405234]
            
            roles_to_remove = []
            roles_to_add = []
            
            for role in member.roles:
                if role.id in excellence_role_ids:
                    roles_to_remove.append(role)
                if role.id in staff_role_ids:
                    roles_to_remove.append(role)
            
            if true_staff_role and true_staff_role in member.roles:
                roles_to_remove.append(true_staff_role)
            if clinic_maids_role and clinic_maids_role in member.roles:
                roles_to_remove.append(clinic_maids_role)
            
            if admittee_role:
                roles_to_add.append(admittee_role)
            if untrue_patient_role:
                roles_to_add.append(untrue_patient_role)
            
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
                    
        except Exception as e:
            print(f"Error changing resignation roles: {e}")

    async def restore_excellence_roles(self, member, excellences):
        try:
            guild = member.guild
            
            excellence_role_ids = [
                1401232544611176528,  # 1 excellence
                1401235996380627057,  # 2 excellence
                1401236077796266146,  # 3 excellence
                1401236156779073678,  # 4 excellence
                1401236230477185034   # 5 excellence
            ]
            
            if excellences >= 5:
                excellence_role = guild.get_role(excellence_role_ids[4])
                if excellence_role:
                    await member.add_roles(excellence_role)
            elif excellences >= 4:
                excellence_role = guild.get_role(excellence_role_ids[3])
                if excellence_role:
                    await member.add_roles(excellence_role)
            elif excellences >= 3:
                excellence_role = guild.get_role(excellence_role_ids[2])
                if excellence_role:
                    await member.add_roles(excellence_role)
            elif excellences >= 2:
                excellence_role = guild.get_role(excellence_role_ids[1])
                if excellence_role:
                    await member.add_roles(excellence_role)
            elif excellences >= 1:
                excellence_role = guild.get_role(excellence_role_ids[0])
                if excellence_role:
                    await member.add_roles(excellence_role)
                    
        except Exception as e:
            print(f"Error restoring excellence roles: {e}")

    def parse_date(self, date_str):
        try:
            if not date_str or not isinstance(date_str, str):
                return None
            
            date_str = date_str.strip()
            
            month_map = {
                'january': 1, 'jan': 1,
                'february': 2, 'feb': 2,
                'march': 3, 'mar': 3,
                'april': 4, 'apr': 4,
                'may': 5,
                'june': 6, 'jun': 6,
                'july': 7, 'jul': 7,
                'august': 8, 'aug': 8,
                'september': 9, 'sep': 9,
                'october': 10, 'oct': 10,
                'november': 11, 'nov': 11,
                'december': 12, 'dec': 12
            }
            
            pattern = r'(\d{1,2})(?:st|nd|rd|th)?\s+(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
            match = re.search(pattern, date_str, re.IGNORECASE)
            
            if match:
                day = int(match.group(1))
                month_name = match.group(2).lower()
                month = month_map.get(month_name)
                
                if month:
                    current_year = datetime.now().year
                    return datetime(current_year, month, day, tzinfo=timezone.utc)
            
            date_formats = [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%Y/%m/%d",
                "%m-%d-%Y",
                "%d-%m-%Y"
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            
            return None
        except Exception as e:
            print(f"Error parsing date {date_str}: {e}")
            return None

    async def is_resignation_notice(self, content):
        resignation_keywords = [
            "resign", "resignation"
        ]
        
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in resignation_keywords)

    async def is_inactivity_notice(self, content):
        inactivity_keywords = [
            "inactivity", "inactive"
        ]
        
        content_lower = content.lower()
        
        for keyword in inactivity_keywords:
            if keyword in content_lower:
                return True
        
        return False

    async def get_user_info(self, user_identifier: str):
        # Check database directly for ALL possible matches regardless of input type
        # This is the most reliable method - check all database columns for exact matches
        
        # 1. Try as Discord ID in staff table
        if user_identifier.isdigit():
            staff = get_staff_by_discord_id(user_identifier)
            if staff:
                return {
                    'roblox_user_id': staff[0],
                    'roblox_username': staff[1],
                    'discord_user_id': staff[2],
                    'type': 'staff'
                }
            
            # 2. Try as Discord ID in verified users table
            verified = get_verified_user_by_discord_id(user_identifier)
            if verified:
                return {
                    'roblox_user_id': verified[2],
                    'roblox_username': verified[1],
                    'discord_user_id': verified[0],
                    'type': 'verified'
                }
            
            # 3. Try as Discord ID in inactive staff table
            inactivity = get_staff_inactivity_by_discord_id(user_identifier)
            if inactivity:
                return {
                    'roblox_user_id': inactivity[0],
                    'roblox_username': inactivity[1],
                    'discord_user_id': inactivity[2],
                    'type': 'inactive'
                }
            
            # 4. Try as Roblox ID in staff table
            staff = get_staff_member(user_identifier)
            if staff:
                return {
                    'roblox_user_id': staff[0],
                    'roblox_username': staff[1],
                    'discord_user_id': staff[2],
                    'type': 'staff'
                }
            
            # 5. Try as Roblox ID in verified users table
            verified = get_verified_user_by_roblox_id(user_identifier)
            if verified:
                return {
                    'roblox_user_id': verified[2],
                    'roblox_username': verified[1],
                    'discord_user_id': verified[0],
                    'type': 'verified'
                }
            
            # 6. Try as Roblox ID in inactive staff table
            inactivity = get_staff_inactivity_by_roblox_id(user_identifier)
            if inactivity:
                return {
                    'roblox_user_id': inactivity[0],
                    'roblox_username': inactivity[1],
                    'discord_user_id': inactivity[2],
                    'type': 'inactive'
                }
            
            # 7. Try Roblox API for numeric IDs
            if 7 <= len(user_identifier) <= 16:
                roblox_info = await self.get_roblox_user_info_by_id(user_identifier)
                if roblox_info:
                    return {
                        'roblox_user_id': roblox_info['user_id'],
                        'roblox_username': roblox_info['username'],
                        'discord_user_id': None,
                        'type': 'unknown'
                    }
        
        # 8. Try as username (case-insensitive search) in staff table
        staff_members = get_all_staff()
        for staff in staff_members:
            if staff[1].lower() == user_identifier.lower():
                return {
                    'roblox_user_id': staff[0],
                    'roblox_username': staff[1],
                    'discord_user_id': staff[2],
                    'type': 'staff'
                }
        
        # 9. Try as username (case-insensitive search) in verified users table
        verified_users = get_all_verified_users()
        for user in verified_users:
            if user[1].lower() == user_identifier.lower():
                return {
                    'roblox_user_id': user[2],
                    'roblox_username': user[1],
                    'discord_user_id': user[0],
                    'type': 'verified'
                }
        
        # 10. Try as username (case-insensitive search) in inactive staff table
        inactive_staff = get_all_inactive_staff()
        for staff in inactive_staff:
            if staff[1].lower() == user_identifier.lower():
                return {
                    'roblox_user_id': staff[0],
                    'roblox_username': staff[1],
                    'discord_user_id': staff[2],
                    'type': 'inactive'
                }
        
        # 11. Try Roblox API for usernames
        if not user_identifier.isdigit():
            roblox_info = await self.get_roblox_user_info(user_identifier)
            if roblox_info:
                return {
                    'roblox_user_id': roblox_info['user_id'],
                    'roblox_username': roblox_info['username'],
                    'discord_user_id': None,
                    'type': 'unknown'
                }
        
        return None
