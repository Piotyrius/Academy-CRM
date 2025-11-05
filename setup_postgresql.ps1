# PostgreSQL Setup Script for Windows
# This script helps set up PostgreSQL for the Academy CRM project

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Academy CRM - PostgreSQL Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is available
$dockerAvailable = Get-Command docker -ErrorAction SilentlyContinue

if ($dockerAvailable) {
    Write-Host "✅ Docker detected" -ForegroundColor Green
    Write-Host ""
    Write-Host "Option 1: Use Docker Compose (Recommended)" -ForegroundColor Yellow
    Write-Host "  Run: docker-compose up -d db redis" -ForegroundColor White
    Write-Host ""
    $useDocker = Read-Host "Use Docker Compose? (Y/n)"
    
    if ($useDocker -eq '' -or $useDocker -eq 'Y' -or $useDocker -eq 'y') {
        Write-Host ""
        Write-Host "Starting PostgreSQL and Redis with Docker..." -ForegroundColor Yellow
        docker-compose up -d db redis
        
        Write-Host ""
        Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        
        Write-Host ""
        Write-Host "✅ PostgreSQL should now be running!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "  1. Update .env file (if needed):" -ForegroundColor White
        Write-Host "     DB_NAME=academy_crm" -ForegroundColor Gray
        Write-Host "     DB_USER=postgres" -ForegroundColor Gray
        Write-Host "     DB_PASSWORD=postgres" -ForegroundColor Gray
        Write-Host "     DB_HOST=localhost" -ForegroundColor Gray
        Write-Host "     DB_PORT=5432" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  2. Run migrations:" -ForegroundColor White
        Write-Host "     python manage.py migrate" -ForegroundColor Gray
        Write-Host ""
        Write-Host "  3. Create superuser:" -ForegroundColor White
        Write-Host "     python manage.py createsuperuser" -ForegroundColor Gray
        Write-Host ""
        exit
    }
}

# Check if PostgreSQL is installed locally
Write-Host ""
Write-Host "Option 2: Local PostgreSQL Installation" -ForegroundColor Yellow
$pgInstalled = Get-Command psql -ErrorAction SilentlyContinue

if ($pgInstalled) {
    Write-Host "✅ PostgreSQL (psql) detected" -ForegroundColor Green
    Write-Host ""
    Write-Host "Please ensure:" -ForegroundColor Yellow
    Write-Host "  1. PostgreSQL service is running" -ForegroundColor White
    Write-Host "  2. Database 'academy_crm' exists" -ForegroundColor White
    Write-Host "  3. .env file has correct credentials" -ForegroundColor White
    Write-Host ""
    Write-Host "To create database, run:" -ForegroundColor Cyan
    Write-Host "  psql -U postgres -c 'CREATE DATABASE academy_crm;'" -ForegroundColor Gray
    Write-Host ""
} else {
    Write-Host "❌ PostgreSQL not found locally" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install options:" -ForegroundColor Yellow
    Write-Host "  1. Download from: https://www.postgresql.org/download/windows/" -ForegroundColor White
    Write-Host "  2. Use Chocolatey: choco install postgresql" -ForegroundColor White
    Write-Host "  3. Use Docker Compose (recommended - see above)" -ForegroundColor White
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "For detailed instructions, see:" -ForegroundColor Cyan
Write-Host "  DATABASE_SETUP.md" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
