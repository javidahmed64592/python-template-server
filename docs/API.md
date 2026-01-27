<!-- omit from toc -->
# API

This document summarizes the backend API provided by the Python Template Server.
All endpoints are mounted under the `/api` prefix.

**Note**: The `TemplateServer` base class provides common behaviors (authentication, rate limiting, security headers, instrumentation) that are automatically applied to all endpoints. Application-specific servers (like `ExampleServer`) extend `TemplateServer` to add custom endpoints and business logic.

<!-- omit from toc -->
## Table of Contents
- [Authentication](#authentication)
- [Logging Configuration](#logging-configuration)
- [Request Logging](#request-logging)
- [Security Headers](#security-headers)
- [CORS (Cross-Origin Resource Sharing)](#cors-cross-origin-resource-sharing)
- [Rate Limiting](#rate-limiting)
- [Endpoints](#endpoints)
  - [GET /api/health](#get-apihealth)
  - [GET /api/login](#get-apilogin)
- [Static File Serving](#static-file-serving)
- [Request and Response Models (Pydantic)](#request-and-response-models-pydantic)
- [API Documentation](#api-documentation)
  - [Swagger UI (/api/docs)](#swagger-ui-apidocs)
  - [ReDoc (/api/redoc)](#redoc-apiredoc)

## Authentication

All API endpoints require authentication via an API key passed in the `X-API-Key` header.

**Request Header**:
```
X-API-Key: your-api-token-here
```

**Error Responses**:
- `401 Unauthorized`: Missing or invalid API key

## Logging Configuration

The server uses Python's built-in logging system with both console and rotating file handlers for comprehensive log management.

**Log Files**:
- Location: `logs/server.log` (relative to project root)
- Rotation: Automatic when file reaches 10 MB
- Backup Count: 5 backup files retained (e.g., `server.log.1`, `server.log.2`, etc.)
- Total Storage: Up to 60 MB (10 MB active + 5 × 10 MB backups)

**Log Format**:
```
[DD/MM/YYYY | HH:MM:SS] (LEVEL) module: message
```

**Example**:
```
[22/11/2025 | 14:30:45] (INFO) template_server: Server starting on https://localhost:443/api
[22/11/2025 | 14:30:46] (INFO) request_logging_middleware: Request: GET /api/health from 192.168.1.100
[22/11/2025 | 14:30:46] (INFO) request_logging_middleware: Response: GET /api/health -> 200
```

**Note:** The server host and port are configured via `HOST` and `PORT` environment variables in `.env` (default: `localhost:443`).

## Request Logging

All incoming requests and responses are automatically logged for monitoring and debugging purposes.

**Logged Information**:
- **Request**: HTTP method, path, client IP address
- **Response**: HTTP method, path, status code
- **Authentication**: API key validation attempts

**Log Levels**:
- `INFO`: Successful requests and responses
- `WARNING`: Authentication failures (missing or invalid API keys)
- `DEBUG`: Successful API key validations
- `ERROR`: Server errors and exceptions

**Example Log Output**:
```
INFO: Request: GET /api/health from 192.168.1.100
DEBUG: API key validated successfully
INFO: Response: GET /api/health -> 200
```

## Security Headers

All API responses include security headers to protect against common web vulnerabilities:

**Headers Included**:
- `Strict-Transport-Security`: Forces HTTPS connections (HSTS)
- `X-Content-Type-Options`: Prevents MIME-type sniffing
- `X-Frame-Options`: Prevents clickjacking attacks
- `Content-Security-Policy`: Controls which resources can be loaded
- `X-XSS-Protection`: Enables browser XSS filtering
- `Referrer-Policy`: Controls referrer information sent with requests

**Configuration** (`config.json`):
```json
{
  "security": {
    "hsts_max_age": 31536000,
    "content_security_policy": "default-src 'self'"
  }
}
```

- `hsts_max_age`: Duration in seconds that browsers should remember to only access the site via HTTPS (default: 1 year)
- `content_security_policy`: CSP directive controlling resource loading (default: only allow resources from same origin)

## CORS (Cross-Origin Resource Sharing)

CORS allows controlled access to the API from web applications hosted on different domains. By default, CORS is **disabled** for security.

**Configuration** (`config.json`):
```json
{
  "cors": {
    "enabled": false,
    "allow_origins": ["*"],
    "allow_credentials": true,
    "allow_methods": ["GET"],
    "allow_headers": ["Content-Type", "X-API-Key"],
    "expose_headers": [],
    "max_age": 600
  }
}
```

**Configuration Options**:
- `enabled`: Enable/disable CORS (default: `false`)
- `allow_origins`: List of allowed origins (use `["*"]` for all, or specify domains like `["https://example.com"]`)
- `allow_credentials`: Whether to allow credentials (cookies, authorization headers) in cross-origin requests (default: `true`)
- `allow_methods`: HTTP methods allowed for cross-origin requests (default: `["GET"]`)
- `allow_headers`: Headers allowed in cross-origin requests (default: `["Content-Type", "X-API-Key"]`)
- `expose_headers`: Headers exposed to the browser in responses
- `max_age`: Maximum age (in seconds) for CORS preflight cache (default: 600 seconds)

**Security Considerations**:
- For production, specify exact origins instead of `["*"]` to prevent unauthorized access
- Set `allow_credentials: true` only if your application requires authentication cookies or headers
- Limit `allow_methods` and `allow_headers` to only what your frontend needs

**Example Production Configuration**:
```json
{
  "cors": {
    "enabled": true,
    "allow_origins": ["https://yourdomain.com", "https://app.yourdomain.com"],
    "allow_credentials": true,
    "allow_methods": ["GET", "POST", "PUT", "DELETE"],
    "allow_headers": ["Content-Type", "X-API-Key"],
    "expose_headers": ["X-RateLimit-Limit", "X-RateLimit-Remaining"],
    "max_age": 3600
  }
}
```

## Rate Limiting

API endpoints are rate-limited to prevent abuse. When the rate limit is exceeded, the server responds with:

**Response**:
- Status Code: `429 Too Many Requests`
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

Default rate limit: **100 requests per minute** per IP address.

Rate limits can be configured in `config.json`.

## Endpoints

### GET /api/health

**Purpose**: Simple health check of the server.

**Authentication**: Not required (publicly accessible)

**Rate Limiting**: Subject to rate limits (default: 100/minute)

**Request**: None

**Response Model**: `GetHealthResponse`
- `message` (string): Status message
- `timestamp` (string): ISO 8601 timestamp

**Example Request**:
```bash
curl -k https://localhost:443/api/health
```

**Example Response** (200 OK - Healthy):
```json
{
  "message": "Server is healthy",
  "timestamp": "2025-11-22T12:00:00.000000Z"
}
```

### GET /api/login

**Purpose**: Verify API token and return successful login message.

**Authentication**: Required (API key must be provided)

**Rate Limiting**: Subject to rate limits (default: 100/minute)

**Request**: None

**Response Model**: `GetLoginResponse`
- `message` (string): Login status message
- `timestamp` (string): ISO 8601 timestamp

**Example Request**:
```bash
curl -k https://localhost:443/api/login \
  -H "X-API-Key: your-api-token-here"
```

**Example Response** (200 OK):
```json
{
  "message": "Login successful.",
  "timestamp": "2025-11-22T12:00:00.000000Z"
}
```

## Static File Serving

The server can optionally serve static files (HTML, CSS, JavaScript, images) from a `static/` directory if it exists, enabling you to host Single Page Applications (SPAs) alongside the API.

**Directory Structure**:
```
project-root/
├── static/           # Static files directory
│   ├── index.html    # Main entry point
│   ├── 404.html      # Custom 404 page (optional)
│   └── ...
```

**Implementation**:
The server uses FastAPI's built-in `StaticFiles` mounting for optimized static file serving:
- Mounted at root (`/`) with `html=True` to automatically serve `index.html` for directories
- Custom exception handler intercepts 404 errors to serve `404.html` when available

**Routing Behavior**:
1. **Exact file match**: If the requested path matches a file, it's served directly by `StaticFiles`
2. **Directory with index.html**: Automatically served when `html=True` is enabled
3. **404.html fallback**: Custom exception handler catches 404 errors and serves `404.html` if present
4. **HTTP 404 error**: If no fallback exists, returns standard FastAPI 404 error

**Example Requests**:
```bash
# Serve index.html
curl -k https://localhost:443/index.html

# Serve directory index (automatically serves index.html)
curl -k https://localhost:443/app/

# 404 fallback (custom exception handler serves 404.html if present)
curl -k https://localhost:443/nonexistent/path
```

**Important Notes**:
- **No Authentication**: Static files are served **without** API key verification
- **No Rate Limiting**: Static file mounting bypasses rate limiting for performance
- **Priority**: API routes (`/api/*`) registered before mounting take precedence
- **SPA Support**: Automatic `index.html` serving enables client-side routing for SPAs

## Request and Response Models (Pydantic)

The primary Pydantic models are defined in `python_template_server/models.py`:
- `BaseResponse`: Base model with message and timestamp fields
- `GetHealthResponse`: Extends BaseResponse for health endpoint responses
- `GetLoginResponse`: Extends BaseResponse for login endpoint responses
- `TemplateServerConfig`: Configuration model for server settings (security, rate limiting, JSON response)

**Extending Configurations**: Extend the `TemplateServerConfig` class to get the necessary server setup configuration.

**Extending Models**: When building your own server, create custom response models by extending `BaseResponse` for consistent API responses.

## API Documentation

FastAPI automatically generates interactive API documentation, providing two different interfaces for exploring and testing the API.

### Swagger UI (/api/docs)

**URL**: `https://localhost:443/api/docs`

**Purpose**: Interactive API documentation with "Try it out" functionality

**Features**:
- Execute API calls directly from the browser
- View request/response schemas
- Test authentication with API keys
- Explore all available endpoints
- View models and their properties

### ReDoc (/api/redoc)

**URL**: `https://localhost:443/api/redoc`

**Purpose**: Alternative API documentation with a clean, three-panel layout

**Features**:
- Read-only documentation interface
- Clean, responsive design
- Search functionality
- Detailed schema information
- Markdown support in descriptions
