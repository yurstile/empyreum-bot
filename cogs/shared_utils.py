import discord
import requests
import os
import sqlite3
from database import get_role_by_name, SPECIAL_ROLES, ROBLOX_GROUP_ID

ROBLOX_LOGIN_COOKIE = os.getenv('ROBLOX_LOGIN_COOKIE')

class SharedUtils:
    def __init__(self, bot):
        self.bot = bot

    def get_rank_name_by_roblox_role_id(self, roblox_role_id):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM roles WHERE roblox_role_id = ?', (roblox_role_id,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting rank name for Roblox role {roblox_role_id}: {e}")
            return None

    def get_rank_name_by_discord_role_id(self, discord_role_id):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM roles WHERE discord_role_id = ?', (discord_role_id,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting rank name for Discord role {discord_role_id}: {e}")
            return None

    def get_discord_role_id_by_roblox_role_id(self, roblox_role_id):
        try:
            conn = sqlite3.connect('roles.db')
            cursor = conn.cursor()
            cursor.execute('SELECT discord_role_id FROM roles WHERE roblox_role_id = ?', (roblox_role_id,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            print(f"Error getting Discord role ID for Roblox role {roblox_role_id}: {e}")
            return None

    async def rank_roblox_user(self, roblox_user_id, new_roblox_role_id):
        try:
            if not ROBLOX_LOGIN_COOKIE:
                return False
            
            session = requests.Session()
            session.cookies.set('.ROBLOSECURITY', ROBLOX_LOGIN_COOKIE, domain='.roblox.com')
            
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
            
            url = f"https://groups.roblox.com/v1/groups/{ROBLOX_GROUP_ID}/users/{roblox_user_id}"
            data = {"roleId": int(new_roblox_role_id)}
            response = session.patch(url, headers=headers, json=data)
            
            return response.status_code == 200
        except Exception as e:
            print(f"Error ranking Roblox user: {e}")
            return False

    async def get_roblox_user_info(self, username):
        try:
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
            
            if response.status_code == 200:
                data = response.json()
                if data.get('data') and len(data['data']) > 0:
                    user_data = data['data'][0]
                    if user_data.get('id'):
                        return {
                            'user_id': str(user_data['id']),
                            'username': user_data.get('name', username)
                        }
            
            return None
        except Exception as e:
            print(f"Error getting Roblox user info: {e}")
            return None

    async def get_roblox_user_info_by_id(self, user_id):
        try:
            response = requests.get(f"https://users.roblox.com/v1/users/{user_id}")
            if response.status_code == 200:
                data = response.json()
                return {
                    'user_id': str(user_id),
                    'username': data.get('name', 'Unknown')
                }
            return None
        except Exception as e:
            print(f"Error getting Roblox user info by ID: {e}")
            return None
