# API Documentation for Frontend Developers

## Swagger UI (Interactive API Documentation)

**URL:** `https://academy-crm.onrender.com/api/docs/`

- Browse all available API endpoints
- See request/response schemas
- Test endpoints directly in the browser
- No authentication required to view documentation

## ReDoc (Alternative Documentation View)

**URL:** `https://academy-crm.onrender.com/api/docs/redoc/`

- Clean, readable API documentation
- Better for reading and understanding the API
- No authentication required

## OpenAPI Schema (JSON)

**URL:** `https://academy-crm.onrender.com/api/schema/`

- Raw OpenAPI 3.0 schema in JSON format
- Can be imported into Postman, Insomnia, or other API tools
- No authentication required

## Authentication

While the documentation is publicly accessible, **API endpoints require authentication**.

### How to Authenticate

1. **Get JWT Token:**
   - POST to `/api/v1/auth/login/` (or your login endpoint)
   - Receive access token and refresh token

2. **Use Token in Requests:**
   - Add header: `Authorization: Bearer <your-access-token>`
   - Token expires after 1 hour (use refresh token to get new one)

3. **In Swagger UI:**
   - Click "Authorize" button (top right)
   - Enter: `Bearer <your-token>`
   - Now you can test authenticated endpoints

## Quick Start

1. Open Swagger: `https://academy-crm.onrender.com/api/docs/`
2. Explore available endpoints
3. Test authentication endpoints first
4. Use the token to test other endpoints

## Notes

- All documentation endpoints are publicly accessible (no login needed)
- API endpoints require JWT authentication
- Swagger UI has "Try it out" feature for testing
- Schema is automatically generated from your Django code

