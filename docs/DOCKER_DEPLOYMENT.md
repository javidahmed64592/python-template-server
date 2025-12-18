<!-- omit from toc -->
# Docker Deployment Guide

This guide provides comprehensive instructions for deploying the Python Template Server using Docker and Docker Compose, including metrics visualization with Prometheus and Grafana.

<!-- omit from toc -->
## Table of Contents
- [Prerequisites](#prerequisites)
  - [Check Prerequisites](#check-prerequisites)
- [Quick Start](#quick-start)
  - [1. Generate API Key](#1-generate-api-key)
  - [2. Start Services](#2-start-services)
- [Configuration](#configuration)
  - [Docker Compose Services](#docker-compose-services)
  - [Environment Variables](#environment-variables)
  - [Server Configuration](#server-configuration)
- [Building and Running](#building-and-running)
  - [Development Mode](#development-mode)
  - [Managing Containers](#managing-containers)
- [Accessing Services](#accessing-services)
  - [Python Template Server](#python-template-server)
  - [Prometheus](#prometheus)
  - [Grafana](#grafana)
- [Metrics Visualization](#metrics-visualization)
  - [Available Metrics](#available-metrics)
    - [Authentication Metrics](#authentication-metrics)
    - [Rate Limiting Metrics](#rate-limiting-metrics)
    - [HTTP Metrics (provided by prometheus-fastapi-instrumentator)](#http-metrics-provided-by-prometheus-fastapi-instrumentator)
  - [Custom Dashboard Setup](#custom-dashboard-setup)
  - [View Container Logs](#view-container-logs)

## Prerequisites

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **API Key**: Generate using `generate-new-token` command (see below)

### Check Prerequisites

```bash
docker --version
```

## Quick Start

### 1. Generate API Key

Before starting the containers, you need to generate an API key:

```bash
# Install the package locally (if not already installed)
uv sync

# Generate a new API token (automatically creates/updates .env file)
uv run generate-new-token
```

This will:
- Generate a cryptographically secure **raw token** (displayed once - keep this secret!)
- Hash the token using SHA-256
- Automatically save the hash to `.env` as `API_TOKEN_HASH`

**Important**:
- Save the displayed raw token - you'll need it for authenticated API requests
- The `.env` file is automatically created/updated by the command
- **The same `.env` file is shared between local development and Docker containers**, allowing you to use the same token across both environments

### 2. Start Services

```bash
# Start all services (FastAPI server, Prometheus, Grafana)
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

**Token Management in Docker**:

The Docker startup script automatically handles token generation with the following logic:

1. **Existing `.env` file**: If you've already run `uv run generate-new-token` locally, the Docker container will use the existing token hash from your `.env` file. This means:
   - You can generate a token once during development and use it consistently across local and Docker environments
   - The same API token works for both `uv run python-template-server` and `docker compose up`
   - No need to regenerate tokens when switching between environments

2. **No `.env` file**: If no `.env` file exists (e.g., fresh checkout), the Docker startup script will automatically generate a new token. However:
   - The auto-generated token is only displayed in the container logs
   - It's recommended to generate tokens locally using `uv run generate-new-token` so you can save the raw token for API requests

## Configuration

### Docker Compose Services

The `docker-compose.yml` defines three services:

1. **python-template-server** (Port 443)
   - FastAPI application with HTTPS
   - Auto-generates self-signed certificates on first run (if not present)
   - Uses existing `.env` file if available, otherwise generates a new token on startup
   - Exposes `/api/metrics` endpoint for Prometheus

2. **prometheus** (Port 9090)
   - Metrics collection and storage
   - Scrapes `/api/metrics` endpoint every 15 seconds
   - Persistent storage via Docker volume

3. **grafana** (Port 3000)
   - Metrics visualization dashboards
   - Pre-configured Prometheus datasource
   - Custom dashboards for authentication and rate limiting
   - Default credentials: `admin/admin`

### Environment Variables

Configure the FastAPI server using environment variables in `docker-compose.yml`:

```yaml
environment:
  - API_TOKEN_HASH=${API_TOKEN_HASH}
```

The `API_TOKEN_HASH` is loaded from your local `.env` file.
If the `.env` file exists when you run `docker compose up`, the container will use that token hash.
Otherwise, the container startup script will generate a new token and create the `.env` file.

### Server Configuration

Modify `config.json` to customize:

- **Host and Port**: Change server binding address
- **Security Headers**: Configure HSTS and CSP policies
- **Rate Limiting**: Adjust rate limit rules
- **Certificates**: Set certificate validity period

## Building and Running

### Development Mode

```bash
# Stop containers if required
docker compose down

# Build and start in background
docker compose up --build -d
```

### Managing Containers

```bash
# View running containers
docker compose ps

# Stop services
docker compose stop

# Start stopped services
docker compose start

# Restart services
docker compose restart python-template-server

# Remove containers and volumes
docker compose down -v
```

## Accessing Services

### Python Template Server

**Base URL**: `https://localhost:443`

**API Endpoints**:
- Metrics: `GET /api/metrics` (publicly accessible, no authentication required)
- Health Check: `GET /api/health` (publicly accessible, no authentication required)
- Login: `GET /api/login` (requires authentication with X-API-Key header)
- Custom Endpoints: Defined in your server subclass (authentication may be required)

**Example Request**:
```bash
# Using curl (with self-signed cert)
curl -k https://localhost:443/api/health

# Login endpoint (authenticated)
curl -k -H "X-API-Key: your-token-here" https://localhost:443/api/login
```

### Prometheus

**URL**: `http://localhost:9090`

**Features**:
- Query metrics directly
- View scrape targets and status
- Create custom queries

### Grafana

**URL**: `http://localhost:3000`

**Default Credentials**:
- Username: `admin`
- Password: `admin` (change on first login)

**Pre-installed Dashboards**:
1. **Authentication Metrics** (`/d/auth-metrics`)
   - Success/failure rates
   - Total authentication attempts
   - Failure reasons breakdown
   - Success rate percentage

2. **Rate Limiting & Performance** (`/d/rate-limit-metrics`)
   - Rate limit violations by endpoint
   - HTTP request rates
   - Request duration percentiles
   - Total violations gauge

## Metrics Visualization

### Available Metrics

#### Authentication Metrics
- `auth_success_total`: Successful authentication attempts
- `auth_failure_total{reason}`: Failed attempts by reason (missing, invalid, error)

#### Rate Limiting Metrics
- `rate_limit_exceeded_total{endpoint}`: Rate limit violations per endpoint

#### HTTP Metrics (provided by prometheus-fastapi-instrumentator)
- `http_requests_total`: Total HTTP requests
- `http_request_duration_seconds`: Request latency histogram
- `http_requests_in_progress`: Current in-flight requests

### Custom Dashboard Setup

1. **Access Grafana**: Navigate to `http://localhost:3000`
2. **Login**: Use `admin/admin`
3. **Navigate**: Go to Dashboards → Browse → Python Template Server folder
4. **View**: Select either dashboard to visualize metrics

### View Container Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f python-template-server

# Last 100 lines
docker compose logs --tail=100 prometheus
```
