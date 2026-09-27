# Deployment Guide

## Local Development

### Backend Setup

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy and configure environment:
   ```bash
   cp .env.example .env
   ```

4. Run migrations:
   ```bash
   python manage.py makemigrations core orders
   python manage.py migrate
   ```

5. Create superuser:
   ```bash
   python manage.py createsuperuser
   ```

6. Run development server:
   ```bash
   python manage.py runserver
   ```

### Frontend Setup

1. Navigate to frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start development server:
   ```bash
   npm start
   ```

Backend runs on `http://localhost:8000`, frontend on `http://localhost:3000`.

## Production Deployment

### Backend (AWS EC2 / DigitalOcean)

1. Install system dependencies:
   ```bash
   sudo apt update
   sudo apt install python3.10 python3.10-venv postgresql postgresql-contrib nginx redis-server
   ```

2. Clone repository and setup:
   ```bash
   git clone <repo> marketplace
   cd marketplace
   python3.10 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Configure PostgreSQL:
   ```bash
   sudo -u postgres createdb marketplace_db
   sudo -u postgres createuser marketplace_user
   sudo -u postgres psql
   ALTER USER marketplace_user WITH PASSWORD 'strong_password';
   ALTER ROLE marketplace_user SET client_encoding TO 'utf8';
   GRANT ALL PRIVILEGES ON DATABASE marketplace_db TO marketplace_user;
   ```

4. Set production environment:
   ```bash
   cp .env.example .env
   # Edit .env with production settings:
   # DEBUG=False
   # SECRET_KEY=<generate-strong-key>
   # DB_ENGINE=postgresql
   # DB_NAME=marketplace_db
   # DB_USER=marketplace_user
   # DB_PASSWORD=<strong_password>
   # DB_HOST=localhost
   # ALLOWED_HOSTS=yourdomain.com
   # SECURE_SSL_REDIRECT=True
   # SESSION_COOKIE_SECURE=True
   # CSRF_COOKIE_SECURE=True
   ```

5. Run migrations:
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

6. Create Gunicorn service (`/etc/systemd/system/marketplace.service`):
   ```ini
   [Unit]
   Description=Marketplace Gunicorn Application
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/home/ubuntu/marketplace
   Environment="PATH=/home/ubuntu/marketplace/venv/bin"
   ExecStart=/home/ubuntu/marketplace/venv/bin/gunicorn \
     --workers 4 \
     --bind unix:/run/gunicorn.sock \
     marketplace.wsgi:application

   [Install]
   WantedBy=multi-user.target
   ```

7. Start Gunicorn:
   ```bash
   sudo systemctl start marketplace
   sudo systemctl enable marketplace
   ```

8. Configure Nginx (`/etc/nginx/sites-available/marketplace`):
   ```nginx
   upstream gunicorn {
       server unix:/run/gunicorn.sock;
   }

   server {
       listen 80;
       server_name yourdomain.com www.yourdomain.com;
       return 301 https://$server_name$request_uri;
   }

   server {
       listen 443 ssl http2;
       server_name yourdomain.com www.yourdomain.com;

       ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

       client_max_body_size 100M;

       location /static/ {
           alias /home/ubuntu/marketplace/staticfiles/;
       }

       location /media/ {
           alias /home/ubuntu/marketplace/media/;
       }

       location / {
           proxy_pass http://gunicorn;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

9. Enable Nginx site and restart:
   ```bash
   sudo ln -s /etc/nginx/sites-available/marketplace /etc/nginx/sites-enabled/
   sudo systemctl restart nginx
   ```

10. Setup SSL with Let's Encrypt:
    ```bash
    sudo apt install certbot python3-certbot-nginx
    sudo certbot certonly --nginx -d yourdomain.com -d www.yourdomain.com
    ```

### Frontend (Vercel or Netlify)

1. Push to GitHub
2. Connect Vercel/Netlify to repository
3. Set build command: `npm run build`
4. Set publish directory: `build`
5. Set environment variables (REACT_APP_API_URL)

Or self-host:
```bash
npm run build
# Serve `build/` directory with web server
```

### Redis for Celery

```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### Celery Worker

1. Create service (`/etc/systemd/system/celery.service`):
   ```ini
   [Unit]
   Description=Marketplace Celery Worker
   After=network.target

   [Service]
   User=www-data
   WorkingDirectory=/home/ubuntu/marketplace
   Environment="PATH=/home/ubuntu/marketplace/venv/bin"
   ExecStart=/home/ubuntu/marketplace/venv/bin/celery -A marketplace worker -l info

   [Install]
   WantedBy=multi-user.target
   ```

2. Start worker:
   ```bash
   sudo systemctl start celery
   sudo systemctl enable celery
   ```

## Monitoring

- Use Sentry for error tracking
- Setup CloudWatch/Datadog for monitoring
- Configure log aggregation
- Monitor database performance

## Backup Strategy

- Daily database backups to S3
- Weekly code backups
- Test restore procedures monthly

## Security Checklist

- [ ] Set strong SECRET_KEY
- [ ] Enable SSL/TLS
- [ ] Configure firewall rules
- [ ] Setup fail2ban for brute force protection
- [ ] Enable database encryption
- [ ] Use environment variables for secrets
- [ ] Implement rate limiting
- [ ] Regular security audits
- [ ] Keep dependencies updated
