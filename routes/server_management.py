from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import asyncio
from datetime import datetime, timezone
from database import (
    register_roblox_server, ping_roblox_server, add_server_player_count,
    get_all_server_player_counts, cleanup_inactive_servers, get_active_server_count,
    get_server_player_count
)

router = APIRouter(prefix="/server", tags=["server-management"])

# API Key for Roblox server authentication
ROBLOX_SERVER_API_KEY = "ReadYaoiFromResono.Pro"

class ServerRegistrationRequest(BaseModel):
    job_id: str

class PlayerCountRequest(BaseModel):
    job_id: str
    player_type: str  
    ward_name: Optional[str] = None
    count: int

class PingRequest(BaseModel):
    job_id: str

async def verify_server_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key for Roblox server requests"""
    if not x_api_key or x_api_key != ROBLOX_SERVER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

@router.post("/register-server")
async def register_server(
    request: ServerRegistrationRequest,
    api_key: str = Depends(verify_server_api_key)
):
    """
    Register a new Roblox server job ID
    Query parameter: ?id={job_id}
    """
    try:
        job_id = request.job_id
        
        if not job_id or not job_id.strip():
            raise HTTPException(status_code=400, detail="Job ID is required")
        
        # Register the server
        success = register_roblox_server(job_id)
        
        if success:
            return {
                "success": True,
                "message": f"Server {job_id} registered successfully",
                "job_id": job_id,
                "registered_at": datetime.now(timezone.utc).isoformat(),
                "ping_interval": 120  # seconds
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to register server")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registering server: {str(e)}")

@router.post("/add-player-count")
async def add_player_count(
    request: PlayerCountRequest,
    api_key: str = Depends(verify_server_api_key)
):
    """
    Add or update player count for a server
    Query parameters: ?type={patient/staff}&ward={ward_name}
    """
    try:
        job_id = request.job_id
        player_type = request.player_type.lower()
        ward_name = request.ward_name
        count = request.count
        
        # Validate inputs
        if not job_id or not job_id.strip():
            raise HTTPException(status_code=400, detail="Job ID is required")
        
        if player_type not in ["patient", "staff"]:
            raise HTTPException(status_code=400, detail="Player type must be 'patient' or 'staff'")
        
        if count < 0:
            raise HTTPException(status_code=400, detail="Count must be non-negative")
        
        # Add player count
        success = add_server_player_count(job_id, player_type, ward_name, count)
        
        if success:
            return {
                "success": True,
                "message": f"Player count updated for {job_id}",
                "job_id": job_id,
                "player_type": player_type,
                "ward_name": ward_name,
                "count": count,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Server not found or inactive")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating player count: {str(e)}")

@router.post("/ping-server")
async def ping_server(
    request: PingRequest,
    api_key: str = Depends(verify_server_api_key)
):
    """
    Ping server to keep it alive
    Query parameter: ?id={job_id}
    """
    try:
        job_id = request.job_id
        
        if not job_id or not job_id.strip():
            raise HTTPException(status_code=400, detail="Job ID is required")
        
        # Update ping time
        success = ping_roblox_server(job_id)
        
        if success:
            return {
                "success": True,
                "message": f"Server {job_id} pinged successfully",
                "job_id": job_id,
                "pinged_at": datetime.now(timezone.utc).isoformat(),
                "next_ping_due": 120  # seconds
            }
        else:
            raise HTTPException(status_code=404, detail="Server not found")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error pinging server: {str(e)}")

@router.post("/player-left")
async def player_left(
    request: PlayerCountRequest,
    api_key: str = Depends(verify_server_api_key)
):
    """
    Handle when a player leaves - update player count
    """
    try:
        job_id = request.job_id
        player_type = request.player_type.lower()
        ward_name = request.ward_name
        
        # Validate inputs
        if not job_id or not job_id.strip():
            raise HTTPException(status_code=400, detail="Job ID is required")
        
        if player_type not in ["patient", "staff"]:
            raise HTTPException(status_code=400, detail="Player type must be 'patient' or 'staff'")
        
        # Get current count and subtract 1
        current_count = get_server_player_count(job_id, player_type, ward_name)
        new_count = max(0, current_count - 1)  # Don't go below 0
        
        # Update player count in database
        success = add_server_player_count(job_id, player_type, ward_name, new_count)
        
        if success:
            return {
                "success": True,
                "message": f"Player left, count updated to {new_count}",
                "job_id": job_id,
                "player_type": player_type,
                "ward_name": ward_name,
                "new_count": new_count,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to update player count")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating player count: {str(e)}")

@router.get("/get-players")
async def get_players(api_key: str = Depends(verify_server_api_key)):
    """
    Get all player counts from active servers
    """
    try:
        # Get all player counts
        player_data = get_all_server_player_counts()
        active_server_count = get_active_server_count()
        
        # Organize data by server
        servers = {}
        for row in player_data:
            job_id = row[0]
            registered_at = row[1]
            last_ping = row[2]
            player_type = row[3]
            ward_name = row[4]
            count = row[5]
            updated_at = row[6]
            
            if job_id not in servers:
                servers[job_id] = {
                    "job_id": job_id,
                    "registered_at": registered_at,
                    "last_ping": last_ping,
                    "player_counts": {
                        "patient": {},
                        "staff": {}
                    },
                    "total_patients": 0,
                    "total_staff": 0
                }
            
            if player_type and count is not None:
                if ward_name:
                    servers[job_id]["player_counts"][player_type][ward_name] = {
                        "count": count,
                        "updated_at": updated_at
                    }
                else:
                    servers[job_id]["player_counts"][player_type]["general"] = {
                        "count": count,
                        "updated_at": updated_at
                    }
                
                # Update totals
                if player_type == "patient":
                    servers[job_id]["total_patients"] += count
                elif player_type == "staff":
                    servers[job_id]["total_staff"] += count
        
        # Calculate overall totals
        total_patients = sum(server["total_patients"] for server in servers.values())
        total_staff = sum(server["total_staff"] for server in servers.values())
        
        return {
            "success": True,
            "active_servers": active_server_count,
            "total_patients": total_patients,
            "total_staff": total_staff,
            "total_players": total_patients + total_staff,
            "servers": list(servers.values()),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving player data: {str(e)}")

@router.post("/cleanup-inactive")
async def cleanup_inactive_servers_endpoint(
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_server_api_key)
):
    """
    Manually trigger cleanup of inactive servers
    """
    try:
        # Run cleanup in background
        background_tasks.add_task(cleanup_inactive_servers)
        
        return {
            "success": True,
            "message": "Cleanup task started",
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting cleanup: {str(e)}")

@router.get("/status")
async def server_status(api_key: str = Depends(verify_server_api_key)):
    """
    Get overall server management status
    """
    try:
        active_server_count = get_active_server_count()
        
        return {
            "success": True,
            "active_servers": active_server_count,
            "status": "operational",
            "ping_timeout": 120,  # seconds
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")
