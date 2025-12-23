import sqlite3
import json
from datetime import datetime, timezone

ROBLOX_GROUP_ID = 14029943

GUILD_ID = 941998687779954708

WELCOME_CHANNEL_ID = 942004270679597106
STAFF_REQUEST_CHANNEL_ID = 1166412415597023252

RANK_CATEGORIES = {
    "patient": ["admittee", "patient", "lunatic patient", "honored patient"],
    "staff": ["undocumented", "noviciate", "attendant", "warden", "custodian"],
    "staff_silver": ["concierge", "lecturer"]
}

SPECIAL_ROLES = {
    "true_staff": "942445410381873222",
    "clinic_maids": "943124878834425866",
    "true_patient": "942451886739578931",
    "untrue_patient": "963524808446967978"
}

RANK_HIERARCHY = [
    "admittee",
    "patient",
    "lunatic patient",
    "honored patient",
    "undocumented",
    "noviciate",
    "attendant",
    "warden",
    "custodian",
    "concierge",
    "lecturer"
]

STAFF_ROLES = [
    "undocumented",
    "noviciate",
    "attendant",
    "warden",
    "custodian",
    "concierge",
    "lecturer"
]

PATIENT_ROLES = [
    "patient",
    "lunatic patient",
    "honored patient"
]

ROLE_CATEGORY_MAP = {
    "undocumented": "staff",
    "noviciate": "staff",
    "attendant": "staff",
    "warden": "staff",
    "custodian": "staff",
    "concierge": "staff_silver",
    "lecturer": "staff_silver"
}

def init_database():
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            discord_role_id TEXT NOT NULL,
            roblox_role_id TEXT,
            category TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_verification (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT NOT NULL,
            username TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verified_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT NOT NULL,
            username TEXT NOT NULL,
            roblox_user_id TEXT,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roblox_user_id TEXT NOT NULL,
            roblox_username TEXT NOT NULL,
            discord_user_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roblox_user_id TEXT NOT NULL UNIQUE,
            roblox_username TEXT NOT NULL,
            discord_user_id TEXT,
            excellences INTEGER DEFAULT 0,
            evaluation BOOLEAN DEFAULT FALSE,
            roblox_role_id TEXT,
            category TEXT,
            warnings INTEGER DEFAULT 0,
            excellence_score INTEGER DEFAULT 0,
            bad_streak INTEGER DEFAULT 0,
            minimum_streak INTEGER DEFAULT 0,
            evaluation_week_score INTEGER DEFAULT 0,
            last_inactivity_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff_inactivity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roblox_user_id TEXT NOT NULL,
            roblox_username TEXT NOT NULL,
            discord_user_id TEXT,
            excellences INTEGER DEFAULT 0,
            evaluation BOOLEAN DEFAULT FALSE,
            roblox_role_id TEXT,
            category TEXT,
            warnings INTEGER DEFAULT 0,
            excellence_score INTEGER DEFAULT 0,
            bad_streak INTEGER DEFAULT 0,
            minimum_streak INTEGER DEFAULT 0,
            evaluation_week_score INTEGER DEFAULT 0,
            activity_start TIMESTAMP NOT NULL,
            activity_end TIMESTAMP NOT NULL,
            reason TEXT,
            last_inactivity_date TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    try:
        cursor.execute('ALTER TABLE staff ADD COLUMN category TEXT')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE staff ADD COLUMN warnings INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE staff ADD COLUMN excellence_score INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE staff ADD COLUMN bad_streak INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE staff ADD COLUMN minimum_streak INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE staff ADD COLUMN evaluation_week_score INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE staff ADD COLUMN last_inactivity_date TIMESTAMP')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE applications ADD COLUMN discord_user_id TEXT')
    except sqlite3.OperationalError:
        pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roblox_user_id TEXT NOT NULL,
            roblox_username TEXT NOT NULL,
            discord_user_id TEXT,
            chat_filter_triggered BOOLEAN NOT NULL,
            communication_server_verified BOOLEAN NOT NULL,
            country_timezone TEXT NOT NULL,
            device_choice TEXT NOT NULL,
            activity_level INTEGER NOT NULL,
            discovery_method TEXT NOT NULL,
            previous_experience TEXT,
            motivation TEXT NOT NULL,
            handling_disrespect TEXT NOT NULL,
            personality_description TEXT NOT NULL,
            special_abilities TEXT,
            benefits_to_group TEXT NOT NULL,
            perception_of_role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS passers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roblox_user_id TEXT NOT NULL UNIQUE,
            roblox_username TEXT NOT NULL,
            discord_user_id TEXT,
            passed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            passed_by TEXT,
            notes TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roblox_servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL UNIQUE,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_ping TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_player_counts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            player_type TEXT NOT NULL,
            ward_name TEXT,
            count INTEGER NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (job_id) REFERENCES roblox_servers (job_id)
        )
    ''')

    # Shifts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_user_id TEXT NOT NULL,
            message_id TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP
        )
    ''')

    role_data = [
        ("admittee", "942019598142828574", "79838856", "patient"),
        ("patient", "942019597371056159", "79838855", "patient"),
        ("lunatic patient", "948008718111490099", "80752931", "patient"),
        ("honored patient", "942019596469280768", "79839843", "patient"),
        ("undocumented", "942019594363756544", "79840122", "staff"),
        ("noviciate", "953743887149695007", "81474749", "staff"),
        ("attendant", "942019593000611851", "79840232", "staff"),
        ("warden", "942019592442765352", "79840296", "staff"),
        ("custodian", "942019591608102952", "79840262", "staff"),
        ("concierge", "942019590576275467", "80133627", "staff_silver"),
        ("lecturer", "943947575965405234", "80133700", "staff_silver"),
        ("curator", "942019588500127795", "None", "hr"),
        ("magistrate", "942019587615113266", None, "hr"),
        ("monarch", "942019586809802773", None, "hr"),
        ("hierarch", "943947574996508672", None, "hr"),
        ("untrue patient", "963524808446967978", None, "untrue"),
        ("true patient", "942451886739578931", None, "true"),
        ("true staff", "942445410381873222", None, "true"),
        ("clinic maids", "943124878834425866", None, "clinic_maids"),
        ("1 excellence", "1401232544611176528", None, "excellence_points"),
        ("2 excellence", "1401235996380627057", None, "excellence_points"),
        ("3 excellence", "1401236077796266146", None, "excellence_points"),
        ("4 excellence", "1401236156779073678", None, "excellence_points"),
        ("5 excellence", "1401236230477185034", None, "excellence_points")
    ]

    cursor.executemany('''
        INSERT OR REPLACE INTO roles (name, discord_role_id, roblox_role_id, category)
        VALUES (?, ?, ?, ?)
    ''', role_data)

    conn.commit()
    conn.close()

def search_role(name):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT name, discord_role_id, roblox_role_id, category
        FROM roles
        WHERE name LIKE ?
    ''', (f'%{name}%',))

    results = cursor.fetchall()
    conn.close()

    return results

def get_role_by_discord_id(discord_role_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT name, discord_role_id, roblox_role_id, category
        FROM roles
        WHERE discord_role_id = ?
    ''', (discord_role_id,))

    result = cursor.fetchone()
    conn.close()

    return result

def get_roles_by_category(category):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT name, discord_role_id, roblox_role_id, category
        FROM roles
        WHERE category = ?
    ''', (category,))

    results = cursor.fetchall()
    conn.close()

    return results

def add_pending_verification(discord_id, username):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM pending_verification
        WHERE discord_id = ?
    ''', (discord_id,))

    cursor.execute('''
        INSERT INTO pending_verification (discord_id, username)
        VALUES (?, ?)
    ''', (discord_id, username))

    conn.commit()
    conn.close()

def get_pending_verifications():
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT discord_id, username, created_at
        FROM pending_verification
        WHERE created_at > datetime('now', '-5 minutes')
        ORDER BY created_at DESC
    ''')

    results = cursor.fetchall()
    conn.close()

    return results

def get_pending_by_username(username):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT discord_id, username, created_at
        FROM pending_verification
        WHERE username = ? AND created_at > datetime('now', '-5 minutes')
    ''', (username,))

    result = cursor.fetchone()
    conn.close()

    return result

def remove_pending_verification(discord_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM pending_verification
        WHERE discord_id = ?
    ''', (discord_id,))

    conn.commit()
    conn.close()

def add_verified_user(discord_id, username, roblox_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO verified_users (discord_id, username, roblox_user_id)
        VALUES (?, ?, ?)
    ''', (discord_id, username, roblox_user_id))

    conn.commit()
    conn.close()

def get_role_by_name(name):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT name, discord_role_id, roblox_role_id, category
        FROM roles
        WHERE name = ?
    ''', (name,))

    result = cursor.fetchone()
    conn.close()

    return result

def is_user_pending(discord_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT discord_id, username, created_at
        FROM pending_verification
        WHERE discord_id = ? AND created_at > datetime('now', '-5 minutes')
    ''', (discord_id,))

    result = cursor.fetchone()
    conn.close()

    return result is not None

def get_verified_user_by_roblox_id(roblox_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT discord_id, username, roblox_user_id, verified_at
        FROM verified_users
        WHERE roblox_user_id = ?
    ''', (roblox_user_id,))

    result = cursor.fetchone()
    conn.close()

    return result

def add_pending_staff(roblox_user_id, roblox_username, discord_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM pending_staff
        WHERE roblox_user_id = ?
    ''', (roblox_user_id,))

    cursor.execute('''
        INSERT INTO pending_staff (roblox_user_id, roblox_username, discord_user_id)
        VALUES (?, ?, ?)
    ''', (roblox_user_id, roblox_username, discord_user_id))

    conn.commit()
    conn.close()

def get_pending_staff(roblox_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, roblox_user_id, roblox_username, discord_user_id, created_at
        FROM pending_staff
        WHERE roblox_user_id = ?
    ''', (roblox_user_id,))

    result = cursor.fetchone()
    conn.close()

    return result

def remove_pending_staff(roblox_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM pending_staff
        WHERE roblox_user_id = ?
    ''', (roblox_user_id,))

    conn.commit()
    conn.close()

def add_staff_member(roblox_user_id, roblox_username, discord_user_id, roblox_role_id, category=None):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO staff (roblox_user_id, roblox_username, discord_user_id, roblox_role_id, category)
        VALUES (?, ?, ?, ?, ?)
    ''', (roblox_user_id, roblox_username, discord_user_id, roblox_role_id, category))

    conn.commit()
    conn.close()

def restore_staff_member_from_inactivity(roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT activity_end FROM staff_inactivity
        WHERE roblox_user_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    ''', (roblox_user_id,))

    result = cursor.fetchone()
    last_inactivity_date = None
    if result and result[0]:
        activity_end = result[0]
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

def get_staff_member(roblox_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at
        FROM staff
        WHERE roblox_user_id = ?
    ''', (roblox_user_id,))

    result = cursor.fetchone()
    conn.close()

    return result

def get_staff_by_category(category):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at
        FROM staff
        WHERE category = ?
        ORDER BY created_at DESC
    ''', (category,))

    results = cursor.fetchall()
    conn.close()

    return results

def get_all_staff():
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at
        FROM staff
        ORDER BY created_at DESC
    ''')

    results = cursor.fetchall()
    conn.close()

    return results

def get_all_verified_users():
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT discord_id, username, roblox_user_id, verified_at
        FROM verified_users
        ORDER BY verified_at DESC
    ''')

    results = cursor.fetchall()
    conn.close()

    return results

def remove_staff_member(roblox_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM staff
        WHERE roblox_user_id = ?
    ''', (roblox_user_id,))

    conn.commit()
    conn.close()

def remove_verified_user(roblox_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM verified_users
        WHERE roblox_user_id = ?
    ''', (roblox_user_id,))

    conn.commit()
    conn.close()

def get_staff_by_discord_id(discord_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, created_at
        FROM staff
        WHERE discord_user_id = ?
    ''', (discord_user_id,))

    result = cursor.fetchone()
    conn.close()

    return result

def get_verified_user_by_discord_id(discord_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT discord_id, username, roblox_user_id, verified_at
        FROM verified_users
        WHERE discord_id = ?
    ''', (discord_id,))

    result = cursor.fetchone()
    conn.close()

    return result

def update_staff_role(roblox_user_id, new_roblox_role_id, new_category):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE staff
        SET roblox_role_id = ?, category = ?
        WHERE roblox_user_id = ?
    ''', (new_roblox_role_id, new_category, roblox_user_id))

    conn.commit()
    conn.close()

def update_excellence_score(roblox_user_id, excellence_score):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE staff
        SET excellence_score = ?
        WHERE roblox_user_id = ?
    ''', (excellence_score, roblox_user_id))

    conn.commit()
    conn.close()

def update_bad_streak(roblox_user_id, bad_streak):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE staff
        SET bad_streak = ?
        WHERE roblox_user_id = ?
    ''', (bad_streak, roblox_user_id))

    conn.commit()
    conn.close()

def increment_excellence_score(roblox_user_id, increment=1):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE staff
        SET excellence_score = excellence_score + ?
        WHERE roblox_user_id = ?
    ''', (increment, roblox_user_id))

    conn.commit()
    conn.close()

def increment_bad_streak(roblox_user_id, increment=1):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE staff
        SET bad_streak = bad_streak + ?
        WHERE roblox_user_id = ?
    ''', (increment, roblox_user_id))

    conn.commit()
    conn.close()

def reset_bad_streak(roblox_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE staff
        SET bad_streak = 0
        WHERE roblox_user_id = ?
    ''', (roblox_user_id,))

    conn.commit()
    conn.close()

def update_minimum_streak(roblox_user_id, minimum_streak):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE staff
        SET minimum_streak = ?
        WHERE roblox_user_id = ?
    ''', (minimum_streak, roblox_user_id))

    conn.commit()
    conn.close()

def update_evaluation_week_score(roblox_user_id, evaluation_week_score):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE staff
        SET evaluation_week_score = ?
        WHERE roblox_user_id = ?
    ''', (evaluation_week_score, roblox_user_id))

    conn.commit()
    conn.close()

def increment_minimum_streak(roblox_user_id, increment=1):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE staff
        SET minimum_streak = minimum_streak + ?
        WHERE roblox_user_id = ?
    ''', (increment, roblox_user_id))

    conn.commit()
    conn.close()

def increment_evaluation_week_score(roblox_user_id, increment=1):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE staff
        SET evaluation_week_score = evaluation_week_score + ?
        WHERE roblox_user_id = ?
    ''', (increment, roblox_user_id))

    conn.commit()
    conn.close()

def reset_evaluation_week_score(roblox_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE staff
        SET evaluation_week_score = 0
        WHERE roblox_user_id = ?
    ''', (roblox_user_id,))

    conn.commit()
    conn.close()

def reset_all_evaluation_week_scores():
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('UPDATE staff SET evaluation_week_score = 0')

    conn.commit()
    conn.close()

def add_staff_to_inactivity(roblox_user_id, roblox_username, discord_user_id, excellences, evaluation, roblox_role_id, category, warnings, excellence_score, bad_streak, minimum_streak, evaluation_week_score, activity_start, activity_end, reason=None):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    if hasattr(activity_end, 'timestamp'):
        activity_end_timestamp = int(activity_end.timestamp())
    elif isinstance(activity_end, str):
        try:
            dt = datetime.fromisoformat(activity_end.replace('Z', '+00:00'))
            activity_end_timestamp = int(dt.timestamp())
        except:
            activity_end_timestamp = int(datetime.now(timezone.utc).timestamp())
    else:
        activity_end_timestamp = int(datetime.now(timezone.utc).timestamp())

    cursor.execute('''
        INSERT INTO staff_inactivity (
            roblox_user_id, roblox_username, discord_user_id, excellences, evaluation,
            roblox_role_id, category, warnings, excellence_score, bad_streak,
            minimum_streak, evaluation_week_score, activity_start, activity_end, reason, last_inactivity_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (roblox_user_id, roblox_username, discord_user_id, excellences, evaluation,
          roblox_role_id, category, warnings, excellence_score, bad_streak,
          minimum_streak, evaluation_week_score, activity_start, activity_end, reason, activity_end_timestamp))

    conn.commit()
    conn.close()

def get_staff_inactivity_by_roblox_id(roblox_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation,
               roblox_role_id, category, warnings, excellence_score, bad_streak,
               minimum_streak, evaluation_week_score, activity_start, activity_end, reason, created_at
        FROM staff_inactivity
        WHERE roblox_user_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    ''', (roblox_user_id,))

    result = cursor.fetchone()
    conn.close()

    return result

def get_staff_inactivity_by_discord_id(discord_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation,
               roblox_role_id, category, warnings, excellence_score, bad_streak,
               minimum_streak, evaluation_week_score, activity_start, activity_end, reason, created_at
        FROM staff_inactivity
        WHERE discord_user_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    ''', (discord_user_id,))

    result = cursor.fetchone()
    conn.close()

    return result

def get_all_inactive_staff():
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT roblox_user_id, roblox_username, discord_user_id, excellences, evaluation,
               roblox_role_id, category, warnings, excellence_score, bad_streak,
               minimum_streak, evaluation_week_score, activity_start, activity_end, reason, created_at
        FROM staff_inactivity
        ORDER BY activity_start ASC
    ''')

    results = cursor.fetchall()
    conn.close()

    return results

def remove_staff_from_inactivity(roblox_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        DELETE FROM staff_inactivity
        WHERE roblox_user_id = ?
    ''', (roblox_user_id,))

    conn.commit()
    conn.close()

def can_submit_inactivity_request(discord_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()

    cursor.execute('''
        SELECT last_inactivity_date FROM staff
        WHERE discord_user_id = ?
    ''', (discord_user_id,))

    result = cursor.fetchone()
    conn.close()

    if not result or not result[0]:
        return True

    last_inactivity_timestamp = result[0]
    if isinstance(last_inactivity_timestamp, str):
        try:
            last_inactivity_timestamp = int(last_inactivity_timestamp)
        except:
            return True
    
    last_inactivity_date = datetime.fromtimestamp(last_inactivity_timestamp, tz=timezone.utc)
    current_time = datetime.now(timezone.utc)
    
    days_since_last = (current_time - last_inactivity_date).days
    return days_since_last >= 14

def add_application(roblox_user_id, roblox_username, discord_user_id, chat_filter_triggered, communication_server_verified,
                   country_timezone, device_choice, activity_level, discovery_method, previous_experience,
                   motivation, handling_disrespect, personality_description, special_abilities,
                   benefits_to_group, perception_of_role):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO applications (
                roblox_user_id, roblox_username, discord_user_id, chat_filter_triggered, communication_server_verified,
                country_timezone, device_choice, activity_level, discovery_method, previous_experience,
                motivation, handling_disrespect, personality_description, special_abilities,
                benefits_to_group, perception_of_role
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (roblox_user_id, roblox_username, discord_user_id, chat_filter_triggered, communication_server_verified,
              country_timezone, device_choice, activity_level, discovery_method, previous_experience,
              motivation, handling_disrespect, personality_description, special_abilities,
              benefits_to_group, perception_of_role))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_applications(page=1, per_page=10):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        offset = (page - 1) * per_page
        
        cursor.execute('''
            SELECT id, roblox_user_id, roblox_username, discord_user_id, chat_filter_triggered, communication_server_verified,
                   country_timezone, device_choice, activity_level, discovery_method, previous_experience,
                   motivation, handling_disrespect, personality_description, special_abilities,
                   benefits_to_group, perception_of_role, created_at
            FROM applications
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (per_page, offset))
        
        applications = cursor.fetchall()
        
        cursor.execute('SELECT COUNT(*) FROM applications')
        total_count = cursor.fetchone()[0]
        
        return applications, total_count
    except Exception as e:
        raise e
    finally:
        conn.close()

def find_discord_id_by_roblox_username(roblox_username, bot=None):
    """
    Find Discord ID by searching verified users table and Discord server
    Returns Discord ID if found, None otherwise
    """
    # First, check verified users table
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT discord_id FROM verified_users
        WHERE username = ?
    ''', (roblox_username,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0]
    
    if bot and bot.is_ready():
        try:
            from database import GUILD_ID
            guild = bot.get_guild(GUILD_ID)
            if guild:
                for member in guild.members:
                    if (member.display_name.lower() == roblox_username.lower() or
                        member.name.lower() == roblox_username.lower() or
                        (member.nick and member.nick.lower() == roblox_username.lower())):
                        return str(member.id)
        except Exception as e:
            print(f"Error searching Discord server for {roblox_username}: {e}")
    
    return None

def check_existing_application(roblox_username):
    """
    Check if a user already has an application by their Roblox username
    Returns application data if found, None otherwise
    """
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, roblox_user_id, roblox_username, discord_user_id, chat_filter_triggered, communication_server_verified,
                   country_timezone, device_choice, activity_level, discovery_method, previous_experience,
                   motivation, handling_disrespect, personality_description, special_abilities,
                   benefits_to_group, perception_of_role, created_at
            FROM applications
            WHERE roblox_username = ?
            ORDER BY created_at DESC
            LIMIT 1
        ''', (roblox_username,))
        
        result = cursor.fetchone()
        return result
    except Exception as e:
        raise e
    finally:
        conn.close()

def get_application_by_id(application_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, roblox_user_id, roblox_username, discord_user_id, chat_filter_triggered, communication_server_verified,
                   country_timezone, device_choice, activity_level, discovery_method, previous_experience,
                   motivation, handling_disrespect, personality_description, special_abilities,
                   benefits_to_group, perception_of_role, created_at
            FROM applications
            WHERE id = ?
        ''', (application_id,))
        
        application = cursor.fetchone()
        return application
    except Exception as e:
        raise e
    finally:
        conn.close()

def delete_application(application_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM applications WHERE id = ?', (application_id,))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def add_passer(roblox_user_id, roblox_username, discord_user_id=None, passed_by=None, notes=None):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO passers (
                roblox_user_id, roblox_username, discord_user_id, passed_by, notes
            ) VALUES (?, ?, ?, ?, ?)
        ''', (roblox_user_id, roblox_username, discord_user_id, passed_by, notes))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_passer(roblox_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT roblox_user_id, roblox_username, discord_user_id, passed_at, passed_by, notes
            FROM passers
            WHERE roblox_user_id = ?
        ''', (roblox_user_id,))
        
        passer = cursor.fetchone()
        return passer
    except Exception as e:
        raise e
    finally:
        conn.close()

def get_all_passers():
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT roblox_user_id, roblox_username, discord_user_id, passed_at, passed_by, notes
            FROM passers
            ORDER BY passed_at DESC
        ''')
        
        passers = cursor.fetchall()
        return passers
    except Exception as e:
        raise e
    finally:
        conn.close()

def remove_passer(roblox_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM passers WHERE roblox_user_id = ?', (roblox_user_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def delete_all_passers():
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM passers')
        deleted_count = cursor.rowcount
        conn.commit()
        return deleted_count
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def update_staff_username(roblox_user_id, new_username):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE staff 
            SET roblox_username = ? 
            WHERE roblox_user_id = ?
        ''', (new_username, roblox_user_id))
        
        cursor.execute('''
            UPDATE staff_inactivity 
            SET roblox_username = ? 
            WHERE roblox_user_id = ?
        ''', (new_username, roblox_user_id))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def register_roblox_server(job_id):
    """Register a new Roblox server job ID"""
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO roblox_servers (job_id, registered_at, last_ping, is_active)
            VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, TRUE)
        ''', (job_id,))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def ping_roblox_server(job_id):
    """Update the last ping time for a Roblox server"""
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE roblox_servers 
            SET last_ping = CURRENT_TIMESTAMP, is_active = TRUE
            WHERE job_id = ?
        ''', (job_id,))
        
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def add_server_player_count(job_id, player_type, ward_name, count):
    """Add or update player count for a server"""
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        # First, ensure the server exists and is active
        cursor.execute('SELECT job_id FROM roblox_servers WHERE job_id = ? AND is_active = TRUE', (job_id,))
        if not cursor.fetchone():
            conn.close()
            return False
        
        # Insert or update player count
        cursor.execute('''
            INSERT OR REPLACE INTO server_player_counts (job_id, player_type, ward_name, count, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (job_id, player_type, ward_name, count))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_all_server_player_counts():
    """Get all player counts from active servers"""
    conn = sqlite3.connect('roles.db', timeout=10.0)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT s.job_id, s.registered_at, s.last_ping,
                   pc.player_type, pc.ward_name, pc.count, pc.updated_at
            FROM roblox_servers s
            LEFT JOIN server_player_counts pc ON s.job_id = pc.job_id
            WHERE s.is_active = TRUE
            ORDER BY s.job_id, pc.player_type, pc.ward_name
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        conn.close()
        raise e

def cleanup_inactive_servers():
    """Remove servers that haven't pinged in the last 120 seconds"""
    conn = sqlite3.connect('roles.db', timeout=5.0)  # 5 second timeout
    cursor = conn.cursor()
    
    try:
        # Get count of servers that will be marked inactive
        cursor.execute('''
            SELECT COUNT(*) FROM roblox_servers 
            WHERE last_ping < datetime('now', '-120 seconds')
        ''')
        inactive_count = cursor.fetchone()[0]
        
        if inactive_count > 0:
            # Delete player counts for inactive servers first
            cursor.execute('''
                DELETE FROM server_player_counts 
                WHERE job_id IN (
                    SELECT job_id FROM roblox_servers 
                    WHERE last_ping < datetime('now', '-120 seconds')
                )
            ''')
            
            # Delete inactive servers
            cursor.execute('''
                DELETE FROM roblox_servers 
                WHERE last_ping < datetime('now', '-120 seconds')
            ''')
            
            print(f"Cleaned up {inactive_count} inactive servers")
        
        conn.commit()
        return inactive_count
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_active_server_count():
    """Get count of active servers"""
    conn = sqlite3.connect('roles.db', timeout=10.0)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT COUNT(*) FROM roblox_servers WHERE is_active = TRUE')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except Exception as e:
        conn.close()
        raise e

def get_server_player_count(job_id, player_type, ward_name):
    """Get current player count for a specific server, type, and ward"""
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT count FROM server_player_counts 
            WHERE job_id = ? AND player_type = ? AND ward_name = ?
        ''', (job_id, player_type, ward_name))
        
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else 0
    except Exception as e:
        conn.close()
        raise e

# === Shift management helpers ===
def create_shift(discord_user_id, message_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO shifts (discord_user_id, message_id, status)
            VALUES (?, ?, 'ongoing')
        ''', (str(discord_user_id), str(message_id)))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_active_shift_by_user(discord_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, discord_user_id, message_id, status, created_at
            FROM shifts
            WHERE discord_user_id = ? AND status = 'ongoing'
            ORDER BY created_at DESC
            LIMIT 1
        ''', (str(discord_user_id),))
        result = cursor.fetchone()
        return result
    finally:
        conn.close()

def end_shift_by_user(discord_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, message_id FROM shifts
            WHERE discord_user_id = ? AND status = 'ongoing'
            ORDER BY created_at DESC
            LIMIT 1
        ''', (str(discord_user_id),))
        row = cursor.fetchone()
        if not row:
            return None
        shift_id, message_id = row
        cursor.execute('''
            UPDATE shifts
            SET status = 'ended', ended_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (shift_id,))
        conn.commit()
        return str(message_id)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_all_active_shifts():
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, discord_user_id, message_id, created_at
            FROM shifts
            WHERE status = 'ongoing'
            ORDER BY created_at ASC
        ''')
        return cursor.fetchall()
    finally:
        conn.close()

def end_all_shifts():
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT id, message_id FROM shifts
            WHERE status = 'ongoing'
        ''')
        rows = cursor.fetchall()
        cursor.execute('''
            UPDATE shifts
            SET status = 'ended', ended_at = CURRENT_TIMESTAMP
            WHERE status = 'ongoing'
        ''')
        conn.commit()
        return [str(r[1]) for r in rows]
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_last_ended_shift(discord_user_id):
    conn = sqlite3.connect('roles.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            SELECT ended_at FROM shifts
            WHERE discord_user_id = ? AND status = 'ended' AND ended_at IS NOT NULL
            ORDER BY ended_at DESC
            LIMIT 1
        ''', (str(discord_user_id),))
        row = cursor.fetchone()
        return row[0] if row else None
    finally:
        conn.close()
