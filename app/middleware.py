from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, Dict, Any
import logging
from auth import KeycloakAuth
import jwt

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.auth = KeycloakAuth()
        self.exclude_paths = {"/login", "/docs", "/openapi.json", "/redoc"}

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for excluded paths
        if request.url.path in self.exclude_paths:
            logger.info(f"Skipping authentication for excluded path: {request.url.path}")
            return await call_next(request)

        try:
            # Extract token from header
            auth_header = request.headers.get("Authorization")
            logger.info(f"Processing request to {request.url.path}")
            
            if not auth_header:
                logger.error("No Authorization header found")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Missing authorization header",
                )
                
            if not auth_header.startswith("Bearer "):
                logger.error("Invalid Authorization header format")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authorization header format. Expected 'Bearer <token>'",
                )

            token = auth_header.split(" ")[1]
            logger.debug("Successfully extracted token from header")
            
            # Try to validate the token
            try:
                user_info = await self.auth.validate_token(token)
                logger.info(f"Successfully validated token for user: {user_info.get('preferred_username')}")
            except HTTPException as e:
                # Check if it's a token expiration error
                try:
                    # Try to decode the token without verification to check expiration
                    decoded_token = jwt.decode(token, options={"verify_signature": False})
                    if "exp" in decoded_token:
                        # Get refresh token from request cookies
                        refresh_token = request.cookies.get("refresh_token")
                        if refresh_token:
                            try:
                                # Try to refresh the token
                                logger.info("Attempting to refresh expired token")
                                new_tokens = await self.auth.refresh_token(refresh_token)
                                
                                # Create response with new tokens
                                response = await call_next(request)
                                
                                # Set new access token in Authorization header
                                response.headers["Authorization"] = f"Bearer {new_tokens['access_token']}"
                                
                                # Set new refresh token in cookie
                                response.set_cookie(
                                    key="refresh_token",
                                    value=new_tokens["refresh_token"],
                                    httponly=True,
                                    secure=True,
                                    samesite="strict",
                                )
                                
                                return response
                            except HTTPException as refresh_error:
                                logger.error(f"Token refresh failed: {str(refresh_error)}")
                                raise HTTPException(
                                    status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail="Token expired and refresh failed",
                                )
                        else:
                            logger.error("No refresh token found in cookies")
                            raise HTTPException(
                                status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Token expired and no refresh token available",
                            )
                except jwt.InvalidTokenError:
                    logger.error("Invalid token format")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token format",
                    )
                
                # If it's not a token expiration error, re-raise the original exception
                raise
            
            # Add user info to request state
            request.state.user = user_info
            
            # Process the request
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Error in auth middleware: {str(e)}")
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )
