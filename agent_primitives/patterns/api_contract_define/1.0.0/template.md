---
name: "Define API Contract"
description: "Define a detailed API contract between the backend and frontend for a given feature, including RESTful endpoints and DTOs."
arguments: "$ARGUMENTS"
keywords:
  - api
  - contract
  - rest
  - dto
  - backend
  - frontend
---

# Define API Contract Between Backend and Frontend

Feature: $ARGUMENTS

## Task: Create detailed API contract specification for backend/frontend coordination

1. **Define RESTful endpoints**:

   ```yaml
   Base URL: /api/v1/{feature}

   Endpoints:
   - GET /api/v1/{features}
     Query params: page, size, sort, filter
     Response: Page<{Feature}Response>

   - GET /api/v1/{features}/{id}
     Path param: id (Long)
     Response: {Feature}Response

   - POST /api/v1/{features}
     Body: {Feature}Request
     Response: {Feature}Response (201 Created)

   - PUT /api/v1/{features}/{id}
     Path param: id (Long)
     Body: {Feature}Request
     Response: {Feature}Response

   - DELETE /api/v1/{features}/{id}
     Path param: id (Long)
     Response: 204 No Content
   ```

2. **Define request/response DTOs**:

   ```typescript
   // Request DTO (for POST/PUT)
   interface {Feature}Request {
     name: string;        // min: 2, max: 100
     description?: string; // max: 1000
     // Add domain-specific fields
   }

   // Response DTO (for GET)
   interface {Feature}Response {
     id: number;
     // Add domain-specific fields
   }
   ```

3. **Define error cases and status codes**:

   - 400 Bad Request: Invalid input
   - 401 Unauthorized: Not authenticated
   - 403 Forbidden: Not authorized
   - 404 Not Found: Resource missing
   - 500 Internal Server Error: Unexpected failure

---

_This template is intended for use in the PRP v2.0 pattern system._
