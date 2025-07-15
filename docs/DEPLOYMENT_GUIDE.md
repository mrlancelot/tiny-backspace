# Tiny Backspace Deployment Guide

## Production Deployment

This guide covers deploying the Tiny Backspace API to production environments.

## Prerequisites

- Docker and Docker Compose
- Domain name with SSL certificate
- GitHub account with personal access token
- Daytona API access
- (Optional) Anthropic API key

## Deployment Options

### Option 1: Docker Compose (Recommended)

1. **Prepare environment**:
```bash
# Clone repository
git clone https://github.com/yourusername/tiny-backspace.git
cd tiny-backspace

# Create production env file
cp .env.example .env.production
# Edit .env.production with production values
```

2. **Configure production settings**:
```env
# .env.production
DAYTONA_API_KEY=your_production_key
GITHUB_TOKEN=your_github_token
DEBUG=false
REQUIRE_AUTH=true
API_KEY=generate_secure_api_key
ENABLE_TELEMETRY=true
OTEL_ENDPOINT=your_telemetry_endpoint
```

3. **Deploy with Docker Compose**:
```bash
# Use production compose file
docker-compose -f docker-compose.api.yml up -d

# Check logs
docker-compose -f docker-compose.api.yml logs -f
```

### Option 2: Kubernetes Deployment

1. **Create ConfigMap**:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tinybackspace-config
data:
  API_HOST: "0.0.0.0"
  API_PORT: "8000"
  DEBUG: "false"
  REQUIRE_AUTH: "true"
```

2. **Create Secret**:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: tinybackspace-secrets
type: Opaque
stringData:
  DAYTONA_API_KEY: "your_key"
  GITHUB_TOKEN: "your_token"
  API_KEY: "your_api_key"
```

3. **Deploy application**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tinybackspace-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tinybackspace-api
  template:
    metadata:
      labels:
        app: tinybackspace-api
    spec:
      containers:
      - name: api
        image: tinybackspace:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: tinybackspace-config
        - secretRef:
            name: tinybackspace-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

4. **Create Service**:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: tinybackspace-api
spec:
  selector:
    app: tinybackspace-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Option 3: Cloud Platform Deployment

#### AWS ECS

1. **Build and push image**:
```bash
# Build image
docker build -f api/Dockerfile -t tinybackspace-api .

# Tag for ECR
docker tag tinybackspace-api:latest $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/tinybackspace-api:latest

# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/tinybackspace-api:latest
```

2. **Create ECS task definition** with environment variables
3. **Deploy service** with auto-scaling

#### Google Cloud Run

```bash
# Build and submit
gcloud builds submit --tag gcr.io/PROJECT_ID/tinybackspace-api

# Deploy
gcloud run deploy tinybackspace-api \
  --image gcr.io/PROJECT_ID/tinybackspace-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "DAYTONA_API_KEY=xxx,GITHUB_TOKEN=xxx"
```

## Production Configuration

### 1. **Reverse Proxy (Nginx)**

```nginx
server {
    listen 443 ssl http2;
    server_name api.tinybackspace.com;

    ssl_certificate /etc/ssl/certs/tinybackspace.crt;
    ssl_certificate_key /etc/ssl/private/tinybackspace.key;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE specific
        proxy_set_header Cache-Control no-cache;
        proxy_buffering off;
        proxy_read_timeout 86400;
    }
}
```

### 2. **Process Manager (systemd)**

```ini
[Unit]
Description=Tiny Backspace API
After=network.target

[Service]
Type=exec
User=tinybackspace
WorkingDirectory=/opt/tinybackspace
Environment="PATH=/opt/tinybackspace/venv/bin"
EnvironmentFile=/opt/tinybackspace/.env.production
ExecStart=/opt/tinybackspace/venv/bin/python /opt/tinybackspace/api/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. **Monitoring Setup**

#### Prometheus Metrics

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'tinybackspace'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

#### Grafana Dashboard

Import the dashboard from `monitoring/grafana-dashboard.json`

## Security Checklist

- [ ] Enable HTTPS with valid SSL certificate
- [ ] Set strong API keys
- [ ] Configure rate limiting
- [ ] Enable authentication (`REQUIRE_AUTH=true`)
- [ ] Restrict CORS origins
- [ ] Use environment-specific secrets
- [ ] Enable security headers
- [ ] Configure firewall rules
- [ ] Set up intrusion detection
- [ ] Enable audit logging

## Performance Optimization

1. **Database Connection Pooling** (if using external DB)
2. **Redis Caching** for common operations
3. **CDN** for static assets
4. **Horizontal Scaling** with load balancer
5. **Resource Limits** on Daytona sandboxes

## Backup and Recovery

1. **Configuration Backup**:
```bash
# Backup configs
tar -czf tinybackspace-config-$(date +%Y%m%d).tar.gz .env.production *.yml
```

2. **Log Rotation**:
```logrotate
/var/log/tinybackspace/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 tinybackspace tinybackspace
}
```

## Troubleshooting

### Common Issues

1. **SSE Connection Drops**
   - Check proxy timeout settings
   - Ensure `proxy_buffering off`

2. **Sandbox Creation Fails**
   - Verify Daytona API connectivity
   - Check resource limits

3. **PR Creation Fails**
   - Verify GitHub token permissions
   - Check network connectivity

### Debug Commands

```bash
# Check API health
curl https://api.tinybackspace.com/health

# Test SSE endpoint
curl -N https://api.tinybackspace.com/api/code \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_key" \
  -d '{"repo_url": "...", "prompt": "..."}'

# View logs
docker logs -f tinybackspace-api

# Check metrics
curl https://api.tinybackspace.com/metrics
```

## Maintenance

### Regular Tasks

- **Weekly**: Review error logs and metrics
- **Monthly**: Update dependencies
- **Quarterly**: Security audit
- **Annually**: Review and rotate secrets

### Upgrade Process

1. Test in staging environment
2. Backup current deployment
3. Deploy with rolling update
4. Monitor for issues
5. Rollback if needed

## Support

For production support:
- Documentation: [README_TINYB.md](README_TINYB.md)
- Issues: GitHub Issues
- Email: support@tinybackspace.com