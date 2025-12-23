import discord
from discord import app_commands
from database import get_role_by_name, RANK_HIERARCHY, STAFF_ROLES

class PromotionView(discord.ui.View):
    def __init__(self, user_identifier: str, user_type: str, utils):
        super().__init__(timeout=60)
        self.user_identifier = user_identifier
        self.user_type = user_type
        self.utils = utils

    @discord.ui.button(label="Promote User", style=discord.ButtonStyle.green)
    async def promote_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.process_promotion(interaction)

    async def process_promotion(self, interaction: discord.Interaction):
        try:
            user_info = await self.utils.get_user_info(self.user_identifier, self.user_type)
            if not user_info:
                await interaction.followup.send("❌ User not found!", ephemeral=True)
                return

            roblox_user_id = user_info['roblox_user_id']
            roblox_username = user_info['roblox_username']
            discord_user_id = user_info.get('discord_user_id')
            in_database = user_info.get('in_database', True)

            current_rank_info = await self.utils.get_current_rank_info(roblox_user_id, discord_user_id)
            current_rank_name = self.utils.get_current_rank_name(current_rank_info)
            
            if not current_rank_name and discord_user_id:
                current_rank_name = self.utils.get_current_rank_name_from_discord_roles(interaction.guild, discord_user_id)
            
            if not current_rank_name:
                await interaction.followup.send("❌ Could not determine user's current rank!", ephemeral=True)
                return

            next_rank_name = self.utils.get_next_rank(current_rank_name)
            if not next_rank_name:
                await interaction.followup.send(f"❌ User {roblox_username} is already at the maximum rank (lecturer)!", ephemeral=True)
                return

            new_role_info = get_role_by_name(next_rank_name)
            if not new_role_info:
                await interaction.followup.send(f"❌ Rank '{next_rank_name}' not found in database!", ephemeral=True)
                return

            new_roblox_role_id = new_role_info[2]
            new_discord_role_id = new_role_info[1]
            new_category = new_role_info[3]

            result = await self.utils.execute_rank_change(
                interaction, roblox_user_id, roblox_username, discord_user_id,
                current_rank_info, new_roblox_role_id, new_discord_role_id, new_category, in_database, user_info
            )

            if result:
                author_name = interaction.user.display_name
                if not in_database:
                    await interaction.followup.send(f"> ✅ Successfully promoted {roblox_username} to {next_rank_name} on Roblox by {author_name} (user not in database)", ephemeral=False)
                else:
                    await interaction.followup.send(f"> ✅ Successfully promoted {roblox_username} from {current_rank_name} to {next_rank_name} by {author_name}", ephemeral=False)
            else:
                await interaction.followup.send("❌ Failed to promote user. Check logs for details.", ephemeral=True)

        except Exception as e:
            print(f"Error in process_promotion: {e}")
            await interaction.followup.send(f"❌ Error processing promotion: {str(e)}", ephemeral=True)

class RankChangeView(discord.ui.View):
    def __init__(self, user_identifier: str, user_type: str, utils):
        super().__init__(timeout=60)
        self.user_identifier = user_identifier
        self.user_type = user_type
        self.utils = utils
        self.selected_rank = None

        options = [discord.SelectOption(label=rank.title(), value=rank) for rank in RANK_HIERARCHY]
        self.rank_select = discord.ui.Select(
            placeholder="Select a rank...",
            options=options,
            custom_id="rank_select"
        )
        self.rank_select.callback = self.rank_select_callback
        self.add_item(self.rank_select)

    async def rank_select_callback(self, interaction: discord.Interaction):
        self.selected_rank = interaction.data['values'][0]
        await self.process_rank_change(interaction)

    async def process_rank_change(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            
            print(f"[DEBUG] Processing rank change for user: {self.user_identifier} to rank: {self.selected_rank}")
            
            user_info = await self.utils.get_user_info(self.user_identifier, self.user_type)
            if not user_info:
                await interaction.followup.send(
                    "❌ User not found! Please provide a valid Roblox username, Roblox user ID, Discord user ID, or Discord mention.",
                    ephemeral=True
                )
                return
            
            # Handle manual registration for Discord users not in database
            if user_info.get('needs_manual_registration'):
                print(f"[DEBUG] User needs manual registration")
                
                # Check if we have Roblox info
                if not user_info.get('roblox_user_id'):
                    error_msg = user_info.get('error', 'Could not find Roblox user')
                    await interaction.followup.send(
                        f"❌ {error_msg}",
                        ephemeral=True
                    )
                    return
                
                discord_id = user_info['discord_user_id']
                roblox_user_id = user_info['roblox_user_id']
                roblox_username = user_info['roblox_username']
                
                # Attempt manual registration
                registration_result = await self.utils.manual_register_user(
                    discord_id,
                    roblox_user_id,
                    roblox_username,
                    self.selected_rank
                )
                
                if not registration_result['success']:
                    await interaction.followup.send(
                        f"❌ Manual registration failed: {registration_result['error']}",
                        ephemeral=True
                    )
                    return
                
                print(f"[DEBUG] Manual registration successful for {registration_result['roblox_username']}")
                
                # Update user_info with registration results
                user_info = {
                    'roblox_user_id': registration_result['roblox_user_id'],
                    'roblox_username': registration_result['roblox_username'],
                    'discord_user_id': discord_id,
                    'in_database': True,
                    'type': registration_result['target_category']
                }
                
                # Update Discord roles
                new_role_info = get_role_by_name(self.selected_rank)
                if new_role_info:
                    new_discord_role_id = new_role_info[1]
                    new_category = new_role_info[3]
                    
                    discord_success = await self.utils.change_discord_rank(
                        interaction.guild,
                        discord_id,
                        new_discord_role_id,
                        new_category,
                        None
                    )
                    
                    if discord_success:
                        author_name = interaction.user.display_name
                        await interaction.followup.send(
                            f"> ✅ Successfully registered and ranked {registration_result['roblox_username']} to {self.selected_rank} by {author_name}",
                            ephemeral=False
                        )
                        return
                    else:
                        await interaction.followup.send(
                            f"❌ Manual registration successful but failed to update Discord roles. Check logs.",
                            ephemeral=True
                        )
                        return

            # Normal rank change flow
            roblox_user_id = user_info['roblox_user_id']
            roblox_username = user_info['roblox_username']
            discord_user_id = user_info.get('discord_user_id')
            in_database = user_info.get('in_database', True)

            print(f"[DEBUG] Found user info: {roblox_username} (ID: {roblox_user_id}), Discord: {discord_user_id}, In DB: {in_database}")

            current_rank_info = await self.utils.get_current_rank_info(roblox_user_id, discord_user_id)
            
            new_role_info = get_role_by_name(self.selected_rank)
            if not new_role_info:
                await interaction.followup.send(f"❌ Rank '{self.selected_rank}' not found in database!", ephemeral=True)
                return

            new_roblox_role_id = new_role_info[2]
            new_discord_role_id = new_role_info[1]
            new_category = new_role_info[3]

            print(f"[DEBUG] Target role info: {self.selected_rank} (Roblox ID: {new_roblox_role_id}, Discord ID: {new_discord_role_id}, Category: {new_category})")

            result = await self.utils.execute_rank_change(
                interaction, roblox_user_id, roblox_username, discord_user_id,
                current_rank_info, new_roblox_role_id, new_discord_role_id, new_category, in_database, user_info
            )

            if result:
                author_name = interaction.user.display_name
                if not in_database:
                    await interaction.followup.send(f"> ✅ Successfully ranked {roblox_username} to {self.selected_rank} on Roblox by {author_name} (user not in database)", ephemeral=False)
                else:
                    await interaction.followup.send(f"> ✅ Successfully changed {roblox_username}'s rank to {self.selected_rank} by {author_name}", ephemeral=False)
            else:
                await interaction.followup.send("❌ Failed to change user's rank. Check logs for details.", ephemeral=True)

        except Exception as e:
            print(f"[ERROR] Error in process_rank_change: {e}")
            import traceback
            traceback.print_exc()
            try:
                await interaction.followup.send(f"❌ Error processing rank change: {str(e)}", ephemeral=True)
            except:
                pass

class DemotionView(discord.ui.View):
    def __init__(self, user_identifier: str, user_type: str, reason: str, utils):
        super().__init__(timeout=60)
        self.user_identifier = user_identifier
        self.user_type = user_type
        self.reason = reason
        self.utils = utils

    @discord.ui.button(label="Demote User", style=discord.ButtonStyle.red)
    async def demote_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.process_demotion(interaction)

    async def process_demotion(self, interaction: discord.Interaction):
        try:
            user_info = await self.utils.get_user_info(self.user_identifier, self.user_type)
            if not user_info:
                await interaction.followup.send("❌ User not found!", ephemeral=True)
                return

            roblox_user_id = user_info['roblox_user_id']
            roblox_username = user_info['roblox_username']
            discord_user_id = user_info.get('discord_user_id')
            in_database = user_info.get('in_database', True)

            current_rank_info = await self.utils.get_current_rank_info(roblox_user_id, discord_user_id)
            current_rank_name = self.utils.get_current_rank_name(current_rank_info)
            
            if not current_rank_name and discord_user_id:
                current_rank_name = self.utils.get_current_rank_name_from_discord_roles(interaction.guild, discord_user_id)
            
            if not current_rank_name:
                await interaction.followup.send("❌ Could not determine user's current rank!", ephemeral=True)
                return

            if current_rank_name not in STAFF_ROLES:
                await interaction.followup.send(f"❌ User {roblox_username} is not a staff member and cannot be demoted!", ephemeral=True)
                return

            current_category = current_rank_info.get('category') if current_rank_info else None
            
            if current_category == "staff_silver":
                new_rank_name = "custodian"
            elif current_category == "staff":
                new_rank_name = "admittee"
            else:
                new_rank_name = "admittee"

            new_role_info = get_role_by_name(new_rank_name)
            if not new_role_info:
                await interaction.followup.send(f"❌ Rank '{new_rank_name}' not found in database!", ephemeral=True)
                return

            new_roblox_role_id = new_role_info[2]
            new_discord_role_id = new_role_info[1]
            new_category = new_role_info[3]

            result = await self.utils.execute_rank_change(
                interaction, roblox_user_id, roblox_username, discord_user_id,
                current_rank_info, new_roblox_role_id, new_discord_role_id, new_category, in_database, user_info
            )

            if result:
                author_name = interaction.user.display_name
                if not in_database:
                    await interaction.followup.send(f"> ✅ Successfully demoted {roblox_username} to {new_rank_name} on Roblox by {author_name} (user not in database)", ephemeral=False)
                else:
                    await interaction.followup.send(f"> ✅ Successfully demoted {roblox_username} from {current_rank_name} to {new_rank_name} by {author_name}", ephemeral=False)
                
                if discord_user_id:
                    await self.utils.send_demotion_dm(interaction.guild, discord_user_id, current_rank_name, new_rank_name, self.reason, author_name)
            else:
                await interaction.followup.send("❌ Failed to demote user. Check logs for details.", ephemeral=True)
            
        except Exception as e:
            print(f"Error in process_demotion: {e}")
            await interaction.followup.send(f"❌ Error processing demotion: {str(e)}", ephemeral=True)

class StaffApprovalView(discord.ui.View):
    def __init__(self, roblox_user_id: str):
        super().__init__(timeout=None)
        self.roblox_user_id = roblox_user_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, custom_id="approve_staff")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.process_approval(interaction, True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, custom_id="deny_staff")
    async def deny_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        await self.process_approval(interaction, False)

    async def process_approval(self, interaction: discord.Interaction, approved: bool):
        try:
            hr_plus_role_ids = [
                942019580921008188,
                942019582741323826,
                943123573592195112,
                942019581986340864,
                943947211551678564,
                942019588500127795
            ]
            
            user_roles = [role.id for role in interaction.user.roles]
            has_hr_plus = any(role_id in user_roles for role_id in hr_plus_role_ids)
            
            if not has_hr_plus:
                await interaction.followup.send("❌ You need HR+ permissions to approve staff!", ephemeral=True)
                return
            
            from database import get_pending_staff, remove_pending_staff, add_staff_member, get_role_by_name
            
            pending_staff = get_pending_staff(self.roblox_user_id)
            
            if not pending_staff:
                await interaction.followup.send("❌ Staff request not found or already processed!", ephemeral=True)
                return

            roblox_user_id, roblox_username, discord_user_id = pending_staff[1], pending_staff[2], pending_staff[3]
            
            if approved:
                undocumented_role = get_role_by_name("undocumented")
                if not undocumented_role:
                    await interaction.followup.send("❌ Undocumented role not found in database!", ephemeral=True)
                    return

                try:
                    add_staff_member(roblox_user_id, roblox_username, discord_user_id, undocumented_role[2], "staff")
                except Exception as e:
                    await interaction.followup.send("❌ Error adding staff member to database!", ephemeral=True)
                    return
                
                if discord_user_id:
                    try:
                        guild = interaction.guild
                        
                        if not guild.me.guild_permissions.manage_roles:
                            await interaction.followup.send("⚠️ Bot lacks 'Manage Roles' permission - Discord role assignment skipped", ephemeral=True)
                        else:
                            member = await guild.fetch_member(int(discord_user_id))
                            if member:
                                # Remove patient roles
                                patient_roles_to_remove = []
                                from database import SPECIAL_ROLES, get_roles_by_category
                                
                                # Get all patient category roles from database
                                patient_roles = get_roles_by_category("patient")
                                for role_info in patient_roles:
                                    role_name, discord_role_id, _, _ = role_info
                                    if discord_role_id and discord_role_id != "None":
                                        role = guild.get_role(int(discord_role_id))
                                        if role and role in member.roles:
                                            patient_roles_to_remove.append(role)
                                
                                # Also remove special patient roles
                                true_patient_role = guild.get_role(int(SPECIAL_ROLES["true_patient"]))
                                untrue_patient_role = guild.get_role(int(SPECIAL_ROLES["untrue_patient"]))
                                
                                if true_patient_role and true_patient_role in member.roles:
                                    patient_roles_to_remove.append(true_patient_role)
                                
                                if untrue_patient_role and untrue_patient_role in member.roles:
                                    patient_roles_to_remove.append(untrue_patient_role)
                                
                                # Remove all patient roles
                                for role in patient_roles_to_remove:
                                    try:
                                        await member.remove_roles(role)
                                    except Exception as e:
                                        pass
                                
                                # Add undocumented role
                                undocumented_discord_role = guild.get_role(int(undocumented_role[1]))
                                if undocumented_discord_role:
                                    await member.add_roles(undocumented_discord_role)
                                
                                # Add true staff and clinic maids roles
                                true_staff_role = guild.get_role(int(SPECIAL_ROLES["true_staff"]))
                                clinic_maids_role = guild.get_role(int(SPECIAL_ROLES["clinic_maids"]))
                                
                                if true_staff_role:
                                    await member.add_roles(true_staff_role)
                                
                                if clinic_maids_role:
                                    await member.add_roles(clinic_maids_role)
                                
                    except Exception as e:
                        await interaction.followup.send("⚠️ Discord role assignment failed, but Roblox ranking was successful", ephemeral=True)
                
                # Ensure Roblox ranking happens
                try:
                    import requests
                    import os
                    
                    # Get Roblox login cookie from environment
                    roblox_cookie = os.getenv('ROBLOX_LOGIN_COOKIE')
                    if not roblox_cookie:
                        await interaction.followup.send("⚠️ Roblox ranking failed - no login cookie configured", ephemeral=True)
                    else:
                        # Simple Roblox ranking implementation
                        session = requests.Session()
                        session.cookies.set('.ROBLOSECURITY', roblox_cookie, domain='.roblox.com')
                        
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                            'Content-Type': 'application/json',
                            'Accept': 'application/json, text/plain, */*'
                        }
                        
                        # Get CSRF token
                        auth_url = "https://auth.roblox.com/v2/logout"
                        xsrf_response = session.post(auth_url, headers=headers)
                        xsrf_token = xsrf_response.headers.get('x-csrf-token')
                        
                        if xsrf_token:
                            headers['x-csrf-token'] = xsrf_token
                            
                            # Rank the user
                            from database import ROBLOX_GROUP_ID
                            url = f"https://groups.roblox.com/v1/groups/{ROBLOX_GROUP_ID}/users/{roblox_user_id}"
                            data = {"roleId": int(undocumented_role[2])}
                            response = session.patch(url, headers=headers, json=data)
                            
                            if response.status_code != 200:
                                await interaction.followup.send("⚠️ Roblox ranking failed, but Discord roles were updated", ephemeral=True)
                        else:
                            await interaction.followup.send("⚠️ Roblox ranking failed - authentication issue", ephemeral=True)
                            
                except Exception as e:
                    await interaction.followup.send("⚠️ Roblox ranking failed, but Discord roles were updated", ephemeral=True)
                
                await interaction.followup.send(f"✅ **{roblox_username}** has been approved and added as staff member!", ephemeral=False)
                
                # Send log to specified channel
                try:
                    log_channel = guild.get_channel(1262033245101490296)
                    if log_channel:
                        await log_channel.send(f"> Staff gamepass purchase made by {roblox_username} was accepted by {interaction.user.display_name}")
                except Exception as e:
                    pass
                    
            else:
                await interaction.followup.send(f"❌ **{roblox_username}**'s staff request has been denied.", ephemeral=False)
                
                # Send log to specified channel
                try:
                    log_channel = interaction.guild.get_channel(1262033245101490296)
                    if log_channel:
                        await log_channel.send(f"> Staff gamepass purchase made by {roblox_username} was rejected by {interaction.user.display_name}")
                except Exception as e:
                    pass
            
            try:
                remove_pending_staff(self.roblox_user_id)
            except Exception as e:
                pass
            
            if interaction.message.embeds:
                embed = interaction.message.embeds[0]
                embed.color = discord.Color.green() if approved else discord.Color.red()
                embed.add_field(name="Status", value="Approved" if approved else "Denied", inline=True)
                embed.add_field(name="Processed by", value=interaction.user.display_name, inline=True)
                
                try:
                    await interaction.message.edit(embed=embed, view=None)
                except Exception as e:
                    await interaction.followup.send("⚠️ Failed to update message embed, but staff approval was successful", ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error processing staff approval: {str(e)}", ephemeral=True)
