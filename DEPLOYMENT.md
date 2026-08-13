# StudentERP V1.0 Production Deployment Guide

This guide provides step-by-step instructions for deploying StudentERP (School Faculty Face Attendance SaaS) to a production Linux server using Docker Compose, Nginx, PostgreSQL, and Redis with wildcard SSL subdomains (`*.ourapp.com`).

---

## 1. Prerequisites

- Linux Server (Ubuntu 22.04 LTS or 24.04 LTS recommended)
- Minimum Hardware: 2 CPU Cores, 4 GB RAM, 20 GB SSD
- Domain Name with Wildcard DNS Records configured:
  - `A` Record: `ourapp.com` $\to$ `SERVER_IP`
  - `A` Record (Wildcard): `*.ourapp.com` $\to$ `SERVER_IP`
- Software installed on server:
  - Docker 24.0+ (`docker --version`)
  - Docker Compose v2 (`docker compose version`)

---

## 2. Environment Setup

1. Clone the repository on your server:
   ```bash
   git clone https://github.com/your-org/StudentERP1.git /opt/studenterp
   cd /opt/studenterp
   ```

2. Copy the environment configuration template:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and fill in secure credentials:
   ```env
   DEBUG=False
   SECRET_KEY=generate_a_secure_50_character_random_secret_key
   ALLOWED_HOSTS=.ourapp.com,ourapp.com
   POSTGRES_DB=studenterp_prod
   POSTGRES_USER=studenterp_dbuser
   POSTGRES_PASSWORD=your_strong_db_password
   ```

---

## 3. Provision Wildcard SSL Certificate (Certbot / Let's Encrypt)

Run Certbot to obtain a wildcard SSL certificate for `ourapp.com` and `*.ourapp.com`:

```bash
sudo apt update && sudo apt install -y certbot
sudo certbot certonly --manual --preferred-challenges dns -d "ourapp.com" -d "*.ourapp.com"
```

Copy or symlink the issued certificates to `nginx/certs/`:

```bash
mkdir -p nginx/certs
cp /etc/letsencrypt/live/ourapp.com/fullchain.pem nginx/certs/fullchain.pem
cp /etc/letsencrypt/live/ourapp.com/privkey.pem nginx/certs/privkey.pem
```

---

## 4. Docker Compose Deployment

1. Build and start the production container stack:
   ```bash
   docker compose up -d --build
   ```

2. Verify that all 4 containers are running healthily:
   ```bash
   docker compose ps
   ```
   *Expected output:*
   - `studenterp_db`: `healthy`
   - `studenterp_redis`: `healthy`
   - `studenterp_web`: `running`
   - `studenterp_nginx`: `running`

3. Create the initial Super Admin account:
   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

---

## 5. Security & Verification Checklist

- [x] Multi-tenant isolation verified (subdomain routing `school.ourapp.com`).
- [x] Privacy boundaries enforced (Super Admin prohibited from viewing biometric vectors).
- [x] Raw photo byte destruction verified (zero raw photo disk persistence).
- [x] Rate limiting active on `/login/` (5 req/min), `/biometrics/extract/` (10 req/min), and `/attendance/scan/` (60 req/min).
- [x] Production security headers active (`HSTS`, `XSS Filter`, `X-Frame-Options DENY`, `Secure Cookies`).
- [x] Automated test suite executed cleanly: `docker compose exec web python manage.py test`.

---

## 6. Maintenance & Backups

### Automated Database Backup Cron Job
Add a daily database backup cron job:

```bash
crontab -e
```
Add line:
```cron
0 2 * * * docker compose -f /opt/studenterp/docker-compose.yml exec -T db pg_dump -U studenterp_dbuser studenterp_prod | gzip > /opt/backups/db_$(date +\%Y\%m\%d).sql.gz
```
