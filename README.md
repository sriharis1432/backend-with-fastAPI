# RAG Pipeline with Keycloak Authentication

This project implements a RAG (Retrieval-Augmented Generation) pipeline with Keycloak authentication. It provides secure API endpoints for text prediction and generation using Hugging Face models.

## Table of Contents
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Keycloak Setup](#keycloak-setup)
- [Environment Variables](#environment-variables)
- [API Endpoints](#api-endpoints)
- [Authentication Flow](#authentication-flow)
- [Manual Testing](#manual-testing)
- [Docker Deployment](#docker-deployment)

## Architecture

The project consists of several components:
1. **FastAPI Backend**: Handles API requests and authentication
2. **Keycloak**: Manages user authentication and authorization
3. **Hugging Face API**: Provides ML models for text generation
4. **RAG Pipeline**: Implements text generation logic

Key files:
- `app/main.py`: FastAPI application and route definitions
- `app/auth.py`: Keycloak authentication implementation
- `app/middleware.py`: Authentication middleware
- `app/rag.py`: RAG pipeline implementation
- `app/models.py`: Pydantic models for request/response validation

## Prerequisites

- Python 3.8+
- Docker and Docker Compose
- Keycloak 21.0+
- Hugging Face API key

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd prjct-7
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start Keycloak:
```bash
docker-compose up -d
```

4. Start the FastAPI application:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Keycloak Setup

### 1. Start Keycloak Server
```bash
docker run -p 8080:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin quay.io/keycloak/keycloak:21.0 start-dev
```

### 2. Create a New Realm
1. Login to Keycloak Admin Console (http://localhost:8080)
2. Click "Create Realm"
3. Set Name: "myrealm"
4. Click "Create"

### 3. Create a Client
```bash
# Using Keycloak Admin CLI
kcadm.sh create clients -r myrealm -s clientId=myclient -s enabled=true -s publicClient=true -s redirectUris='["http://localhost:8000/*"]' -s webOrigins='["http://localhost:8000"]'
```

Or through UI:
1. Go to "Clients" → "Create Client"
2. Set:
   - Client ID: myclient
   - Client Protocol: openid-connect
   - Access Type: public
   - Valid Redirect URIs: http://localhost:8000/*
   - Web Origins: http://localhost:8000

### 4. Create Users
```bash
# Create testuser
kcadm.sh create users -r myrealm -s username=testuser -s enabled=true
kcadm.sh set-password -r myrealm --username testuser --new-password testpass

# Create newuser
kcadm.sh create users -r myrealm -s username=newuser -s enabled=true
kcadm.sh set-password -r myrealm --username newuser --new-password newpass
```

Or through UI:
1. Go to "Users" → "Add User"
2. Set:
   - Username: testuser
   - Email: testuser@example.com
   - First Name: Test
   - Last Name: User
3. Click "Save"
4. Go to "Credentials" tab
5. Set password and disable "Temporary"

## Environment Variables

Create a `.env` file:
```bash
KEYCLOAK_URL=http://localhost:8080
KEYCLOAK_REALM=myrealm
KEYCLOAK_CLIENT_ID=myclient
KEYCLOAK_CLIENT_SECRET=  # Leave empty for public client
HUGGINGFACE_API_KEY=your_api_key_here
FASTAPI_HOST=0.0.0.0
```

## API Endpoints

### Authentication
- POST `/login`: Authenticate user and get tokens
  ```bash
  curl -X POST http://localhost:8000/login \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=testuser&password=testpass"
  ```

### RAG Operations
- POST `/predict`: Make text predictions
  ```bash
  curl -X POST http://localhost:8000/predict \
    -H "Authorization: Bearer <your_token>" \
    -H "Content-Type: application/json" \
    -d '{"input_text": "Hello, how are you?"}'
  ```

- POST `/generate`: Generate streaming text
  ```bash
  curl -X POST http://localhost:8000/generate \
    -H "Authorization: Bearer <your_token>" \
    -H "Content-Type: application/json" \
    -d '{"input_text": "Once upon a time"}'
  ```

## Authentication Flow

1. **Login Flow**:
   - User provides credentials
   - Server authenticates with Keycloak
   - Returns access token and sets refresh token in secure cookie

2. **Request Flow**:
   - Client includes access token in Authorization header
   - Middleware validates token with Keycloak
   - If token expired, attempts refresh using refresh token
   - If refresh successful, returns new tokens

3. **Token Refresh**:
   - Happens automatically in middleware
   - Uses refresh token from secure cookie
   - Updates both access and refresh tokens

## Manual Testing

### 1. Get Access Token
```bash
# Get tokens
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass")

# Extract access token
ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')
```

### 2. Test Protected Endpoint
```bash
# Make prediction
curl -X POST http://localhost:8000/predict \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_text": "Hello, how are you?"}'
```

### 3. Verify Token with Keycloak
```bash
# Check token info
curl -X GET \
  "http://localhost:8080/realms/myrealm/protocol/openid-connect/userinfo" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 4. Test Token Refresh
```bash
# Get new tokens using refresh token
curl -X POST "http://localhost:8080/realms/myrealm/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=myclient" \
  -d "grant_type=refresh_token" \
  -d "refresh_token=$REFRESH_TOKEN"
```

### 5. Test Invalid Token
```bash
# Should return 401 Unauthorized
curl -X POST http://localhost:8000/predict \
  -H "Authorization: Bearer invalid_token" \
  -H "Content-Type: application/json" \
  -d '{"input_text": "Hello"}'
```

## Docker Deployment

### Prerequisites
- Docker
- Docker Compose
- Hugging Face API key

### Quick Start with Docker

1. Clone the repository and navigate to the project directory:
```bash
git clone <repository-url>
cd prjct-7
```

2. Create a `.env` file with your Hugging Face API key:
```bash
HUGGINGFACE_API_KEY=your_api_key_here
```

3. Build and start the services:
```bash
docker-compose up --build
```

This will start:
- Keycloak on http://localhost:8080
- FastAPI application on http://localhost:8000

4. Wait for the health checks to pass (about 30 seconds)

5. Set up Keycloak (first time only):

Access Keycloak admin console:
- URL: http://localhost:8080
- Username: admin
- Password: admin

Then run these commands in a new terminal:
```bash
# Get into the Keycloak container
docker exec -it keycloak bash

# Create realm
/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password admin
/opt/keycloak/bin/kcadm.sh create realms -s realm=myrealm -s enabled=true

# Create client
/opt/keycloak/bin/kcadm.sh create clients -r myrealm -s clientId=myclient -s enabled=true -s publicClient=true -s redirectUris='["http://localhost:8000/*"]' -s webOrigins='["http://localhost:8000"]'

# Create test users
/opt/keycloak/bin/kcadm.sh create users -r myrealm -s username=testuser -s enabled=true
/opt/keycloak/bin/kcadm.sh set-password -r myrealm --username testuser --new-password testpass

/opt/keycloak/bin/kcadm.sh create users -r myrealm -s username=newuser -s enabled=true
/opt/keycloak/bin/kcadm.sh set-password -r myrealm --username newuser --new-password newpass
```

### Testing the Deployment

1. Get an access token:
```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpass"
```

2. Test the predict endpoint:
```bash
# Store the access token
export TOKEN=<access_token_from_previous_step>

# Make a prediction
curl -X POST http://localhost:8000/predict \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_text": "Hello, how are you?"}'
```

3. Test the generate endpoint:
```bash
curl -X POST http://localhost:8000/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input_text": "Once upon a time"}'
```

### Docker Commands Reference

```bash
# Build and start services
docker-compose up --build

# Start services in detached mode
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# View logs for a specific service
docker-compose logs -f app
docker-compose logs -f keycloak

# Restart a service
docker-compose restart app
docker-compose restart keycloak

# Remove containers and volumes
docker-compose down -v
```

### Troubleshooting Docker Deployment

1. **Keycloak not starting:**
```bash
# Check Keycloak logs
docker-compose logs keycloak

# Restart Keycloak
docker-compose restart keycloak
```

2. **FastAPI app not connecting to Keycloak:**
```bash
# Check if services are in the same network
docker network ls
docker network inspect prjct-7_app-network

# Check FastAPI logs
docker-compose logs app
```

3. **Container health checks failing:**
```bash
# Check container health status
docker ps --format "table {{.Names}}\t{{.Status}}"

# View health check logs
docker inspect --format "{{json .State.Health }}" fastapi-app | jq
docker inspect --format "{{json .State.Health }}" keycloak | jq
```

### Production Considerations

1. **Security:**
   - Use HTTPS in production
   - Set secure passwords
   - Configure proper CORS settings
   - Use secrets management

2. **Performance:**
   - Adjust container resource limits
   - Configure proper scaling
   - Set up monitoring

3. **Maintenance:**
   - Regular backups
   - Update dependencies
   - Monitor logs
   - Set up alerting

## Error Handling

Common error codes:
- 401: Unauthorized (invalid/expired token)
- 403: Forbidden (insufficient permissions)
- 500: Internal Server Error
- 503: Service Unavailable (Hugging Face API issues)
- 504: Gateway Timeout

## Security Best Practices

1. **Token Storage**:
   - Access tokens in memory only
   - Refresh tokens in HTTP-only cookies
   - CSRF protection with SameSite=strict

2. **Token Configuration**:
   - Short-lived access tokens (5 minutes)
   - Longer refresh tokens (30 minutes)
   - Automatic token refresh

3. **API Security**:
   - HTTPS in production
   - Rate limiting
   - Input validation
   - Error message sanitization
