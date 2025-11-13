# Academy CRM - Backend-Only Deployment Guide for Render.com

This guide provides step-by-step instructions for deploying **only the backend API + PostgreSQL** to Render.com using Docker. No frontend, Redis, or Celery workers needed.

## Prerequisites

- Render.com account
- GitHub repository with your code
- Basic understanding of Docker and Django

## Overview

For backend-only deployment, you only need:
1. **PostgreSQL Database** - Main database
2. **Web Service (API)** - Django REST API

**Optional (can add later):**
- Redis (for caching and Celery)
- Celery Worker (for background tasks)
- Celery Beat (for scheduled tasks)

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
   - **User:** (leave empty - auto-generated)
   - **Region:** **Match your Web Service region** (e.g., Frankfurt, Oregon)
   - **PostgreSQL Version:** `15` (recommended)
   - **Plan:** `Basic-256mb` ($6/month) for testing, or `Basic-1gb` ($19/month) for production
   - **Storage:** `1 GB` for testing, `15 GB` for production
4. Click **"Create Database"**
5. **Important:** Save these connection details:
   - **Internal Database URL** (starts with `postgresql://`)
   - **Internal Host** (e.g., `dpg-xxxxx-a.frankfurt-postgres.render.com`)
   - **Port:** `5432`
   - **Database:** `academy_crm`
   - **User:** (from connection details)
   - **Password:** (from connection details - save this securely!)

## Step 3: Create Web Service (API)

1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:

### Basic Settings:
   - **Name:** `academy-crm-api`
   - **Environment:** `Docker` ⚠️ (NOT Python 3)
   - **Region:** **Same as your PostgreSQL database**
   - **Branch:** `main`
   - **Root Directory:** (leave empty)
   - **Build Command:** (leave empty - Docker handles it)
   - **Start Command:** (leave empty - Dockerfile CMD is used)
   - **Instance Type:** `Starter` ($7/month) or `Standard` ($25/month)

### Advanced Settings:
   - **Health Check Path:** `/health/`
   - **Docker Build Context Directory:** `.`
   - **Dockerfile Path:** `./Dockerfile`
   - **Docker Command:** (leave empty)
   - **Pre-Deploy Command:** (leave empty - run migrations manually)
   - **Auto-Deploy:** `On Commit` (enabled)

### Environment Variables:

Add these environment variables one by one:

#### Required Core Variables:

1. **DJANGO_ENV**
   ```
   Key: DJANGO_ENV
   Value: prod
   ```

2. **SECRET_KEY**
   ```
   Key: SECRET_KEY
   Value: [Generate a secure key - see below]
   ```
   Generate secret key:
   ```bash
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
   Or use: https://djecrety.ir/

3. **ALLOWED_HOSTS**
   ```
   Key: ALLOWED_HOSTS
   Value: academy-crm-api.onrender.com
   ```
   ⚠️ Replace `academy-crm-api` with your actual service name from Render

#### Database Variables (from Step 2):

4. **DB_HOST**
   ```
   Key: DB_HOST
   Value: [Your PostgreSQL Internal Host]
   ```
   Example: `dpg-xxxxx-a.frankfurt-postgres.render.com`

5. **DB_NAME**
   ```
   Key: DB_NAME
   Value: academy_crm
   ```

6. **DB_USER**
   ```
   Key: DB_USER
   Value: [Your PostgreSQL User]
   ```

7. **DB_PASSWORD**
   ```
   Key: DB_PASSWORD
   Value: [Your PostgreSQL Password]
   ```

8. **DB_PORT**
   ```
   Key: DB_PORT
   Value: 5432
   ```

#### Optional Variables (can skip for now):

- **CORS_ALLOWED_ORIGINS** - Leave empty (backend allows all origins for testing)
- **REDIS_URL** - Not needed for backend-only
- **USE_REDIS** - Not needed for backend-only
- **CELERY_BROKER_URL** - Not needed for backend-only
- **CELERY_RESULT_BACKEND** - Not needed for backend-only

4. Click **"Create Web Service"**

## Step 4: Deploy and Verify

1. **Monitor Build:**
   - Render will automatically build your Docker image
   - Watch the build logs for any errors
   - Build takes 3-5 minutes

2. **Wait for "Live" Status:**
   - Once build completes, service will start
   - Wait for status to show "Live"

3. **Run Migrations:**
   - Go to your Web Service → **"Shell"** tab
   - Run: `python manage.py migrate`
   - You should see migrations being applied

4. **Create Superuser (Optional):**
   - In Shell, run: `python manage.py createsuperuser`
   - Follow prompts to create admin user

5. **Verify Health Check:**
   - Visit: `https://academy-crm-api.onrender.com/health/`
   - Should return: `{"status": "healthy"}` or similar

6. **Test API:**
   - Visit: `https://academy-crm-api.onrender.com/api/docs/`
   - You should see the Swagger/OpenAPI documentation
   - Test authentication endpoints

## Step 5: Test Your API

### Using curl:
```bash
# Health check
curl https://academy-crm-api.onrender.com/health/

# API docs
curl https://academy-crm-api.onrender.com/api/docs/
```

### Using Browser:
- Visit: `https://academy-crm-api.onrender.com/api/docs/`
- You can test API endpoints directly from the Swagger UI

## Environment Variables Checklist

Use this checklist to ensure all required variables are set:

### Required:
- [ ] `DJANGO_ENV=prod`
- [ ] `SECRET_KEY=<secure-random-key>`
- [ ] `ALLOWED_HOSTS=academy-crm-api.onrender.com` (your actual service name)
- [ ] `DB_HOST=<postgres-internal-host>`
- [ ] `DB_NAME=academy_crm`
- [ ] `DB_USER=<postgres-user>`
- [ ] `DB_PASSWORD=<postgres-password>`
- [ ] `DB_PORT=5432`

### Optional (can add later):
- [ ] `CORS_ALLOWED_ORIGINS` - Leave empty for now
- [ ] `REDIS_URL` - Not needed
- [ ] `USE_REDIS` - Not needed
- [ ] `CELERY_BROKER_URL` - Not needed
- [ ] `CELERY_RESULT_BACKEND` - Not needed

## Troubleshooting

### Build Fails
- Check Dockerfile syntax
- Verify all requirements are in `requirements/prod.txt`
- Check build logs for specific errors

### Database Connection Errors
- Verify database credentials are correct
- Ensure database is in the **same region** as Web Service
- Check that `DB_HOST` uses the **Internal Host** (not external)
- Verify database is running

### Health Check Fails
- Check `ALLOWED_HOSTS` includes your Render service URL
- Verify service is running (check logs)
- Ensure `/health/` endpoint is accessible

### CORS Errors (when testing from browser)
- CORS is currently set to allow all origins for backend-only deployment
- This is fine for API testing
- You can restrict it later when you add a frontend

## Cost Estimate

Monthly costs for backend-only setup:

- **PostgreSQL Database:** $6-19/month (Basic-256mb or Basic-1gb)
- **Web Service (API):** $7-25/month (Starter or Standard)
- **Total: ~$13-44/month**

## Next Steps

Once your backend is working:

1. **Add Redis** (if you need caching or Celery):
   - Create Redis service on Render
   - Add Redis environment variables

2. **Add Celery Workers** (if you need background tasks):
   - Create Background Worker services
   - Configure Celery environment variables

3. **Add Frontend** (when ready):
   - Deploy your frontend
   - Update `CORS_ALLOWED_ORIGINS` with your frontend URL
   - Set `CORS_ALLOW_ALL_ORIGINS = False` in production settings

4. **Restrict CORS** (when frontend is added):
   - Update `CORS_ALLOWED_ORIGINS` environment variable
   - The code will automatically restrict CORS when origins are specified

## Security Notes

- **CORS:** Currently allows all origins for backend-only deployment. Restrict this when you add a frontend.
- **SECRET_KEY:** Must be a secure random key - never commit it to git
- **Database:** Uses Render's internal network for security
- **HTTPS:** Render provides SSL automatically

## Support

For issues:
- **Render.com:** Check [Render Documentation](https://render.com/docs)
- **Django:** Check [Django Documentation](https://docs.djangoproject.com)

