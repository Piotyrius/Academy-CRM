# Academy CRM - Architecture & Docker Setup

## Current Architecture: Monolithic Django Application

### ✅ Swagger API Documentation Status

**All endpoints are visible and documented!** The Swagger UI shows:

- ✅ **Authentication** (2 endpoints) - Login, Token Refresh
- ✅ **Users** (7 endpoints) - User management, profile
- ✅ **Catalog** (15 endpoints) - Programs, Courses, Cohorts, Sessions
- ✅ **Admissions** (12 endpoints) - Applications, Enrollments
- ✅ **Attendance** (6 endpoints) - Attendance tracking, bulk operations
- ✅ **Assessment** (12 endpoints) - Assessments, Grades, Submissions
- ✅ **Certificates** (7 endpoints) - Certificate management, verification
- ✅ **Documents** (5 endpoints) - Document management
- ✅ **Timekeeping** (10 endpoints) - Timesheets, Worklogs, Rates, Payroll
- ✅ **Gallery** (5 endpoints) - Gallery works management
- ✅ **Reporting** (5 endpoints) - Reports and exports
- ✅ **Me** (5 endpoints) - Student portal endpoints

**Total: 91 API endpoints** - All documented and accessible via Swagger!

## Docker Architecture

### Current Setup: Monolithic (Single Container)

**Current deployment:**
- **1 Docker container** running all Django apps together
- **1 Web Service** on Render.com
- All apps share the same:
  - Database connection
  - Static files
  - Media files
  - Environment variables

**Dockerfile:**
- Multi-stage build (optimized)
- Runs Gunicorn with 4 workers
- Handles migrations automatically
- Serves static files with WhiteNoise

**Services (in docker-compose.prod.yml for reference):**
1. **api** - Main Django application (Gunicorn)
2. **worker** - Celery worker for async tasks (optional)
3. **beat** - Celery beat for scheduled tasks (optional)

### Why Monolithic?

✅ **Pros:**
- Simple deployment
- Easy to develop and test
- Shared database (no data consistency issues)
- Lower resource usage
- Faster development

❌ **Cons:**
- All apps scale together (can't scale individual apps)
- Single point of failure
- Harder to deploy updates to specific apps

## Django Apps Structure

All apps are Django modules within the same project:

```
academy_crm/
├── accounts/          # User management, authentication
├── catalog/           # Programs, courses, cohorts, sessions
├── admissions/        # Applications, enrollments
├── attendance/        # Attendance tracking
├── assessment/        # Assessments, grades, submissions
├── certificates/      # Certificate generation and management
├── documents/         # Document management
├── notifications/     # Notification system
├── reporting/         # Reports and exports
├── ops/              # Operations
├── timekeeping/       # Timesheets, worklogs, payroll
└── gallery/          # Gallery works
```

## When to Move to Microservices?

Consider splitting into separate containers/services when:

1. **Scale Requirements:**
   - One app needs more resources than others
   - Different apps have different traffic patterns
   - Need to scale apps independently

2. **Team Size:**
   - Multiple teams working on different apps
   - Need independent deployment cycles

3. **Technology Requirements:**
   - Different apps need different Python versions
   - Some apps need different dependencies

4. **Performance:**
   - One app is causing performance issues for others
   - Need to isolate resource-intensive operations

## Migration Path to Microservices (If Needed)

If you need to split into separate containers later:

### Option 1: Separate Docker Containers (Same Codebase)
- Keep same codebase
- Create separate Dockerfiles for each app
- Use shared database
- Deploy as separate services on Render

### Option 2: True Microservices
- Split into separate repositories
- Each service has its own database (or shared)
- Use API Gateway
- More complex but more scalable

### Option 3: Hybrid Approach
- Keep core apps together (monolith)
- Extract heavy/complex apps (e.g., reporting, timekeeping)
- Gradual migration

## Current Docker Setup - Production Ready ✅

### What's Working:
- ✅ Multi-stage Docker build (optimized)
- ✅ Non-root user (security)
- ✅ Health checks configured
- ✅ Automatic migrations
- ✅ Static file serving (WhiteNoise)
- ✅ Environment variable configuration
- ✅ Gunicorn with multiple workers
- ✅ Production-ready settings

### Render.com Deployment:
- ✅ Single Web Service container
- ✅ PostgreSQL database (separate service)
- ✅ Redis (optional, for cache/Celery)
- ✅ Auto-deploy on git push
- ✅ Health check endpoint working

## Recommendations

### For Current Scale (Small to Medium):
✅ **Keep monolithic architecture** - It's working well and is simpler to maintain.

### If You Need to Scale:
1. **First:** Add more Gunicorn workers (increase `--workers` in Dockerfile)
2. **Second:** Add Redis for caching (already configured)
3. **Third:** Add Celery workers for async tasks (already configured)
4. **Fourth:** Consider splitting only if specific apps need independent scaling

### Future Considerations:
- Monitor which apps use most resources
- If one app (e.g., reporting) needs more resources, consider extracting it
- Keep related apps together (e.g., admissions + enrollments)

## Summary

**Current Status:**
- ✅ Swagger shows all 91 API endpoints
- ✅ Docker setup is production-ready
- ✅ Monolithic architecture (all apps in one container)
- ✅ Suitable for current scale
- ✅ Easy to migrate to microservices later if needed

**Your setup is solid!** The monolithic approach is perfect for your current needs. You can always split into microservices later if you need independent scaling.

