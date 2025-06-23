# 🚨 RENDER DEPLOYMENT FIX - STEP BY STEP GUIDE

## Problem Summary
Your current Render service is configured as a **Node.js application** and keeps trying to run `pnpm install` and `pnpm run build`, even though you want to deploy only the **Python FastAPI backend**.

## Root Cause
The existing Render service has cached Node.js configuration settings that cannot be changed to Python. You need to create a **completely new service** configured specifically for Python.

## 🔧 SOLUTION: Create New Python Service

### Step 1: Delete Current Service (Important!)
1. Go to **Render Dashboard**: https://dashboard.render.com
2. Find your current `social-media-post-manager` service
3. Click on the service → **Settings** → **Delete Service**
4. Confirm deletion (this clears all Node.js configuration)

### Step 2: Create New Python Web Service
1. **Dashboard** → **New** → **Web Service**
2. **Connect Repository**: `SajanMathew14/social-media-post-manager`
3. **Configure Service**:

```
Name: social-media-backend
Environment: Python 3
Region: Oregon (or your preferred region)
Branch: main
Root Directory: backend          ← CRITICAL: This tells Render to only look in backend folder
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Step 3: Add Environment Variables
Add these environment variables to your new service:

**Required API Keys:**
```
SERPER_API_KEY=your_serper_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

**Configuration Variables:**
```
ALLOWED_HOSTS=https://your-frontend-domain.vercel.app,http://localhost:3000
LOG_LEVEL=INFO
LOG_FORMAT=json
DAILY_QUOTA_LIMIT=10
MONTHLY_QUOTA_LIMIT=300
DEFAULT_LLM_MODEL=claude-3-5-sonnet
LLM_MAX_TOKENS=4000
LLM_TEMPERATURE=0.7
MAX_NEWS_ARTICLES=12
DEFAULT_NEWS_ARTICLES=5
NEWS_CACHE_TTL=3600
```

### Step 4: Deploy
1. Click **Create Web Service**
2. Render will now:
   - ✅ Detect Python environment (because Root Directory = backend)
   - ✅ Run `pip install -r requirements.txt`
   - ✅ Start with `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - ✅ Ignore all Node.js/frontend files

## 🎯 Expected Deployment Logs (Success)
```
==> Cloning from https://github.com/SajanMathew14/social-media-post-manager
==> Using Python version 3.11.x
==> Running build command 'pip install -r requirements.txt'...
Successfully installed fastapi uvicorn sqlalchemy...
==> Running start command 'uvicorn app.main:app --host 0.0.0.0 --port $PORT'...
INFO: Started server process
INFO: Uvicorn running on http://0.0.0.0:10000
==> Your service is live at https://social-media-backend-xxxx.onrender.com
```

## 🔍 Verification Steps
Once deployed, test these endpoints:

1. **Health Check**: `https://your-backend-name.onrender.com/health`
   - Should return: `{"status": "healthy", "database": "connected"}`

2. **API Documentation**: `https://your-backend-name.onrender.com/docs`
   - Should show FastAPI Swagger UI

3. **Root Endpoint**: `https://your-backend-name.onrender.com/`
   - Should return: `{"message": "Social Media Post Manager API", "version": "1.0.0", "status": "running"}`

## 🚫 What NOT to Do
- ❌ Don't try to modify the existing service settings
- ❌ Don't leave Root Directory empty (it will deploy entire repo)
- ❌ Don't use the old render.yaml in root directory
- ❌ Don't set Environment to Node.js

## 🎉 Success Indicators
- ✅ Build logs show `pip install` (not pnpm)
- ✅ Start logs show `uvicorn` starting
- ✅ Health endpoint returns 200 OK
- ✅ No Node.js or pnpm errors in logs

## 📞 If You Still Have Issues
1. Double-check **Root Directory** is set to `backend`
2. Verify **Environment** is set to `Python 3`
3. Ensure **Build Command** is `pip install -r requirements.txt`
4. Check that all environment variables are added

The key insight: **Root Directory = backend** tells Render to treat only the backend folder as the application, ignoring all Node.js files in the root.
