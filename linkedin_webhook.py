from fastapi import FastAPI, HTTPException, Request
from linkedin_api import Linkedin
from pydantic import BaseModel
from typing import Dict, Optional
import os
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables
load_dotenv()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

class LinkedInCredentials(BaseModel):
    email: str
    password: str
    proxy_host: Optional[str] = None
    proxy_port: Optional[int] = None
    proxy_user: Optional[str] = None
    proxy_pass: Optional[str] = None

class LoginResponse(BaseModel):
    status: str
    message: str
    profile_data: Dict = None

@app.post("/webhook/linkedin/check-login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def check_linkedin_login(credentials: LinkedInCredentials, request: Request):
    try:
        # Prepare proxy configuration if provided
        proxies = None
        if credentials.proxy_host and credentials.proxy_port:
            proxy_auth = ""
            if credentials.proxy_user and credentials.proxy_pass:
                proxy_auth = f"{credentials.proxy_user}:{credentials.proxy_pass}@"
            
            proxy_url = f"http://{proxy_auth}{credentials.proxy_host}:{credentials.proxy_port}"
            proxies = {
                "http": proxy_url,
                "https": proxy_url
            }

        # Initialize LinkedIn API client with proxy if provided
        api = Linkedin(
            credentials.email, 
            credentials.password,
            proxies=proxies
        )
        
        # Try to get profile data to verify login
        profile = api.get_profile()
        
        return LoginResponse(
            status="success",
            message="Successfully logged into LinkedIn",
            profile_data=profile
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail={
                "status": "error",
                "message": f"Login failed: {str(e)}",
                "profile_data": None
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080) 