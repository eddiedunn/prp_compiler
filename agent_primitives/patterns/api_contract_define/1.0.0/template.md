# API Contract Definition Pattern

## 1. Overview

- **API Name:** A clear, descriptive name for the API.
- **Version:** The current version of the contract (e.g., v1, v2).
- **Description:** A brief summary of the API's purpose and what it provides.
- **Owner/Team:** The team responsible for maintaining the API.

## 2. Authentication

- **Method:** Describe the authentication mechanism (e.g., OAuth 2.0, API Key, JWT).
- **Required Headers/Parameters:** Specify headers like `Authorization`.
- **Token Endpoint (if applicable):** The URL to obtain an access token.

## 3. Endpoints

For each endpoint, provide the following details:

### `[HTTP_METHOD] /[resource_path]`

- **Description:** What does this endpoint do? What is its business purpose?
- **Request:**
    - **URL Parameters:** (e.g., `/users/{userId}`)
        - `userId` (string, required): The unique identifier for the user.
    - **Query Parameters:**
        - `sort` (string, optional): The field to sort by. Defaults to `createdAt`.
    - **Headers:**
        - `Content-Type`: `application/json`
    - **Request Body (DTO - Data Transfer Object):**
        ```json
        {
          "name": "string",
          "email": "string (email format)"
        }
        ```
- **Success Response (2xx):**
    - **Status Code:** `200 OK` or `201 Created`
    - **Response Body:**
        ```json
        {
          "id": "string (uuid)",
          "name": "string",
          "email": "string (email format)",
          "createdAt": "string (ISO 8601 datetime)"
        }
        ```
- **Error Responses (4xx/5xx):**
    - **Status Code:** `400 Bad Request`
        - **Reason:** Invalid input format.
        - **Response Body:**
            ```json
            {
              "error": "InvalidEmail",
              "message": "The provided email address is not valid."
            }
            ```
    - **Status Code:** `404 Not Found`
        - **Reason:** The requested resource does not exist.
        - **Response Body:**
            ```json
            {
              "error": "NotFound",
              "message": "User with the specified ID was not found."
            }
            ```

## 4. Data Models (DTOs)

Define any complex objects used in requests or responses.

- **User:**
    - `id` (string, uuid): Unique identifier.
    - `name` (string): User's full name.
    - `email` (string, email): User's email address.

## 5. Rate Limiting

- **Limit:** Specify the number of requests allowed per time window (e.g., 100 requests per minute).
- **Headers:** Describe response headers that provide rate limit status (e.g., `X-RateLimit-Limit`, `X-RateLimit-Remaining`).
