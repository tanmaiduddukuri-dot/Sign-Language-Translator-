# SignEase Backend

Production-ready FastAPI + MongoDB backend for the SignEase frontend.

## Features
- User registration and login with hashed passwords
- JWT authentication
- User profile management
- Sign dictionary CRUD
- Translation history CRUD
- Favorites CRUD
- Learning progress
- Feedback
- Admin statistics and management endpoints
- Automatic MongoDB indexes
- Automatic seed data for the 15 signs used by the frontend

## Local setup

1. Create a MongoDB database. For local Compass:
   `mongodb://localhost:27017`

2. Copy `.env.example` to `.env` and update values.

3. Install:
   `pip install -r requirements.txt`

4. Run:
   `uvicorn app.main:app --reload`

5. Open:
   `http://127.0.0.1:8000/docs`

## Deploy

### Render
Push this folder to GitHub, create a new Web Service in Render, and either:
- let Render detect `render.yaml`, or
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

Set environment variables:
- `MONGODB_URL` = your MongoDB Atlas connection string
- `DATABASE_NAME` = `signeaseDB`
- `JWT_SECRET` = long random secret
- `CORS_ORIGINS` = your deployed frontend URL, comma-separated if multiple
- `ADMIN_PASSWORD` = a strong password

## Important
MongoDB Compass is useful for local development. A deployed backend needs a reachable MongoDB instance, typically MongoDB Atlas. Do not expose a local `localhost:27017` database to the public internet.
