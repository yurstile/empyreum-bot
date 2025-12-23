import asyncio
import os
import uvicorn
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import importlib
from dotenv import load_dotenv
from database import init_database, cleanup_inactive_servers
from bot_instance import bot

load_dotenv()

token = os.getenv('DISCORD_TOKEN')
if not token:
    raise ValueError("DISCORD_TOKEN environment variable is required")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def force_https(request, call_next):
    if request.headers.get("x-forwarded-proto") == "http":
        url = str(request.url)
        url = url.replace("http://", "https://", 1)
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url=url, status_code=307)
    return await call_next(request)

def load_routes():
    routes_dir = "./routes"
    if os.path.exists(routes_dir):
        for filename in os.listdir(routes_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(f"routes.{module_name}")
                    if hasattr(module, 'router'):
                        app.include_router(module.router)
                        print(f"Loaded routes from {module_name}")
                except ImportError as e:
                    print(f"Failed to load routes from {module_name}: {e}")
                    pass

async def load_extensions():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py') and filename != '__init__.py' and not filename.endswith('_utils.py') and not filename.endswith('_views.py'):
            await bot.load_extension(f'cogs.{filename[:-3]}')

async def start_weekly_evaluation():
    await bot.wait_until_ready()
    
    try:
        weekly_eval_cog = bot.get_cog('WeeklyEvaluation')
        if weekly_eval_cog and not weekly_eval_cog.weekly_evaluation.is_running():
            weekly_eval_cog.weekly_evaluation.start()
            
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)
            days_until_friday = (4 - now.weekday()) % 7
            if days_until_friday == 0 and now.hour >= 16:
                days_until_friday = 7
            
            target_time = now.replace(hour=16, minute=0, second=0, microsecond=0)
            if days_until_friday > 0:
                target_time += timedelta(days=days_until_friday)
    except Exception:
        pass

# Cleanup is now handled in the server status updater

async def run_api():
    config = uvicorn.Config(
        app, 
        host="0.0.0.0", 
        port=20115,
        forwarded_allow_ips="*",
        proxy_headers=True
    )
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    init_database()
    load_routes()
    await load_extensions()
    
    bot_task = asyncio.create_task(bot.start(token))
    api_task = asyncio.create_task(run_api())
    weekly_eval_task = asyncio.create_task(start_weekly_evaluation())
    
    await asyncio.gather(api_task, bot_task, weekly_eval_task)

if __name__ == '__main__':
    asyncio.run(main())
