# Production Deployment Guide

## Pre-Deployment Checklist

- [ ] Generate strong SECRET_KEY
- [ ] Obtain real Stripe API credentials
- [ ] Obtain real OpenAI API key
- [ ] Set up production PostgreSQL database
- [ ] Configure domain/SSL certificates
- [ ] Set up monitoring and logging
- [ ] Review security settings
- [ ] Test backup/restore procedures
- [ ] Set up CI/CD pipeline
- [ ] Load testing

## Environment Setup

### 1. Generate Secure Secrets

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate database password
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

### 2. Production .env File

```env
# Database (use managed service like AWS RDS)
DATABASE_URL=postgresql://username:password@prod-db-host:5432/ecommerce_prod

# Security
SECRET_KEY=your-generated-secret-key-32-chars-min
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Stripe (real keys from stripe.com)
STRIPE_SECRET_KEY=sk_live_YOUR_REAL_SECRET_KEY
STRIPE_PUBLISHABLE_KEY=pk_live_YOUR_REAL_PUBLISHABLE_KEY

# OpenAI
OPENAI_API_KEY=sk-YOUR_REAL_OPENAI_KEY

# UPS (optional, implement when needed)
UPS_USERNAME=your_ups_username
UPS_PASSWORD=your_ups_password
UPS_ACCESS_LICENSE=your_ups_license

# CORS (set to your domain)
CORS_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]
```

## Docker Deployment

### 1. Build Production Images

```bash
# Build backend
docker build -t ecommerce-backend:latest .

# Build frontend
docker build -t ecommerce-frontend:latest ./frontend

# Tag for registry
docker tag ecommerce-backend:latest your-registry.com/ecommerce-backend:latest
docker tag ecommerce-frontend:latest your-registry.com/ecommerce-frontend:latest
```

### 2. Push to Container Registry

```bash
# Push to Docker Hub, ECR, GCR, etc.
docker push your-registry.com/ecommerce-backend:latest
docker push your-registry.com/ecommerce-frontend:latest
```

### 3. Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  backend:
    image: your-registry.com/ecommerce-backend:latest
    container_name: ecommerce_backend_prod
    environment:
      - DATABASE_URL=postgresql://ecommerce:${DB_PASSWORD}@postgres:5432/ecommerce_prod
      - SECRET_KEY=${SECRET_KEY}
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
      - STRIPE_PUBLISHABLE_KEY=${STRIPE_PUBLISHABLE_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - CORS_ORIGINS=["https://yourdomain.com"]
    restart: always
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - ecommerce-network

  frontend:
    image: your-registry.com/ecommerce-frontend:latest
    container_name: ecommerce_frontend_prod
    environment:
      - REACT_APP_API_URL=https://api.yourdomain.com
    restart: always
    networks:
      - ecommerce-network

  nginx:
    image: nginx:alpine
    container_name: ecommerce_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
      - ./certbot:/etc/letsencrypt:ro
    restart: always
    depends_on:
      - backend
      - frontend
    networks:
      - ecommerce-network

networks:
  ecommerce-network:
    driver: bridge
```

### 4. Nginx Configuration

Create `nginx.conf`:

```nginx
user nginx;
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    upstream backend {
        server backend:8000;
    }

    upstream frontend {
        server frontend:3000;
    }

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS configuration
    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # API routes
        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # API docs
        location /docs {
            proxy_pass http://backend/docs;
            proxy_set_header Host $host;
        }

        location /openapi.json {
            proxy_pass http://backend/openapi.json;
            proxy_set_header Host $host;
        }

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Gzip compression
        gzip on;
        gzip_types text/plain text/css text/xml text/javascript
                   application/x-javascript application/xml+rss
                   application/json;
    }
}
```

## Cloud Deployment

### AWS Deployment

1. **RDS for PostgreSQL**
   - Create RDS instance with Multi-AZ enabled
   - Enable automated backups (30 days minimum)
   - Use VPC security groups to restrict access

2. **ECS (Elastic Container Service)**
   - Create ECS cluster
   - Define task definitions for backend and frontend
   - Set up load balancer (ALB)
   - Configure auto-scaling

3. **S3 for Images** (optional)
   - Create S3 bucket
   - Enable versioning
   - Configure CORS for frontend access
   - Set up CloudFront distribution

4. **CloudWatch**
   - Set up log groups
   - Create alarms for error rates
   - Monitor database metrics

### Google Cloud Deployment

1. **Cloud SQL for PostgreSQL**
   - Create Cloud SQL instance
   - Enable backups and automatic failover
   - Configure firewall rules

2. **Cloud Run**
   - Deploy backend container
   - Deploy frontend container
   - Set environment variables

3. **Cloud Storage**
   - Store product images
   - Configure CDN with Cloud CDN

### Heroku Deployment

```bash
# Install Heroku CLI
npm install -g heroku

# Login
heroku login

# Create app
heroku create your-app-name

# Add PostgreSQL
heroku addons:create heroku-postgresql:standard-0

# Set environment variables
heroku config:set SECRET_KEY=your-secret-key
heroku config:set STRIPE_SECRET_KEY=sk_live_...

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

## Database Migration

### Before Production Launch

1. **Backup Development Database**
```bash
pg_dump -U ecommerce -F c -b -v -f backup.dump ecommerce
```

2. **Restore to Production**
```bash
pg_restore -U ecommerce -d ecommerce_prod backup.dump
```

3. **Run Migrations**
```bash
# Alembic setup (when needed)
alembic upgrade head
```

4. **Verify Data**
```sql
SELECT COUNT(*) FROM users;
SELECT COUNT(*) FROM products;
SELECT SUM(total_amount) FROM orders;
```

## SSL/TLS Certificates

### Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Auto-renew
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

## Monitoring & Logging

### Application Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/ecommerce/app.log'),
        logging.StreamHandler()
    ]
)
```

### Monitoring Tools

1. **Prometheus & Grafana**
   - Track application metrics
   - Set up dashboards
   - Create alerts

2. **ELK Stack**
   - Elasticsearch for log storage
   - Logstash for processing
   - Kibana for visualization

3. **New Relic / Datadog**
   - Application performance monitoring
   - Distributed tracing
   - Alerting

## Security Hardening

### API Security

```python
# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# HTTPS only
CORS_ORIGINS = ["https://yourdomain.com"]

# Security headers
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response
```

### Database Security

- Use strong passwords
- Enable SSL connections
- Regular backups to isolated storage
- Encrypted at rest
- Network isolation (VPC/VPN)

### Frontend Security

- Enable CSP headers
- Sanitize user input
- Use HTTPS only
- Regular dependency updates
- Security scanning (Snyk, npm audit)

## Backup & Disaster Recovery

### Automated Backups

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/ecommerce"

mkdir -p $BACKUP_DIR

# Database backup
pg_dump -U ecommerce -F c -b -f $BACKUP_DIR/db_$DATE.dump ecommerce_prod

# Application files
tar -czf $BACKUP_DIR/app_$DATE.tar.gz /app

# Upload to S3
aws s3 cp $BACKUP_DIR/ s3://your-backup-bucket/ --recursive

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -mtime +30 -delete
```

### Recovery Procedure

1. Stop application
2. Restore database backup
3. Verify data integrity
4. Restart application
5. Run health checks

## Performance Optimization

### Backend

- Enable query result caching
- Use database connection pooling (already enabled)
- Implement pagination
- Add database indexing

### Frontend

- Code splitting with React.lazy()
- Image optimization
- Minification and compression
- CDN for static assets

### Database

```sql
-- Create indexes on frequently queried columns
CREATE INDEX idx_products_store_id ON products(store_id);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_cart_items_user_id ON cart_items(user_id);
```

## Post-Deployment

### Verify Health

```bash
# Health check
curl https://yourdomain.com/health

# API docs
curl https://yourdomain.com/docs

# Frontend
curl -I https://yourdomain.com
```

### Set Up Monitoring Alerts

- API response time > 2s
- Error rate > 1%
- Database connection pool exhausted
- Disk space < 10%
- CPU usage > 80%

### Performance Testing

```bash
# Load testing with Apache Bench
ab -n 10000 -c 100 https://yourdomain.com/api/products

# Or use k6 for more advanced testing
k6 run load-test.js
```

## Maintenance Schedule

- **Daily**: Monitor logs and metrics
- **Weekly**: Security updates review
- **Monthly**: Database maintenance, analyze queries
- **Quarterly**: Security audit, performance review
- **Annually**: Disaster recovery drill

## Scaling Considerations

1. **Horizontal Scaling**: Multiple backend instances behind load balancer
2. **Caching Layer**: Redis for session/query caching
3. **Message Queue**: Celery for async tasks
4. **Database Read Replicas**: For read-heavy workloads
5. **CDN**: CloudFront, Cloudflare for static assets
