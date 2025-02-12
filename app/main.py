from fastapi import FastAPI, HTTPException, status, Request, Depends, Security
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer, SecurityScopes
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Dict, Any
from dotenv import load_dotenv
import os
from auth import KeycloakAuth
from rag import RAGPipeline
from models import PredictRequest, GenerateRequest
from middleware import AuthMiddleware
import logging
import json

# Load environment variables
load_dotenv()

app = FastAPI(
    title="RAG API",
    description="API for RAG Pipeline with Keycloak Authentication",
    version="1.0.0",
    openapi_tags=[
        {"name": "auth", "description": "Authentication operations"},
        {"name": "rag", "description": "RAG operations"}
    ]
)

# Add security scheme for OpenAPI
app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define security scheme
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="login",
    scopes={
        "openid": "OpenID scope",
        "profile": "Profile information",
        "email": "Email information"
    }
)

auth = KeycloakAuth()
rag_pipeline = RAGPipeline()

logger = logging.getLogger(__name__)

@app.post("/login", tags=["auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint that authenticates against Keycloak"""
    try:
        auth = KeycloakAuth()
        tokens = await auth.authenticate_user(form_data.username, form_data.password)
        
        # Create response with access token
        response = JSONResponse(content=tokens)
        
        # Set refresh token in secure cookie
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=True,  # Cannot be accessed by JavaScript
            secure=True,    # Only sent over HTTPS
            samesite="strict",  # Protect against CSRF
            max_age=1800,   # 30 minutes (matches Keycloak's refresh token expiry)
        )
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

@app.post("/predict", tags=["rag"])
async def predict(request: PredictRequest, token: str = Security(oauth2_scheme)):
    """Make a prediction using the RAG pipeline"""
    try:
        result = await rag_pipeline.predict(request.input_text)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/generate", tags=["rag"])
async def generate(request: GenerateRequest, token: str = Security(oauth2_scheme)):
    """Generate streaming response using the RAG pipeline"""
    try:
        async def generate_stream():
            async for chunk in rag_pipeline.generate(request.input_text):
                yield json.dumps(chunk) + "\n"
                
        return StreamingResponse(
            generate_stream(),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
