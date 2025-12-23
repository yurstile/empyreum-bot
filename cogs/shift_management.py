import discord
from discord.ext import commands
from discord import app_commands

from database import (
    get_roles_by_category,
    get_role_by_discord_id,
    create_shift,
    get_active_shift_by_user,
    end_shift_by_user,
    get_all_active_shifts,
    end_all_shifts,
    get_last_ended_shift,
)


SHIFT_ANNOUNCEMENT_CHANNEL_ID = 1405867800479797309
PING_ROLE_ID = 942081105362841661
ADMIN_OVERRIDE_ROLE_IDS = {
    942019581986340864,  # override role
    942019580921008188,  # override role
    942019582741323826,  # override role
    943123573592195112,  
    943122610491895819,
    942019588500127795,
}


def staff_only_except_undocumented():
    async def predicate(interaction: discord.Interaction):
        try:
            # Allow override roles unconditionally
            if any(role.id in ADMIN_OVERRIDE_ROLE_IDS for role in interaction.user.roles):
                return True

            # Staff roles category excludes undocumented
            staff_role_names = {
                "noviciate", "attendant", "warden", "custodian", "concierge", "lecturer"
            }
            user_role_ids = {role.id for role in interaction.user.roles}
            # Map Discord role IDs to role names via DB
            allowed = False
            for role in interaction.user.roles:
                db_role = get_role_by_discord_id(str(role.id))
                if db_role:
                    role_name = db_role[0]
                    if role_name in staff_role_names:
                        allowed = True
                        break
            if not allowed:
                await interaction.response.send_message(
                    "❌ This command is restricted to staff roles (excluding undocumented).",
                    ephemeral=True,
                )
                return False
            return True
        except Exception:
            await interaction.response.send_message(
                "❌ Unable to verify your roles right now.", ephemeral=True
            )
            return False
    return app_commands.check(predicate)


def concierge_lecturer_only():
    async def predicate(interaction: discord.Interaction):
        try:
            # Allow override roles unconditionally
            if any(role.id in ADMIN_OVERRIDE_ROLE_IDS for role in interaction.user.roles):
                return True

            required_names = {"concierge", "lecturer"}
            for role in interaction.user.roles:
                db_role = get_role_by_discord_id(str(role.id))
                if db_role and db_role[0] in required_names:
                    return True
            await interaction.response.send_message(
                "❌ This command is restricted to Concierge and Lecturer.",
                ephemeral=True,
            )
            return False
        except Exception:
            await interaction.response.send_message(
                "❌ Unable to verify your roles right now.", ephemeral=True
            )
            return False
    return app_commands.check(predicate)


class ShiftManagement(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="startshift", description="Start your asylum shift announcement.")
    @staff_only_except_undocumented()
    async def startshift(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            # Prevent duplicate active shift for the same user
            active = get_active_shift_by_user(str(interaction.user.id))
            if active:
                await interaction.followup.send(
                    "❌ You already have an ongoing shift.", ephemeral=True
                )
                return

            last_ended = get_last_ended_shift(str(interaction.user.id))
            if last_ended:
                try:
                    from datetime import datetime
                    ended_dt = None
                    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
                        try:
                            ended_dt = datetime.strptime(str(last_ended), fmt)
                            break
                        except ValueError:
                            continue
                    if ended_dt is None:
                        try:
                            ended_dt = datetime.fromisoformat(str(last_ended).replace('Z', '+00:00'))
                        except Exception:
                            ended_dt = None
                    if ended_dt is not None:
                        from datetime import timedelta
                        remaining = (ended_dt + timedelta(minutes=10)) - datetime.utcnow()
                        if remaining.total_seconds() > 0:
                            minutes = int(remaining.total_seconds() // 60)
                            seconds = int(remaining.total_seconds() % 60)
                            await interaction.followup.send(
                                f"⏳ You can start a new shift in {minutes}m {seconds}s.",
                                ephemeral=True,
                            )
                            return
                except Exception:
                    pass

            channel = self.bot.get_channel(SHIFT_ANNOUNCEMENT_CHANNEL_ID)
            if channel is None:
                await interaction.followup.send(
                    "❌ Shift announcement channel not found.", ephemeral=True
                )
                return

            mention_str = interaction.user.mention
            content_lines = [
                ":exclamation: 𝐀𝐒𝐘𝐋𝐔𝐌 𝐕𝐈𝐒𝐈𝐓 :exclamation:",
                f"<@&{PING_ROLE_ID}>",
                f"Greetings all patients! It seems like {mention_str} has started their shift at the asylum. You're welcome to join! Hope to see you there...",
                "",
                "CURRENT STATUS: 🟢 ONGOING",
                "",
                "Join using the link below.",
                "",
                "📎  https://www.roblox.com/games/9171458073/Empyreal-Lunatic-Asylum",
            ]
            message = await channel.send("\n".join(content_lines))

            create_shift(str(interaction.user.id), str(message.id))

            await interaction.followup.send(
                f"✅ Shift started. Announcement posted in <#{SHIFT_ANNOUNCEMENT_CHANNEL_ID}>.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @app_commands.command(name="stopshift", description="Stop your current shift announcement.")
    async def stopshift(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            message_id = end_shift_by_user(str(interaction.user.id))
            if not message_id:
                await interaction.followup.send(
                    "❌ You do not have an active shift.", ephemeral=True
                )
                return

            channel = self.bot.get_channel(SHIFT_ANNOUNCEMENT_CHANNEL_ID)
            if channel is None:
                await interaction.followup.send(
                    "⚠️ Shift ended in database, but channel not found to edit message.",
                    ephemeral=True,
                )
                return

            try:
                msg = await channel.fetch_message(int(message_id))
            except discord.NotFound:
                await interaction.followup.send(
                    "⚠️ Shift ended in database, but announcement message was not found.",
                    ephemeral=True,
                )
                return

            lines = msg.content.split("\n")
            for idx, line in enumerate(lines):
                if line.startswith("CURRENT STATUS:"):
                    lines[idx] = "CURRENT STATUS: 🔴 ENDED, thank you for coming!"
                    break
            await msg.edit(content="\n".join(lines))

            await interaction.followup.send("✅ Shift ended and announcement updated.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @app_commands.command(name="stopallshifts", description="End all active shifts and update announcements.")
    @concierge_lecturer_only()
    async def stopallshifts(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)

            message_ids = end_all_shifts()
            channel = self.bot.get_channel(SHIFT_ANNOUNCEMENT_CHANNEL_ID)

            updated = 0
            if channel is not None:
                for mid in message_ids:
                    try:
                        msg = await channel.fetch_message(int(mid))
                        lines = msg.content.split("\n")
                        for idx, line in enumerate(lines):
                            if line.startswith("CURRENT STATUS:"):
                                lines[idx] = "CURRENT STATUS: 🔴 ENDED, thank you for coming!"
                                break
                        await msg.edit(content="\n".join(lines))
                        updated += 1
                    except discord.NotFound:
                        continue

            await interaction.followup.send(
                f"✅ Ended {len(message_ids)} shifts. Updated {updated} announcement messages.",
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ShiftManagement(bot))


