from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import List, Optional
import uvicorn

from config import load_config
from analyzer import WrapAnalyzer
from clients import TautulliClient
from models import User, WrapData
from pregenerate import WrapStorage

app = FastAPI(title="Plex Wrapped API", version="1.0.0")

# CORS middleware - allow all origins for LAN access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for LAN access
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Load configuration (will be loaded fresh on each request for flexibility)
def get_settings():
    return load_config()


def get_analyzer():
    return WrapAnalyzer(get_settings())


@app.get("/")
async def root():
    return {"message": "Plex Wrapped API", "version": "1.0.0"}


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    try:
        # Test connections
        settings = get_settings()
        tautulli = TautulliClient(settings.tautulli_url, settings.tautulli_api_key)
        tautulli.get_users()
        return {"status": "healthy", "services": {"tautulli": "connected"}}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/api/users", response_model=List[User])
async def get_users():
    """Get all users from Plex/Tautulli"""
    try:
        analyzer = get_analyzer()
        users = analyzer.tautulli.get_users()
        return [
            User(
                id=str(u.get("user_id", "")),
                username=u.get("username", "") or u.get("friendly_name", ""),
                title=u.get("friendly_name"),
                thumb=u.get("thumb"),
            )
            for u in users
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")


def filter_generated_images(wrap_data: dict, image_generation_enabled: bool) -> dict:
    """Remove generated_image fields from cards if image generation is disabled"""
    if image_generation_enabled:
        return wrap_data

    # Create a copy to avoid modifying the original
    filtered_data = wrap_data.copy()

    # Filter out generated_image from cards if present
    if "cards" in filtered_data and isinstance(filtered_data["cards"], list):
        filtered_cards = []
        for card in filtered_data["cards"]:
            if isinstance(card, dict):
                filtered_card = {
                    k: v for k, v in card.items() if k != "generated_image"
                }
                filtered_cards.append(filtered_card)
            else:
                filtered_cards.append(card)
        filtered_data["cards"] = filtered_cards

    return filtered_data


@app.get("/api/wrap/{username}", response_model=WrapData)
async def get_wrap(username: str):
    """Get wrap for a specific user (from pre-generated storage)"""
    try:
        storage = WrapStorage()
        settings = get_settings()

        # Try to load from storage first
        wrap_data = storage.load_wrap(username)

        if wrap_data:
            # Filter out generated images if image generation is disabled
            wrap_data = filter_generated_images(
                wrap_data, settings.use_image_generation
            )
            # Convert dict back to WrapData model
            return WrapData(**wrap_data)

        # If not found in storage, return 404
        raise HTTPException(
            status_code=404,
            detail=f"Wrap not found for user '{username}'. Please run pregenerate.py to generate wraps.",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load wrap: {str(e)}")


@app.get("/api/wrap-by-token/{token}", response_model=WrapData)
async def get_wrap_by_token(token: str):
    """Get wrap by shareable token"""
    try:
        storage = WrapStorage()
        settings = get_settings()

        # Try to load wrap by token
        wrap_data = storage.load_wrap_by_token(token)

        if wrap_data:
            # Filter out generated images if image generation is disabled
            wrap_data = filter_generated_images(
                wrap_data, settings.use_image_generation
            )
            # Convert dict back to WrapData model
            return WrapData(**wrap_data)

        # If not found, return 404
        raise HTTPException(
            status_code=404,
            detail="Wrap not found for this token. The token may be invalid or the wrap may not exist.",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load wrap: {str(e)}")


@app.get("/api/token/{username}")
async def get_token_for_user(username: str):
    """Get shareable token for a username"""
    try:
        storage = WrapStorage()
        token = storage.get_token_for_user(username)

        if token:
            return {"username": username, "token": token}
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Could not generate token for user '{username}'. Wrap may not exist.",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get token: {str(e)}")


@app.get("/api/plex-image/{thumb_path:path}")
async def get_plex_image(thumb_path: str):
    """Proxy Plex images through Tautulli's pms_image_proxy"""
    import httpx

    try:
        settings = get_settings()
        # Remove leading slash if present
        thumb_path = thumb_path.lstrip("/")
        
        # Use Tautulli's pms_image_proxy to fetch images
        tautulli_base = settings.tautulli_url.rstrip("/")
        full_url = f"{tautulli_base}/api/v2?apikey={settings.tautulli_api_key}&cmd=pms_image_proxy&img=/{thumb_path}"

        # Fetch the image through Tautulli
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(full_url)
            response.raise_for_status()

            # Determine content type from response headers or default to image/jpeg
            content_type = response.headers.get("content-type", "image/jpeg")

            # Return the image with appropriate headers
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400",  # Cache for 1 day
                },
            )
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502, detail=f"Failed to fetch image from Tautulli: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to proxy image: {str(e)}")


@app.get("/api/generated-image-info")
async def get_generated_image_info(path: str):
    """Get metadata for generated image (modification time for cache-busting)"""
    from pathlib import Path
    import os

    try:
        # Use the path from query parameter
        image_path = path.replace("%2F", "/").replace("%5C", "\\")

        # Construct full path relative to project root
        project_root = Path.cwd()
        full_path = (project_root / image_path).resolve()

        # Security: Ensure path is within project directory
        if not str(full_path).startswith(str(project_root.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if file exists
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")

        # Get file modification time
        mtime = os.path.getmtime(full_path)

        return {"mtime": int(mtime), "exists": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get image info: {str(e)}"
        )


@app.get("/api/generated-image")
async def get_generated_image(path: str, t: Optional[int] = None):
    """Serve generated card images

    Args:
        path: Path to the image file
        t: Optional timestamp query parameter for cache-busting
    """
    from fastapi.responses import FileResponse
    from pathlib import Path
    import os

    try:
        # Use the path from query parameter
        image_path = path.replace("%2F", "/").replace("%5C", "\\")

        # Construct full path relative to project root
        project_root = Path.cwd()
        full_path = (project_root / image_path).resolve()

        # Security: Ensure path is within project directory
        if not str(full_path).startswith(str(project_root.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if file exists
        if not full_path.exists():
            raise HTTPException(status_code=404, detail="Image not found")

        # Get file modification time for cache-busting
        mtime = os.path.getmtime(full_path)

        # Return file with cache headers that allow revalidation
        # Use must-revalidate so browser checks if file changed
        # Also include Last-Modified header for proper cache validation
        from email.utils import formatdate

        last_modified = formatdate(mtime, usegmt=True)

        return FileResponse(
            full_path,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600, must-revalidate",  # Cache for 1 hour, but revalidate
                "Last-Modified": last_modified,  # Include modification time for cache validation
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve image: {str(e)}")


@app.get("/api/debug/history/{username}")
async def debug_history(username: str):
    """Debug endpoint to see raw history data"""
    try:
        analyzer = get_analyzer()
        tautulli_users = analyzer.tautulli.get_users()
        user_data = next(
            (
                u
                for u in tautulli_users
                if u.get("username") == username or u.get("friendly_name") == username
            ),
            None,
        )

        if not user_data:
            raise HTTPException(status_code=404, detail=f"User {username} not found")

        user_id = user_data.get("user_id")

        # Try without date filters first
        history_no_filter = analyzer.tautulli.get_user_history(
            user_id=user_id, start_date=None, end_date=None
        )

        # Try with date filters
        history_with_filter = analyzer.tautulli.get_user_history(
            user_id=user_id,
            start_date=analyzer.settings.start_date,
            end_date=analyzer.settings.end_date,
        )

        # Try direct API call to see raw response
        import requests

        url = f"{analyzer.tautulli.base_url}/api/v2"
        test_params = {
            "apikey": analyzer.tautulli.api_key,
            "cmd": "get_history",
            "user_id": int(user_id) if user_id else None,
            "length": 10,
        }
        test_response = requests.get(url, params=test_params)
        raw_data = test_response.json() if test_response.status_code == 200 else None

        return {
            "user_id": user_id,
            "user_data": user_data,
            "username": username,
            "date_range": {
                "start": analyzer.settings.start_date,
                "end": analyzer.settings.end_date,
            },
            "history_no_filter": {
                "count": len(history_no_filter),
                "sample": history_no_filter[:3] if history_no_filter else [],
            },
            "history_with_filter": {
                "count": len(history_with_filter),
                "sample": history_with_filter[:3] if history_with_filter else [],
            },
            "raw_api_response": raw_data,
        }
    except Exception as e:
        import traceback

        return {"error": str(e), "traceback": traceback.format_exc()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8766)
