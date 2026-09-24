import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "signeaseDB")
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_THIS_IN_PRODUCTION")
JWT_ALGORITHM = "HS256"
TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@signease.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")
origins = [x.strip() for x in os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5500,http://localhost:5500"
).split(",") if x.strip()]

app = FastAPI(title="SignEase API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer()

SIGNS = [
    {"name":"Hello","meaning":"Hello","category":"Greetings","icon":"👋"},
    {"name":"Thank You","meaning":"Thank you","category":"Greetings","icon":"🙏"},
    {"name":"Please","meaning":"Please","category":"Common Words","icon":"🤲"},
    {"name":"Sorry","meaning":"Sorry","category":"Common Words","icon":"🙇"},
    {"name":"Yes","meaning":"Yes","category":"Common Words","icon":"👍"},
    {"name":"No","meaning":"No","category":"Common Words","icon":"👎"},
    {"name":"Help","meaning":"Help","category":"Emergency","icon":"🆘"},
    {"name":"Good Morning","meaning":"Good morning","category":"Greetings","icon":"🌅"},
    {"name":"Good Night","meaning":"Good night","category":"Greetings","icon":"🌙"},
    {"name":"I Love You","meaning":"I love you","category":"Emotions","icon":"❤️"},
    {"name":"Welcome","meaning":"Welcome","category":"Greetings","icon":"🤝"},
    {"name":"Friend","meaning":"Friend","category":"Daily Communication","icon":"🧑‍🤝‍🧑"},
    {"name":"Family","meaning":"Family","category":"Daily Communication","icon":"👨‍👩‍👧"},
    {"name":"Water","meaning":"Water","category":"Daily Communication","icon":"💧"},
    {"name":"Food","meaning":"Food","category":"Daily Communication","icon":"🍴"},
]

def now():
    return datetime.now(timezone.utc)

def public_user(user):
    return {
        "id": str(user["_id"]),
        "name": user.get("name"),
        "email": user.get("email"),
        "phone": user.get("phone", ""),
        "language": user.get("language", "English"),
        "role": user.get("role", "user"),
        "status": user.get("status", "Active"),
        "createdAt": user.get("createdAt"),
    }

def serialize(doc):
    if doc is None:
        return None
    out = dict(doc)
    out["id"] = str(out.pop("_id"))
    return out

def create_token(user_id: str, role: str):
    exp = now() + timedelta(minutes=TOKEN_MINUTES)
    return jwt.encode({"sub": user_id, "role": role, "exp": exp}, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        from bson import ObjectId
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

async def admin_user(user=Depends(current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = ""
    language: str = "English"
    password: str = Field(min_length=6, max_length=128)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class ProfileIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = ""
    language: str = "English"

class SignIn(BaseModel):
    name: str
    meaning: str
    category: str
    icon: str = "🤟"

class TranslationIn(BaseModel):
    sign: str
    translation: str
    input: str = "Camera/Demo"

class FavoriteIn(BaseModel):
    signName: str

class ProgressIn(BaseModel):
    course: str = "Basic Greetings"
    progress: int = Field(ge=0, le=100)

class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    type: str
    message: str = Field(min_length=1, max_length=2000)

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.signs.create_index("name", unique=True)
    await db.translations.create_index([("userId", 1), ("createdAt", -1)])
    await db.favorites.create_index([("userId", 1), ("signName", 1)], unique=True)
    await db.feedback.create_index([("createdAt", -1)])
    if await db.signs.count_documents({}) == 0:
        await db.signs.insert_many([{**s, "createdAt": now()} for s in SIGNS])
    admin = await db.users.find_one({"email": ADMIN_EMAIL.lower()})
    if not admin:
        await db.users.insert_one({
            "name": "SignEase Admin",
            "email": ADMIN_EMAIL.lower(),
            "phone": "",
            "language": "English",
            "passwordHash": pwd_context.hash(ADMIN_PASSWORD),
            "role": "admin",
            "status": "Active",
            "createdAt": now()
        })

@app.get("/")
async def root():
    return {"message": "SignEase API is running", "database": DATABASE_NAME}

@app.get("/health")
async def health():
    await db.command("ping")
    return {"status": "ok"}

@app.post("/auth/register", status_code=201)
async def register(data: RegisterIn):
    email = data.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = {
        "name": data.name,
        "email": email,
        "phone": data.phone,
        "language": data.language,
        "passwordHash": pwd_context.hash(data.password),
        "role": "user",
        "status": "Active",
        "createdAt": now(),
    }
    result = await db.users.insert_one(user)
    user["_id"] = result.inserted_id
    token = create_token(str(result.inserted_id), "user")
    return {"accessToken": token, "tokenType": "bearer", "user": public_user(user)}

@app.post("/auth/login")
async def login(data: LoginIn):
    user = await db.users.find_one({"email": data.email.lower()})
    if not user or not pwd_context.verify(data.password, user.get("passwordHash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(str(user["_id"]), user.get("role", "user"))
    return {"accessToken": token, "tokenType": "bearer", "user": public_user(user)}

@app.get("/me")
async def me(user=Depends(current_user)):
    return public_user(user)

@app.put("/me")
async def update_me(data: ProfileIn, user=Depends(current_user)):
    email = data.email.lower()
    existing = await db.users.find_one({"email": email, "_id": {"$ne": user["_id"]}})
    if existing:
        raise HTTPException(status_code=409, detail="Email already in use")
    await db.users.update_one({"_id": user["_id"]}, {"$set": data.model_dump()})
    updated = await db.users.find_one({"_id": user["_id"]})
    return public_user(updated)

@app.get("/signs")
async def list_signs(q: Optional[str] = None, category: Optional[str] = None):
    query = {}
    if category and category != "All Categories":
        query["category"] = category
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"meaning": {"$regex": q, "$options": "i"}},
            {"category": {"$regex": q, "$options": "i"}},
        ]
    return [serialize(x) async for x in db.signs.find(query).sort("name", 1)]

@app.get("/signs/categories")
async def sign_categories():
    return await db.signs.distinct("category")

@app.post("/signs", status_code=201)
async def create_sign(data: SignIn, user=Depends(admin_user)):
    doc = {**data.model_dump(), "createdAt": now()}
    try:
        result = await db.signs.insert_one(doc)
    except Exception:
        raise HTTPException(status_code=409, detail="Sign already exists")
    doc["_id"] = result.inserted_id
    return serialize(doc)

@app.put("/signs/{sign_id}")
async def update_sign(sign_id: str, data: SignIn, user=Depends(admin_user)):
    from bson import ObjectId
    result = await db.signs.update_one({"_id": ObjectId(sign_id)}, {"$set": data.model_dump()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Sign not found")
    return serialize(await db.signs.find_one({"_id": ObjectId(sign_id)}))

@app.delete("/signs/{sign_id}")
async def delete_sign(sign_id: str, user=Depends(admin_user)):
    from bson import ObjectId
    result = await db.signs.delete_one({"_id": ObjectId(sign_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Sign not found")
    return {"message": "Sign deleted"}

@app.get("/translations")
async def list_translations(user=Depends(current_user)):
    return [serialize(x) async for x in db.translations.find({"userId": user["_id"]}).sort("createdAt", -1)]

@app.post("/translations", status_code=201)
async def save_translation(data: TranslationIn, user=Depends(current_user)):
    doc = {**data.model_dump(), "userId": user["_id"], "createdAt": now()}
    result = await db.translations.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)

@app.delete("/translations/{translation_id}")
async def delete_translation(translation_id: str, user=Depends(current_user)):
    from bson import ObjectId
    result = await db.translations.delete_one({"_id": ObjectId(translation_id), "userId": user["_id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Translation not found")
    return {"message": "Translation deleted"}

@app.delete("/translations")
async def clear_translations(user=Depends(current_user)):
    result = await db.translations.delete_many({"userId": user["_id"]})
    return {"deleted": result.deleted_count}

@app.get("/favorites")
async def list_favorites(user=Depends(current_user)):
    return [serialize(x) async for x in db.favorites.find({"userId": user["_id"]}).sort("createdAt", -1)]

@app.post("/favorites", status_code=201)
async def add_favorite(data: FavoriteIn, user=Depends(current_user)):
    doc = {"userId": user["_id"], "signName": data.signName, "createdAt": now()}
    try:
        result = await db.favorites.insert_one(doc)
    except Exception:
        raise HTTPException(status_code=409, detail="Already in favorites")
    doc["_id"] = result.inserted_id
    return serialize(doc)

@app.delete("/favorites/{sign_name}")
async def remove_favorite(sign_name: str, user=Depends(current_user)):
    result = await db.favorites.delete_one({"userId": user["_id"], "signName": sign_name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"message": "Favorite removed"}

@app.get("/progress")
async def get_progress(user=Depends(current_user)):
    doc = await db.learningProgress.find_one({"userId": user["_id"]})
    return serialize(doc) if doc else {"course": "Basic Greetings", "progress": 72}

@app.put("/progress")
async def set_progress(data: ProgressIn, user=Depends(current_user)):
    await db.learningProgress.update_one(
        {"userId": user["_id"]},
        {"$set": {**data.model_dump(), "updatedAt": now()}},
        upsert=True
    )
    return serialize(await db.learningProgress.find_one({"userId": user["_id"]}))

@app.post("/feedback", status_code=201)
async def submit_feedback(data: FeedbackIn, user=Depends(current_user)):
    doc = {**data.model_dump(), "userId": user["_id"], "createdAt": now()}
    result = await db.feedback.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc)

@app.get("/admin/stats")
async def admin_stats(user=Depends(admin_user)):
    return {
        "totalUsers": await db.users.count_documents({}),
        "totalSigns": await db.signs.count_documents({}),
        "totalTranslations": await db.translations.count_documents({}),
        "totalFeedback": await db.feedback.count_documents({}),
    }

@app.get("/admin/users")
async def admin_list_users(user=Depends(admin_user)):
    return [public_user(x) async for x in db.users.find({}).sort("createdAt", -1)]

@app.get("/admin/feedback")
async def admin_feedback(user=Depends(admin_user)):
    return [serialize(x) async for x in db.feedback.find({}).sort("createdAt", -1)]
