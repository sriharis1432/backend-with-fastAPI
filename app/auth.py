from fastapi import HTTPException, status
import httpx
import os
import logging
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KeycloakAuth:                                                    # Define a class named KeycloakAuth
    def __init__(self):                                                # Define the __init__ method
        self.keycloak_url = os.getenv("KEYCLOAK_URL", "http://localhost:8080")
        self.realm = os.getenv("KEYCLOAK_REALM", "myrealm")
        self.client_id = os.getenv("KEYCLOAK_CLIENT_ID", "myclient")
        self.client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET", "")
        
        self.token_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"                # Define the token_url attribute
        self.userinfo_url = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/userinfo"          # Define the userinfo_url attribute
        
    async def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:                      # Define the authenticate_user method
        """Authenticate user against Keycloak and return tokens"""
        try:
            data = {                                                                         # Define the data dictionary
                "client_id": self.client_id,
                "grant_type": "password",
                "username": username,
                "password": password,
                "scope": "openid profile email"
            }
            
            if self.client_secret:                                                           # Check if client_secret is set
                data["client_secret"] = self.client_secret
                
            logger.info(f"Authenticating user {username} against {self.token_url}")
            
            async with httpx.AsyncClient() as client:                                         # Create an instance of the httpx.AsyncClient class
                response = await client.post(
                    self.token_url,
                    data=data,
                    timeout=10.0
                )
                
                logger.info(f"Authentication response status: {response.status_code}")
                
                if response.status_code == 200:
                    tokens = response.json()
                    logger.info(f"Successfully authenticated user: {username}")
                    return tokens
                else:
                    error_msg = f"Authentication failed: {response.text}"
                    logger.error(error_msg)
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=error_msg,
                    )
        except httpx.TimeoutException:
            error_msg = "Authentication request timed out"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=error_msg,
            )
        except HTTPException:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during authentication: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )

    async def validate_token(self, token: str) -> Dict[str, Any]:                            # Define the validate_token method
        """Validate access token against Keycloak"""
        if not token:
            logger.error("No token provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No token provided",
            )
            
        try:
            logger.info(f"Validating token against {self.userinfo_url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.userinfo_url,
                    headers={"Authorization": f"Bearer {token}"},                              
                    timeout=10.0,
                )
                
                logger.info(f"Token validation response status: {response.status_code}")
                
                if response.status_code == 200:
                    user_info = response.json()
                    logger.info(f"Token validated successfully for user: {user_info.get('preferred_username')}")
                    return user_info
                elif response.status_code == 401:
                    error_msg = f"Token validation failed: {response.text}"
                    logger.error(error_msg)
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid or expired token",
                    )
                else:
                    error_msg = f"Unexpected response from Keycloak: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Token validation failed",
                    )
        except httpx.TimeoutException:
            error_msg = "Token validation request timed out"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=error_msg,
            )
        except HTTPException:
            raise
        except Exception as e:
            error_msg = f"Token validation error: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Token validation failed",
            )

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:                     # Define the refresh_token method
        """Refresh an expired access token using the refresh token"""
        try:
            data = {
                "client_id": self.client_id,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }
            
            if self.client_secret:
                data["client_secret"] = self.client_secret
                
            logger.info("Attempting to refresh token")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.token_url,
                    data=data,
                    timeout=10.0
                )
                
                logger.info(f"Refresh token response status: {response.status_code}")
                
                if response.status_code == 200:
                    tokens = response.json()
                    logger.info("Successfully refreshed token")
                    return tokens
                else:
                    error_msg = f"Token refresh failed: {response.text}"
                    logger.error(error_msg)
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=error_msg,
                    )
                    
        except httpx.TimeoutException:
            error_msg = "Token refresh request timed out"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=error_msg,
            )
        except HTTPException:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during token refresh: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )
