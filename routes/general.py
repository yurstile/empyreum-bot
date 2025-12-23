from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
import requests
import os
from database import get_pending_verifications, get_pending_by_username, remove_pending_verification, add_verified_user, get_role_by_name, get_verified_user_by_roblox_id, add_pending_staff, remove_pending_staff, add_staff_member, GUILD_ID, WELCOME_CHANNEL_ID, STAFF_REQUEST_CHANNEL_ID, ROBLOX_GROUP_ID, increment_excellence_score
from typing import Optional
import discord
from datetime import datetime
import sqlite3

class RegistrationRequest(BaseModel):
    username: str
    user_id: str

class RankRequest(BaseModel):
    user_id: str

class NewStaffRequest(BaseModel):
    roblox_user_id: str

class StaffScoreLogRequest(BaseModel):
    roblox_user_id: str
    excellence_score: int



router = APIRouter()

API_KEY = "EVELUCINATE_HasStolenMyTemu-Dilldough"
BEARER_TOKEN = "1iruyUPUbpTLDQuVdPwbmNCRPzYm9CJB"

async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

async def verify_bearer_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    if token != BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid bearer token")
    
    return token

def get_bot():
    try:
        from bot_instance import get_bot as get_bot_instance
        return get_bot_instance()
    except Exception:
        return None

@router.get("/pending-registrations")
async def get_pending(api_key: str = Depends(verify_api_key)):
    pending = get_pending_verifications()
    return {"pending": [{"discord_id": p[0], "username": p[1], "created_at": p[2]} for p in pending]}

@router.post("/complete-registration")
async def complete_registration(request: RegistrationRequest, api_key: str = Depends(verify_api_key)):
    username = request.username
    roblox_user_id = request.user_id
    pending_user = get_pending_by_username(username)
    if not pending_user:
        raise HTTPException(status_code=404, detail="User not found in pending verification")
    
    discord_id, username, created_at = pending_user
    
    try:
        patient_role = get_role_by_name("patient")
        true_patient_role = get_role_by_name("true patient")
        
        if not patient_role or not true_patient_role:
            raise HTTPException(status_code=500, detail="Required roles not found in database")
        
        roblox_rank_id = patient_role[2]
        if not roblox_rank_id:
            raise HTTPException(status_code=500, detail="Roblox rank ID not found for patient role")
        
        success = await rank_roblox_user(roblox_user_id, roblox_rank_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to rank user on Roblox")
        
        bot = get_bot()
        
        if not bot:
            raise HTTPException(status_code=503, detail="Bot is not ready yet. Please try again in a few seconds.")
        
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            raise HTTPException(status_code=500, detail="Guild not found")
        
        member = await guild.fetch_member(int(discord_id))
        if not member:
            raise HTTPException(status_code=404, detail="Discord member not found")
        
        admittee_role = get_role_by_name("admittee")
        admittee_discord_role = guild.get_role(int(admittee_role[1])) if admittee_role else None
        patient_discord_role = guild.get_role(int(patient_role[1]))
        true_patient_discord_role = guild.get_role(int(true_patient_role[1]))
        
        if admittee_discord_role and admittee_discord_role in member.roles:
            await member.remove_roles(admittee_discord_role)
        
        if patient_discord_role:
            await member.add_roles(patient_discord_role)
        
        if true_patient_discord_role:
            await member.add_roles(true_patient_discord_role)
        
        remove_pending_verification(discord_id)
        
        add_verified_user(discord_id, username, roblox_user_id)
        
        welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)
        if welcome_channel:
            await welcome_channel.send(f"> **<@{discord_id}>** has completed registration and is now one of us, welcome aboard.")
        
        return {"success": True, "message": "Registration completed successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rank-lunatic-patient")
async def rank_lunatic_patient(request: RankRequest, api_key: str = Depends(verify_api_key)):
    user_id = request.user_id
    
    try:
        lunatic_patient_role = get_role_by_name("lunatic patient")
        if not lunatic_patient_role:
            raise HTTPException(status_code=500, detail="Lunatic patient role not found in database")
        
        roblox_rank_id = lunatic_patient_role[2]
        if not roblox_rank_id:
            raise HTTPException(status_code=500, detail="Roblox rank ID not found for lunatic patient role")
        
        success = await rank_roblox_user(user_id, roblox_rank_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to rank user on Roblox")
        
        return {"success": True, "message": "User ranked successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def rank_new_staff_internal(roblox_user_id: str):
    try:
        verified_user = get_verified_user_by_roblox_id(roblox_user_id)
        if not verified_user:
            raise Exception("User not found in verified users")
        
        discord_id, username, _, verified_at = verified_user
        
        undocumented_role = get_role_by_name("undocumented")
        true_staff_role = get_role_by_name("true staff")
        clinic_maids_role = get_role_by_name("clinic maids")
        
        if not undocumented_role:
            raise Exception("Undocumented role not found in database")
        
        roblox_rank_id = undocumented_role[2]
        if not roblox_rank_id:
            raise Exception("Roblox rank ID not found for undocumented role")
        
        success = await rank_roblox_user(roblox_user_id, roblox_rank_id)
        if not success:
            raise Exception("Failed to rank user on Roblox")
        
        bot = get_bot()
        if not bot:
            raise Exception("Bot is not ready yet. Please try again in a few seconds.")
        
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            raise Exception("Guild not found")
        
        member = await guild.fetch_member(int(discord_id))
        if not member:
            raise Exception("Discord member not found")
        
        patient_roles = [
            get_role_by_name("admittee"),
            get_role_by_name("patient"), 
            get_role_by_name("lunatic patient"),
            get_role_by_name("honored patient"),
            get_role_by_name("untrue patient"),
            get_role_by_name("true patient")
        ]
        
        for patient_role_info in patient_roles:
            if patient_role_info:
                patient_discord_role = guild.get_role(int(patient_role_info[1]))
                if patient_discord_role and patient_discord_role in member.roles:
                    await member.remove_roles(patient_discord_role)
        
        undocumented_discord_role = guild.get_role(int(undocumented_role[1]))
        if undocumented_discord_role:
            await member.add_roles(undocumented_discord_role)
        
        if true_staff_role:
            true_staff_discord_role = guild.get_role(int(true_staff_role[1]))
            if true_staff_discord_role:
                await member.add_roles(true_staff_discord_role)
        
        if clinic_maids_role:
            clinic_maids_discord_role = guild.get_role(int(clinic_maids_role[1]))
            if clinic_maids_discord_role:
                await member.add_roles(clinic_maids_discord_role)
        
        add_staff_member(roblox_user_id, username, discord_id, roblox_rank_id, "staff")
        
        remove_pending_staff(roblox_user_id)
        
        return {"success": True, "message": "Staff member ranked successfully"}
        
    except Exception as e:
        raise e

@router.post("/rank-new-staff")
async def rank_new_staff(request: RankRequest, api_key: str = Depends(verify_api_key)):
    try:
        result = await rank_new_staff_internal(request.user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/new-staff-request")
async def new_staff_request(request: NewStaffRequest, api_key: str = Depends(verify_api_key)):
    roblox_user_id = request.roblox_user_id
    
    try:
        verified_user = get_verified_user_by_roblox_id(roblox_user_id)

        discord_id, username, _, verified_at = verified_user
        
        roblox_info = await get_roblox_user_info(roblox_user_id)
        if not roblox_info:
            raise HTTPException(status_code=500, detail="Failed to fetch Roblox user information")

        add_pending_staff(roblox_user_id, roblox_info['username'], discord_id)
        
        bot = get_bot()
        
        channel = bot.get_channel(STAFF_REQUEST_CHANNEL_ID)
        if not channel:
            raise HTTPException(status_code=500, detail="Staff request channel not found")
        
        embed = await create_staff_request_embed(roblox_info, discord_id, roblox_user_id)
        
        from cogs.staff_management import StaffApprovalView
        
        view = StaffApprovalView(roblox_user_id)
        
        message = await channel.send(embed=embed, view=view)
        
        return {"success": True, "message": "Staff request sent successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/staff-score-log")
async def staff_score_log(request: StaffScoreLogRequest, api_key: str = Depends(verify_api_key)):
    try:
        conn = sqlite3.connect('roles.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at
            FROM staff
            WHERE roblox_user_id = ?
        ''', (request.roblox_user_id,))
        
        staff_member = cursor.fetchone()
        
        if not staff_member:
            conn.close()
            raise HTTPException(status_code=404, detail="Staff member not found")
        
        if staff_member[4]:
            cursor.execute('''
                UPDATE staff
                SET evaluation_week_score = evaluation_week_score + ?
                WHERE roblox_user_id = ?
            ''', (request.excellence_score, request.roblox_user_id))
            
            conn.commit()
            conn.close()
            
            return {"success": True, "message": f"Added {request.excellence_score} to weekly evaluation score for {staff_member[1]} (evaluation mode)"}
        
        cursor.execute('''
            UPDATE staff
            SET excellence_score = excellence_score + ?
            WHERE roblox_user_id = ?
        ''', (request.excellence_score, request.roblox_user_id))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": f"Added {request.excellence_score} excellence score to {staff_member[1]}"}
        
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/staff-info/{roblox_user_id}")
async def get_staff_info(roblox_user_id: str, api_key: str = Depends(verify_api_key)):
    try:
        conn = sqlite3.connect('roles.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at
            FROM staff
            WHERE roblox_user_id = ?
        ''', (roblox_user_id,))
        
        staff_member = cursor.fetchone()
        
        if not staff_member:
            conn.close()
            raise HTTPException(status_code=404, detail="Staff member not found")
        
        roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at = staff_member
        
        cursor.execute('''
            SELECT roblox_user_id
            FROM staff_inactivity
            WHERE roblox_user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        ''', (roblox_user_id,))
        
        inactivity_record = cursor.fetchone()
        is_inactive = inactivity_record is not None
        
        conn.close()
        
        return {
            "success": True,
            "staff_info": {
                "excellence": excellences,
                "excellence_score": excellence_score,
                "bad_streak": bad_streak,
                "minimum_streak": minimum_streak,
                "evaluation_week_score": evaluation_week_score,
                "is_inactive": is_inactive
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def rank_roblox_user(user_id, rank_id):
    try:
        cookie = os.getenv('ROBLOX_LOGIN_COOKIE')
        if not cookie:
            return False
        
        session = requests.Session()
        session.cookies.set('.ROBLOSECURITY', cookie, domain='.roblox.com')
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/plain, */*',
            'Referer': 'https://www.roblox.com/',
            'Origin': 'https://www.roblox.com'
        }
        
        auth_url = "https://auth.roblox.com/v2/logout"
        xsrf_response = session.post(auth_url, headers=headers)
        
        xsrf_token = xsrf_response.headers.get('x-csrf-token')
        if not xsrf_token:
            return False
        
        headers['x-csrf-token'] = xsrf_token
        
        url = f"https://groups.roblox.com/v1/groups/{ROBLOX_GROUP_ID}/users/{user_id}"
        data = {"roleId": int(rank_id)}
        response = session.patch(url, headers=headers, json=data)
        
        return response.status_code == 200
    except Exception:
        return False

async def get_roblox_user_info(user_id):
    try:
        response = requests.get(f"https://users.roblox.com/v1/users/{user_id}")
        if response.status_code == 200:
            data = response.json()
            return {
                'username': data.get('name', 'Unknown'),
                'displayName': data.get('displayName', 'Unknown'),
                'created': data.get('created', 'Unknown'),
                'avatar_url': f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=false"
            }
        return None
    except Exception:
        return None

async def create_staff_request_embed(roblox_info, discord_id, roblox_user_id):
    embed = discord.Embed(
        title="New Staff Purchase",
        description=f"{roblox_info['username']} has bought staff gamepass. Please approve or reject this purchase.",
        color=0x00ff00,
        timestamp=datetime.utcnow()
    )
    
    try:
        created_date = datetime.fromisoformat(roblox_info['created'].replace('Z', '+00:00'))
        formatted_created = created_date.strftime("%d %B, %Y")
    except:
        formatted_created = roblox_info['created']
    
    embed.add_field(name="Roblox Username", value=roblox_info['username'], inline=True)
    embed.add_field(name="Roblox User ID", value=roblox_user_id, inline=True)
    embed.add_field(name="Discord User ID", value=discord_id, inline=True)
    embed.add_field(name="Account Creation", value=formatted_created, inline=True)
    embed.add_field(name="Requested At", value=datetime.utcnow().strftime("%d %B, %Y at %I:%M %p UTC"), inline=True)

    try:
        avatar_response = requests.get(roblox_info['avatar_url'])
        if avatar_response.status_code == 200:
            avatar_data = avatar_response.json()
            if avatar_data.get('data') and len(avatar_data['data']) > 0:
                avatar_url = avatar_data['data'][0]['imageUrl']
                embed.set_thumbnail(url=avatar_url)
    except:
        pass 
    
    embed.set_footer(text="Click the buttons below to approve or reject this purchase")
    
    return embed


