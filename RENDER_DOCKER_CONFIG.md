# Render.com Docker Configuration Guide

## Docker Configuration Fields

### ✅ Current Configuration (Correct)

1. **Registry Credential**
   - **Value:** `No credential`
   - **Why:** You're building from source code, not pulling from a private registry
   - ✅ **Correct - Leave as is**

2. **Dockerfile Path**
   - **Value:** `./Dockerfile`
   - **Why:** Your Dockerfile is in the root directory
   - ✅ **Correct - Leave as is**

3. **Docker Build Context Directory**
   - **Value:** `.` (dot = root directory)
   - **Why:** All your files (Dockerfile, requirements, code) are in the repo root
   - ✅ **Correct - Leave as is**

4. **Docker Command**
   - **Value:** (Empty/Blank)
   - **Why:** Your Dockerfile already has `CMD` and `ENTRYPOINT` set correctly
   - ✅ **Correct - Leave empty**
   - The Dockerfile uses:
     - `ENTRYPOINT ["/app/scripts/entrypoint.sh"]` - Runs migrations, collects static files
     - `CMD gunicorn ...` - Starts the web server

5. **Pre-Deploy Command**
   - **Value:** (Empty/Blank)
   - **Why:** Migrations are handled by `entrypoint.sh` script (controlled by `AUTO_MIGRATE` env var)
   - ✅ **Correct - Leave empty**
   - **Optional:** If you want to run migrations BEFORE the container starts, you could add:
     ```
     python manage.py migrate --noinput
     ```
     But this is NOT recommended since `entrypoint.sh` already handles it.

6. **Auto-Deploy**
   - **Value:** `On Commit` (enabled)
   - **Why:** Automatically deploys when you push to your repository
   - ✅ **Correct - Leave enabled**

## Summary

**All fields are configured correctly!** ✅

Your setup:
- ✅ Builds from source code (no registry needed)
- ✅ Uses Dockerfile in root directory
- ✅ Build context is root directory
- ✅ Uses Dockerfile's CMD/ENTRYPOINT (no override needed)
- ✅ Migrations handled by entrypoint.sh (no pre-deploy needed)
- ✅ Auto-deploys on git push

## What Happens on Deploy

1. Render pulls your code from Git
2. Builds Docker image using `./Dockerfile`
3. Runs container with `entrypoint.sh` which:
   - Waits for database
   - Runs migrations (if `AUTO_MIGRATE=true`)
   - Collects static files
   - Starts Gunicorn server

## Environment Variables Needed

Make sure these are set in **Environment** tab:

- `DB_HOST` - Database hostname (just hostname, no URL!)
- `DB_NAME` - Database name
- `DB_USER` - Database user
- `DB_PASSWORD` - Database password
- `DB_PORT` - Database port (usually `5432`)
- `AUTO_MIGRATE` - Set to `true` to enable auto-migrations
- `SECRET_KEY` - Django secret key
- `DJANGO_SETTINGS_MODULE` - Should be `academy_crm.settings.prod` (or auto-detected)
- `PORT` - Automatically set by Render (don't set manually)

## No Changes Needed!

Your Docker configuration is perfect. Just make sure:
1. ✅ Environment variables are set correctly (especially `DB_HOST`)
2. ✅ Database connection is working
3. ✅ `AUTO_MIGRATE=true` if you want automatic migrations

