# Academy CRM - Deployment Guide for Render.com

This guide provides step-by-step instructions for deploying Academy CRM to Render.com using Docker.

## Prerequisites

- Render.com account
- GitHub repository with your code
- Basic understanding of Docker and Django

## Overview

Academy CRM requires the following services on Render.com:
1. **PostgreSQL Database** - Main database
2. **Redis** - Caching and Celery message broker
3. **Web Service (API)** - Django REST API
4. **Background Worker** - Celery worker for async tasks
5. **Background Worker (Beat)** - Celery beat for scheduled tasks

## Step 1: Prepare Your Repository

Ensure your code is pushed to the `main` branch of your GitHub repository. The following files should be present:
- `Dockerfile`
- `.dockerignore`
- `requirements/prod.txt`
- `academy_crm/settings/prod.py`

## Step 2: Create PostgreSQL Database

1. Log in to [Render.com Dashboard](https://dashboard.render.com)
2. Click **"New +"** → **"PostgreSQL"**
3. Configure:
   - **Name:** `academy-crm-db`
   - **Database:** `academy_crm`
   - **User:** (auto-generated or custom)
   - **Region:** Oregon (US West) or your preferred region
   - **PostgreSQL Version:** 15 (recommended)
   - **Plan:** Starter ($7/month) or Standard ($25/month)
4. Click **"Create Database"**
5. **Important:** Note down the connection details:
   - Internal Database URL
   - Host
   - Port (usually 5432)
   - Database name
   - User
   - Password

## Step 3: Create Redis Instance

1. Click **"New +"** → **"Redis"**
2. Configure:
   - **Name:** `academy-crm-redis`
   - **Region:** Same as database (Oregon)
   - **Plan:** Starter ($10/month)
3. Click **"Create Redis"**
4. **Important:** Note down the **Internal Redis URL**

## Step 4: Create Web Service (API)

1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:
   - **Name:** `academy-crm-api`
   - **Environment:** `Docker`
   - **Region:** Oregon (US West)
   - **Branch:** `main`
   - **Root Directory:** (leave empty)
   - **Build Command:** (leave empty - Docker handles it)
   - **Start Command:** (leave empty - Dockerfile CMD is used)
   - **Instance Type:** Starter ($7/month) or Standard ($25/month)
   - **Health Check Path:** `/health/`

### Environment Variables for API Service

Add the following environment variables in the Render dashboard:

#### Required Variables

```
DJANGO_ENV=prod
SECRET_KEY=<generate-a-secure-random-key>
ALLOWED_HOSTS=academy-crm-api.onrender.com,your-custom-domain.com
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com,https://academy-crm-api.onrender.com
```

#### Database Variables (from Step 2)

```
DB_HOST=<your-postgres-host>
DB_NAME=academy_crm
DB_USER=<your-postgres-user>
DB_PASSWORD=<your-postgres-password>
DB_PORT=5432
```

#### Redis Variables (from Step 3)

```
REDIS_URL=<your-redis-internal-url>/1
USE_REDIS=True
CELERY_BROKER_URL=<your-redis-internal-url>/0
CELERY_RESULT_BACKEND=<your-redis-internal-url>/0
```

#### Optional Variables

```
SENTRY_DSN=<your-sentry-dsn-if-using>
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@academy.edu.ge
```

**Note:** Replace `<your-redis-internal-url>` with the Internal Redis URL from Step 3, and append `/0` or `/1` for different Redis databases.

4. Click **"Create Web Service"**

## Step 5: Create Background Worker (Celery Worker)

1. Click **"New +"** → **"Background Worker"**
2. Select the same GitHub repository
3. Configure:
   - **Name:** `academy-crm-worker`
   - **Environment:** `Docker`
   - **Region:** Oregon (US West)
   - **Branch:** `main`
   - **Root Directory:** (leave empty)
   - **Start Command:** `celery -A academy_crm worker -l info --concurrency=4`
   - **Instance Type:** Starter ($7/month)

### Environment Variables for Worker

Use the same environment variables as the API service, **except**:
- Remove `CORS_ALLOWED_ORIGINS` (not needed for workers)
- Keep all database, Redis, and Celery variables

4. Click **"Create Background Worker"**

## Step 6: Create Background Worker (Celery Beat)

1. Click **"New +"** → **"Background Worker"**
2. Select the same GitHub repository
3. Configure:
   - **Name:** `academy-crm-beat`
   - **Environment:** `Docker`
   - **Region:** Oregon (US West)
   - **Branch:** `main`
   - **Root Directory:** (leave empty)
   - **Start Command:** `celery -A academy_crm beat -l info`
   - **Instance Type:** Starter ($7/month)

### Environment Variables for Beat

Use the same environment variables as the Worker service.

4. Click **"Create Background Worker"**

## Step 7: Generate Secret Key

Generate a secure secret key for Django:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Or use an online generator. Add this to the `SECRET_KEY` environment variable in all services.

## Step 8: Deploy and Verify

1. **Initial Deployment:**
   - Render will automatically build and deploy when you create services
   - Monitor the build logs for any errors
   - Wait for all services to show "Live" status

2. **Run Migrations:**
   - Go to your API service in Render dashboard
   - Click on **"Shell"** tab
   - Run: `python manage.py migrate`
   - Or migrations will run automatically if using the entrypoint script

3. **Create Superuser:**
   - In the API service Shell, run:
   ```bash
   python manage.py createsuperuser
   ```
   - Follow the prompts to create an admin user

4. **Verify Health Check:**
   - Visit: `https://academy-crm-api.onrender.com/health/`
   - Should return a 200 OK response

5. **Test API Endpoints:**
   - Visit: `https://academy-crm-api.onrender.com/api/docs/`
   - Test authentication endpoints
   - Verify database connectivity

6. **Verify Background Workers:**
   - Check worker logs for: "celery@hostname ready"
   - Check beat logs for: "beat: Starting..."

## Step 9: Configure Custom Domain (Optional)

1. In your API service settings, go to **"Custom Domains"**
2. Add your domain
3. Update `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` to include your domain
4. Follow DNS configuration instructions

## Environment Variables Checklist

Use this checklist to ensure all services have the correct variables:

### All Services (API, Worker, Beat)

- [ ] `DJANGO_ENV=prod`
- [ ] `SECRET_KEY=<secure-key>`
- [ ] `DB_HOST=<postgres-host>`
- [ ] `DB_NAME=academy_crm`
- [ ] `DB_USER=<postgres-user>`
- [ ] `DB_PASSWORD=<postgres-password>`
- [ ] `DB_PORT=5432`
- [ ] `REDIS_URL=<redis-url>/1`
- [ ] `USE_REDIS=True`
- [ ] `CELERY_BROKER_URL=<redis-url>/0`
- [ ] `CELERY_RESULT_BACKEND=<redis-url>/0`

### API Service Only

- [ ] `ALLOWED_HOSTS=<comma-separated-hosts>`
- [ ] `CORS_ALLOWED_ORIGINS=<comma-separated-origins>`

### Optional (All Services)

- [ ] `SENTRY_DSN=<sentry-dsn>`
- [ ] `EMAIL_HOST=smtp.gmail.com`
- [ ] `EMAIL_PORT=587`
- [ ] `EMAIL_HOST_USER=<email>`
- [ ] `EMAIL_HOST_PASSWORD=<app-password>`
- [ ] `DEFAULT_FROM_EMAIL=<from-email>`

## Troubleshooting

### Build Fails

- Check Dockerfile syntax
- Verify all requirements are in `requirements/prod.txt`
- Check build logs for specific errors

### Database Connection Errors

- Verify database credentials are correct
- Ensure database is in the same region
- Check that `DB_HOST` uses the internal hostname (not external)
- Verify database is running and accessible

### Static Files Not Loading

- Verify `collectstatic` ran during build
- Check `STATIC_ROOT` path in settings
- Ensure static files are collected: `python manage.py collectstatic`

### Celery Worker Not Processing Tasks

- Verify Redis connection
- Check `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND`
- Ensure worker service is running
- Check worker logs for errors

### Health Check Failing

- Verify `/health/` endpoint is accessible
- Check database connectivity
- Ensure all required services are running

### CORS Errors

- Verify `CORS_ALLOWED_ORIGINS` includes your frontend URL
- Check that frontend is using the correct API URL
- Ensure credentials are handled correctly

## Cost Estimate

Monthly costs on Render.com (Starter plans):

- PostgreSQL Database: $7/month
- Redis: $10/month
- Web Service (API): $7/month
- Background Worker: $7/month
- Background Worker (Beat): $7/month
- **Total: ~$38/month**

For production with higher traffic, consider Standard plans ($25/month each).

## Monitoring and Maintenance

1. **Monitor Logs:**
   - Regularly check service logs in Render dashboard
   - Set up alerts for errors

2. **Database Backups:**
   - Render provides automatic backups for PostgreSQL
   - Configure backup retention in database settings

3. **Scaling:**
   - Monitor resource usage
   - Scale services up if needed
   - Consider auto-scaling for high traffic

4. **Updates:**
   - Push changes to `main` branch for auto-deploy
   - Test in staging environment first
   - Monitor deployment logs

## Security Best Practices

1. **Never commit secrets:**
   - Use Render environment variables
   - Keep `.env` files out of repository

2. **Use strong SECRET_KEY:**
   - Generate a new one for production
   - Never reuse development keys

3. **Enable HTTPS:**
   - Render provides SSL automatically
   - Ensure `SECURE_SSL_REDIRECT=True` in production

4. **Restrict CORS:**
   - Only allow your frontend domains
   - Never use `*` in production

5. **Database Security:**
   - Use strong passwords
   - Restrict database access to internal network only

## Support

For issues specific to:
- **Render.com:** Check [Render Documentation](https://render.com/docs)
- **Django:** Check [Django Documentation](https://docs.djangoproject.com)
- **Celery:** Check [Celery Documentation](https://docs.celeryproject.org)

## Next Steps

After successful deployment:
1. Set up monitoring (Sentry, etc.)
2. Configure email notifications
3. Set up CI/CD pipeline
4. Plan for scaling as your SaaS grows
5. Implement subscription/payment system

