# Academy CRM - Setup Script for New PC
# Run this script on a new PC to set up the project

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Academy CRM - New PC Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Python not found! Please install Python 3.11+" -ForegroundColor Red
    exit 1
}
Write-Host "Found: $pythonVersion" -ForegroundColor Green

# Check if venv exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "Virtual environment created!" -ForegroundColor Green
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Green
}

# Activate venv
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
if (Test-Path "requirements/base.txt") {
    pip install -r requirements/base.txt
    Write-Host "Dependencies installed!" -ForegroundColor Green
} else {
    Write-Host "WARNING: requirements/base.txt not found!" -ForegroundColor Red
}

# Check .env file
Write-Host ""
Write-Host "Checking .env file..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "WARNING: .env file not found!" -ForegroundColor Red
    if (Test-Path ".env.example") {
        Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
        Copy-Item .env.example .env
        Write-Host ".env file created from template." -ForegroundColor Green
        Write-Host "IMPORTANT: Please update .env with your database password!" -ForegroundColor Red
    } else {
        Write-Host "ERROR: .env.example not found! Please create .env manually." -ForegroundColor Red
    }
} else {
    Write-Host ".env file exists." -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Install PostgreSQL 15+ (if not installed)" -ForegroundColor White
Write-Host "2. Create database 'academy_crm' in PostgreSQL" -ForegroundColor White
Write-Host "3. Set password for postgres user (if not set)" -ForegroundColor White
Write-Host "4. Update .env file with database password" -ForegroundColor White
Write-Host "5. Run: python manage.py migrate" -ForegroundColor White
Write-Host "6. Run: python manage.py createsuperuser" -ForegroundColor White
Write-Host "7. Run: python manage.py runserver" -ForegroundColor White
Write-Host ""
Write-Host "For detailed instructions, see DEPLOYMENT_GUIDE.md" -ForegroundColor Cyan
