<!-- omit from toc -->
# Grafana Configuration

This directory contains Grafana provisioning configuration and custom dashboards for the Python Template Server.

<!-- omit from toc -->
## Table of Contents
- [Directory Structure](#directory-structure)
- [Dashboards](#dashboards)
  - [1. Health Metrics Dashboard](#1-health-metrics-dashboard)
  - [2. Authentication Metrics Dashboard](#2-authentication-metrics-dashboard)
  - [3. Rate Limiting \& Performance Metrics Dashboard](#3-rate-limiting--performance-metrics-dashboard)
- [Accessing Dashboards](#accessing-dashboards)
- [Customizing Dashboards](#customizing-dashboards)
  - [Adding New Panels](#adding-new-panels)
  - [Creating New Dashboards](#creating-new-dashboards)
- [Available Metrics](#available-metrics)
  - [Health Metrics](#health-metrics)
  - [Authentication Metrics](#authentication-metrics)
  - [Rate Limiting Metrics](#rate-limiting-metrics)
  - [HTTP Metrics (from prometheus-fastapi-instrumentator)](#http-metrics-from-prometheus-fastapi-instrumentator)


## Directory Structure

```
grafana/
├── provisioning/
│   ├── datasources/
│   │   └── prometheus.yml          # Prometheus datasource configuration
│   └── dashboards/
│       └── dashboards.yml          # Dashboard provisioning configuration
└── dashboards/
    ├── authentication-metrics.json # Authentication monitoring dashboard
    ├── health-metrics.json         # Health monitoring dashboard
    └── rate-limiting-metrics.json  # Rate limiting & performance dashboard
```

## Dashboards

### 1. Health Metrics Dashboard

**UID**: `health-metrics`
**Path**: `/d/health-metrics`

**Panels**:
- **API Token Configuration Status**: Gauge showing if API token is configured
- **Health Checks (Last 5 Minutes)**: Gauge of recent health check requests
- **Health Check Average Response Time**: Gauge of average response time for health checks
- **Token Configuration Status Over Time**: Timeseries of token configuration status
- **Health Check Request Rate (per second)**: Timeseries of health check request rates
- **Health Check Response Time Percentiles**: Timeseries of p50, p95, p99 response times

**Use Cases**:
- Monitor server health and configuration status
- Track health check performance and frequency
- Detect configuration issues (e.g., missing API token)

### 2. Authentication Metrics Dashboard

**UID**: `auth-metrics`
**Path**: `/d/auth-metrics`

**Panels**:
- **Authentication Rate**: Success and failure rates per second
- **Total Successful Authentications**: Gauge showing cumulative successes
- **Total Failed Authentications**: Gauge showing cumulative failures
- **Authentication Failures by Reason**: Breakdown of failures (missing, invalid, error)
- **Authentication Success Rate**: Percentage of successful attempts

**Use Cases**:
- Monitor authentication health
- Detect brute force attacks (high failure rates)
- Identify common authentication issues

### 3. Rate Limiting & Performance Metrics Dashboard

**UID**: `rate-limit-metrics`
**Path**: `/d/rate-limit-metrics`

**Panels**:
- **Rate Limit Exceeded Events**: Rate of violations per second by endpoint
- **Total Rate Limit Violations**: Cumulative violation count
- **Rate Limit Violations by Endpoint**: Breakdown by endpoint
- **HTTP Request Rate**: Overall request rates by method, handler, and status
- **HTTP Request Duration**: 95th and 99th percentile latency

**Use Cases**:
- Monitor rate limit effectiveness
- Identify endpoints being abused
- Track API performance and latency
- Capacity planning

## Accessing Dashboards

1. Generate API key (if not done): `uv run generate-new-token`
2. Start services: `docker compose up -d`
3. Open Grafana: http://localhost:3000
4. Login with default credentials: `admin/admin`
5. Navigate to: Dashboards → Browse → Python Template Server folder

## Customizing Dashboards

### Adding New Panels

1. Open a dashboard in Grafana
2. Click "Add panel" → "Add a new panel"
3. Configure visualization and query
4. Save the dashboard
5. Export JSON: Dashboard settings → JSON Model
6. Save to this directory for version control

### Creating New Dashboards

1. Create dashboard in Grafana UI
2. Export as JSON: Dashboard settings → JSON Model → Copy to clipboard
3. Save JSON file in `grafana/dashboards/`
4. Restart Grafana: `docker compose restart grafana`

## Available Metrics

### Health Metrics
- `token_configured` - Binary metric indicating if API token is configured (0 or 1)

### Authentication Metrics
- `auth_success_total` - Successful authentication count
- `auth_failure_total{reason="missing|invalid|error"}` - Failed authentication count by reason

### Rate Limiting Metrics
- `rate_limit_exceeded_total{endpoint="/api/health"}` - Rate limit violations per endpoint

### HTTP Metrics (from prometheus-fastapi-instrumentator)
- `http_requests_total{method, handler, status}` - Total requests
- `http_request_duration_seconds_bucket` - Request duration histogram
- `http_requests_in_progress` - Current active requests
