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
- [Rate Limiting](#rate-limiting)
- [Prometheus Metrics](#prometheus-metrics)
  - [GET /api/metrics](#get-apimetrics)
    - [Standard HTTP Metrics (via `prometheus-fastapi-instrumentator`)](#standard-http-metrics-via-prometheus-fastapi-instrumentator)
    - [Custom Application Metrics](#custom-application-metrics)
  - [Accessing Dashboards](#accessing-dashboards)
    - [Prometheus Dashboard](#prometheus-dashboard)
    - [Grafana Dashboards](#grafana-dashboards)
- [Endpoints](#endpoints)
  - [GET /api/health](#get-apihealth)
  - [GET /api/login](#get-apilogin)
- [Request and Response Models (Pydantic)](#request-and-response-models-pydantic)

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

## Rate Limiting

API endpoints are rate-limited to prevent abuse. When the rate limit is exceeded, the server responds with:

**Response**:
- Status Code: `429 Too Many Requests`
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

Default rate limit: **100 requests per minute** per IP address.

Rate limits can be configured in `config.json`.

## Prometheus Metrics

The server exposes Prometheus-compatible metrics for monitoring and observability.

### GET /api/metrics

- **Purpose**: Expose Prometheus metrics for scraping and monitoring.
- **Format**: Prometheus text-based exposition format.

**Metrics Exposed**:

#### Standard HTTP Metrics (via `prometheus-fastapi-instrumentator`)
- `http_requests_total`: Total number of HTTP requests by method, path, and status code
- `http_request_duration_seconds`: HTTP request latency histogram by method and path
- `http_requests_in_progress`: Number of HTTP requests currently being processed

#### Custom Application Metrics

**Authentication Metrics**:
- `auth_success_total`: Counter tracking successful API key validations
- `auth_failure_total{reason}`: Counter tracking failed authentication attempts with labels:
  - `reason="missing"`: No API key provided in request
  - `reason="invalid"`: Invalid or incorrect API key
  - `reason="error"`: Error during token verification

**Rate Limiting Metrics**:
- `rate_limit_exceeded_total{endpoint}`: Counter tracking requests that exceeded rate limits, labeled by endpoint path

### Accessing Dashboards

The application includes pre-configured monitoring dashboards for visualization:

#### Prometheus Dashboard
- **URL**: http://localhost:9090
- **Purpose**: Query and visualize raw metrics data
- **Features**: Built-in query interface, graphing, and alerting

#### Grafana Dashboards
- **URL**: http://localhost:3000
- **Credentials**: admin / admin (change after first login)
- **Pre-configured Dashboards**:
  - **Authentication Metrics**: Tracks successful and failed authentication attempts, including reasons for failures
  - **Rate Limiting Metrics**: Monitors requests that exceed rate limits by endpoint

To access the dashboards, the containers for Grafana and Prometheus must be running.
See the [Docker documentation](./DOCKER_DEPLOYMENT.md) for information on how to run these.

## Endpoints

### GET /api/health

**Purpose**: Simple health check of the server.

**Authentication**: Not required (publicly accessible)

**Rate Limiting**: Subject to rate limits (default: 100/minute)

**Request**: None

**Response Model**: `GetHealthResponse`
- `code` (int): HTTP status code
- `message` (string): Status message
- `timestamp` (string): ISO 8601 timestamp
- `status` (string): Health status indicator (HEALTHY/DEGRADED/UNHEALTHY)

**Health Status Indicators**:
- `HEALTHY`: Server is fully operational and token is configured
- `UNHEALTHY`: Server token is not configured (returns 500 status code)

**Example Request**:
```bash
curl -k https://localhost:443/api/health
```

**Example Response** (200 OK - Healthy):
```json
{
  "code": 200,
  "message": "Server is healthy",
  "timestamp": "2025-11-22T12:00:00.000000Z",
  "status": "HEALTHY"
}
```

**Example Response** (500 Internal Server Error - Unhealthy):
```json
{
  "code": 500,
  "message": "Server token is not configured",
  "timestamp": "2025-11-22T12:00:00.000000Z",
  "status": "UNHEALTHY"
}
```

### GET /api/login

**Purpose**: Verify API token and return successful login message.

**Authentication**: Required (API key must be provided)

**Rate Limiting**: Subject to rate limits (default: 100/minute)

**Request**: None

**Response Model**: `GetLoginResponse`
- `code` (int): HTTP status code
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
  "code": 200,
  "message": "Login successful.",
  "timestamp": "2025-11-22T12:00:00.000000Z"
}
```

**Error Responses**:
- `401 Unauthorized`: Missing or invalid API key
- `429 Too Many Requests`: Rate limit exceeded

## Request and Response Models (Pydantic)

The primary Pydantic models are defined in `python_template_server/models.py`:
- `BaseResponse`: Base model with code, message, and timestamp fields
- `GetHealthResponse`: Extends BaseResponse with status field (HEALTHY/UNHEALTHY)
- `GetLoginResponse`: Extends BaseResponse for login endpoint responses
- `TemplateServerConfig`: Configuration model for server settings (security, rate limiting, JSON response)

**Extending Configurations**: Extend the `TemplateServerConfig` class to get the necessary server setup configuration.

**Extending Models**: When building your own server, create custom response models by extending `BaseResponse` for consistent API responses.
