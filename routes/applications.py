from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import requests
import os
from database import get_applications, get_application_by_id, delete_application, add_application, find_discord_id_by_roblox_username, add_passer, check_existing_application
from typing import Optional
import discord
from datetime import datetime
import jwt
import json

class ApplicationRequest(BaseModel):
    roblox_user_id: str
    roblox_username: str
    chat_filter_triggered: bool
    communication_server_verified: bool
    country_timezone: str
    device_choice: str
    activity_level: int
    discovery_method: str
    previous_experience: str = None
    motivation: str
    handling_disrespect: str
    personality_description: str
    special_abilities: str = None
    benefits_to_group: str
    perception_of_role: str

class ApplicationActionRequest(BaseModel):
    application_id: int

class OAuthCallbackRequest(BaseModel):
    code: str

router = APIRouter(prefix="/applications", tags=["applications"])

API_KEY = "Why7IW19CA"
DISCORD_CLIENT_ID = "1279845296263790622"
DISCORD_CLIENT_SECRET = "2zdfTwlAgo1Xpny8GUaTRqv_bqNyAIGF"
DISCORD_REDIRECT_URI = "https://empyreum-api.yurstile.lol/applications/oauth/callback"
DISCORD_BOT_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = 941998687779954708
NOTIFICATION_CHANNEL_ID = 1262033245101490296
AUTHORIZED_ROLES = [
    943123573592195112,
    942019581986340864,
    942019582741323826,
    942019580921008188,
    942019588500127795,
    1409201856806129756
]

JWT_SECRET = "605adff118c56481af6681d0a2425da9049057d6990ec0a447488bebddc8be48"

def get_bot():
    try:
        from bot_instance import get_bot as get_bot_instance
        return get_bot_instance()
    except Exception:
        return None

async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

async def verify_discord_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        import time
        current_time = int(time.time())
        
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        
        discord_user_id = payload.get("discord_user_id")
        
        if not discord_user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        bot = get_bot()
        if not bot:
            raise HTTPException(status_code=503, detail="Bot is not ready")
        
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            raise HTTPException(status_code=500, detail="Guild not found")
        
        member = await guild.fetch_member(int(discord_user_id))
        if not member:
            raise HTTPException(status_code=401, detail="User not found in guild")
        
        user_roles = [role.id for role in member.roles]
        has_authorized_role = any(role_id in user_roles for role_id in AUTHORIZED_ROLES)
        
        if not has_authorized_role:
            raise HTTPException(status_code=403, detail="Access denied: Insufficient permissions")
        
        return {
            "discord_user_id": discord_user_id,
            "display_name": member.display_name,
            "member": member
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Login expired. Please login again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Token verification failed")

async def send_discord_notification(message: str):
    try:
        bot = get_bot()
        if not bot:
            return
        
        channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
        if not channel:
            return
        
        await channel.send(message)
    except Exception:
        pass

@router.get("/oauth/login")
async def discord_oauth_login():
    oauth_url = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URI}&response_type=code&scope=identify"
    return {"oauth_url": oauth_url}

@router.get("/oauth/callback")
async def discord_oauth_callback_get(code: str):
    try:
        token_url = "https://discord.com/api/oauth2/token"
        data = {
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT_URI
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")
        
        user_response = requests.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        user_data = user_response.json()
        discord_user_id = user_data.get("id")
        
        if not discord_user_id:
            raise HTTPException(status_code=400, detail="No user ID in response")
        
        bot = get_bot()
        if not bot:
            raise HTTPException(status_code=503, detail="Bot is not ready")
        
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            raise HTTPException(status_code=500, detail="Guild not found")
        
        member = await guild.fetch_member(int(discord_user_id))
        if not member:
            raise HTTPException(status_code=401, detail="User not found in guild")
        
        user_roles = [role.id for role in member.roles]
        has_authorized_role = any(role_id in user_roles for role_id in AUTHORIZED_ROLES)
        
        if not has_authorized_role:
            raise HTTPException(status_code=403, detail="Access denied: Insufficient permissions")
        
        import time
        current_time = int(time.time())
        expiration_time = current_time + (2 * 60 * 60)
        
        jwt_token = jwt.encode(
            {
                "discord_user_id": discord_user_id,
                "display_name": member.display_name,
                "exp": expiration_time
            },
            JWT_SECRET,
            algorithm="HS256"
        )
        
        frontend_url = "https://empyreum.yurstile.lol"
        redirect_url = f"{frontend_url}?token={jwt_token}&user_id={discord_user_id}&username={member.display_name}"
        
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        error_detail = str(e)
        frontend_url = "https://empyreum.yurstile.lol"
        
        if "User not found in guild" in error_detail:
            redirect_url = f"{frontend_url}?error=member_not_found&error_description=User not found in guild"
        elif "Access denied: Insufficient permissions" in error_detail:
            redirect_url = f"{frontend_url}?error=insufficient_permissions&error_description=Access denied: Insufficient permissions"
        elif "Unknown Member" in error_detail:
            redirect_url = f"{frontend_url}?error=unknown_member&error_description=Unknown Member"
        elif "Bot is not ready" in error_detail:
            redirect_url = f"{frontend_url}?error=service_unavailable&error_description=Bot is not ready"
        elif "Failed to exchange code for token" in error_detail:
            redirect_url = f"{frontend_url}?error=auth_failed&error_description=Failed to exchange code for token"
        elif "Failed to get user info" in error_detail:
            redirect_url = f"{frontend_url}?error=user_info_error&error_description=Failed to get user info"
        elif "Guild not found" in error_detail:
            redirect_url = f"{frontend_url}?error=guild_not_found&error_description=Guild not found"
        else:
            redirect_url = f"{frontend_url}?error=unknown_error&error_description={error_detail}"
        
        return RedirectResponse(url=redirect_url, status_code=302)

@router.post("/oauth/callback")
async def discord_oauth_callback_post(request: OAuthCallbackRequest):
    try:
        token_url = "https://discord.com/api/oauth2/token"
        data = {
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": request.code,
            "redirect_uri": DISCORD_REDIRECT_URI
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange code for token")
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token received")
        
        user_response = requests.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        user_data = user_response.json()
        discord_user_id = user_data.get("id")
        
        if not discord_user_id:
            raise HTTPException(status_code=400, detail="No user ID in response")
        
        bot = get_bot()
        if not bot:
            raise HTTPException(status_code=503, detail="Bot is not ready")
        
        guild = bot.get_guild(GUILD_ID)
        if not guild:
            raise HTTPException(status_code=500, detail="Guild not found")
        
        member = await guild.fetch_member(int(discord_user_id))
        if not member:
            raise HTTPException(status_code=401, detail="User not found in guild")
        
        user_roles = [role.id for role in member.roles]
        has_authorized_role = any(role_id in user_roles for role_id in AUTHORIZED_ROLES)
        
        if not has_authorized_role:
            raise HTTPException(status_code=403, detail="Access denied: Insufficient permissions")
        
        import time
        current_time = int(time.time())
        expiration_time = current_time + (2 * 60 * 60)
        
        jwt_token = jwt.encode(
            {
                "discord_user_id": discord_user_id,
                "display_name": member.display_name,
                "exp": expiration_time
            },
            JWT_SECRET,
            algorithm="HS256"
        )
        
        frontend_url = "https://empyreum.yurstile.lol"
        redirect_url = f"{frontend_url}?token={jwt_token}&user_id={discord_user_id}&username={member.display_name}"
        
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/submit")
async def submit_application(request: Request, api_key: str = Depends(verify_api_key)):
    try:
        raw_body = await request.body()
        try:
            data = json.loads(raw_body.decode())
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in request body")

        roblox_user_id = data.get("roblox_user_id")
        roblox_username = data.get("roblox_username")
        chat_filter_triggered = data.get("chat_filter_triggered")
        country_timezone = data.get("country_timezone")
        device_choice = data.get("device_choice")
        activity_level = data.get("activity_level")
        discovery_method = data.get("discovery_method")
        previous_experience = data.get("previous_experience")
        motivation = data.get("motivation")
        handling_disrespect = data.get("handling_disrespect")
        personality_description = data.get("personality_description")
        special_abilities = data.get("special_abilities")
        benefits_to_group = data.get("benefits_to_group")
        perception_of_role = data.get("perception_of_role")

        bot = get_bot()
        discord_user_id = find_discord_id_by_roblox_username(roblox_username, bot)
        communication_server_verified = discord_user_id is not None

        add_application(
            roblox_user_id=roblox_user_id,
            roblox_username=roblox_username,
            discord_user_id=discord_user_id,
            chat_filter_triggered=chat_filter_triggered,
            communication_server_verified=communication_server_verified,
            country_timezone=country_timezone,
            device_choice=device_choice,
            activity_level=activity_level,
            discovery_method=discovery_method,
            previous_experience=previous_experience,
            motivation=motivation,
            handling_disrespect=handling_disrespect,
            personality_description=personality_description,
            special_abilities=special_abilities,
            benefits_to_group=benefits_to_group,
            perception_of_role=perception_of_role
        )

        return {
            "success": True,
            "message": "Application submitted successfully",
            "discord_user_id": discord_user_id,
            "communication_server_verified": communication_server_verified
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check/{username}")
async def check_existing_application_endpoint(username: str, api_key: str = Depends(verify_api_key)):
    try:
        application = check_existing_application(username)
        
        if application:
            return {
                "exists": True,
                "application": {
                    "id": application[0],
                    "roblox_user_id": application[1],
                    "roblox_username": application[2],
                    "discord_user_id": application[3],
                    "chat_filter_triggered": bool(application[4]),
                    "communication_server_verified": bool(application[5]),
                    "country_timezone": application[6],
                    "device_choice": application[7],
                    "activity_level": application[8],
                    "discovery_method": application[9],
                    "previous_experience": application[10],
                    "motivation": application[11],
                    "handling_disrespect": application[12],
                    "personality_description": application[13],
                    "special_abilities": application[14],
                    "benefits_to_group": application[15],
                    "perception_of_role": application[16],
                    "created_at": application[17]
                }
            }
        else:
            return {
                "exists": False,
                "application": None
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/")
async def get_applications_endpoint(page: int = 1, per_page: int = 10, user_info: dict = Depends(verify_discord_token)):
    try:
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 50:
            per_page = 10
            
        applications, total_count = get_applications(page, per_page)
        
        total_pages = (total_count + per_page - 1) // per_page
        
        applications_data = []
        for app in applications:
            applications_data.append({
                "id": app[0],
                "roblox_user_id": app[1],
                "roblox_username": app[2],
                "discord_user_id": app[3],
                "chat_filter_triggered": bool(app[4]),
                "communication_server_verified": bool(app[5]),
                "country_timezone": app[6],
                "device_choice": app[7],
                "activity_level": app[8],
                "discovery_method": app[9],
                "previous_experience": app[10],
                "motivation": app[11],
                "handling_disrespect": app[12],
                "personality_description": app[13],
                "special_abilities": app[14],
                "benefits_to_group": app[15],
                "perception_of_role": app[16],
                "created_at": app[17]
            })
        
        return {
            "applications": applications_data,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reject")
async def reject_application(request: ApplicationActionRequest, user_info: dict = Depends(verify_discord_token)):
    try:
        application = get_application_by_id(request.application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        roblox_username = application[2]
        display_name = user_info["display_name"]
        
        delete_application(request.application_id)
        
        notification_message = f"> Application sent by **{roblox_username}** has been rejected by **{display_name}**."
        await send_discord_notification(notification_message)
        
        return {
            "success": True,
            "message": f"Application {request.application_id} rejected and deleted successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pass")
async def pass_application(request: ApplicationActionRequest, user_info: dict = Depends(verify_discord_token)):
    try:
        application = get_application_by_id(request.application_id)
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        roblox_user_id = application[1]
        roblox_username = application[2]
        discord_user_id = application[3]
        display_name = user_info["display_name"]
        
        add_passer(roblox_user_id, roblox_username, discord_user_id, passed_by=display_name)
        delete_application(request.application_id)
        
        notification_message = f"> Application sent by **{roblox_username}** has been accepted by **{display_name}**."
        await send_discord_notification(notification_message)
        
        if discord_user_id:
            user_mention = f"<@{discord_user_id}>"
        else:
            user_mention = roblox_username
        
        return {
            "success": True,
            "message": f"Application {request.application_id} passed and deleted successfully",
            "user_mention": user_mention
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/passers")
async def get_passers_endpoint(user_info: dict = Depends(verify_discord_token)):
    try:
        from database import get_all_passers
        passers = get_all_passers()
        
        passers_data = []
        for passer in passers:
            passers_data.append({
                "roblox_user_id": passer[0],
                "roblox_username": passer[1],
                "discord_user_id": passer[2],
                "passed_at": passer[3],
                "passed_by": passer[4],
                "notes": passer[5]
            })
        
        return {
            "success": True,
            "passers": passers_data,
            "total_count": len(passers_data)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/passers")
async def delete_all_passers_endpoint(user_info: dict = Depends(verify_discord_token)):
    try:
        from database import delete_all_passers
        deleted_count = delete_all_passers()
        
        notification_message = f"> All passers ({deleted_count} records) have been deleted by **{user_info['display_name']}**."
        await send_discord_notification(notification_message)
        
        return {
            "success": True,
            "message": f"Successfully deleted {deleted_count} passers from database",
            "deleted_count": deleted_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
