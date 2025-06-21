# 🔧 CORS Fix for Vercel Frontend + Render Backend

## 🚨 Issue Identified

The backend logs showed repeated `400 Bad Request` errors for OPTIONS preflight requests:
```
INFO:     36.255.91.181:0 - "OPTIONS /api/news/fetch HTTP/1.1" 400 Bad Request
```

This indicates that the frontend on Vercel was making cross-origin requests to the backend on Render, but the backend wasn't properly configured to handle CORS preflight requests from Vercel domains.

## 🛠️ Solution Implemented

### 1. Updated CORS Origins Configuration
Added Vercel domains to the allowed origins in `backend/app/core/config.py`:
```python
CORS_ORIGINS: List[str] = [
    "http://localhost:3000", 
    "http://127.0.0.1:3000", 
    "https://*.onrender.com",
    "https://*.vercel.app",    # Added for Vercel deployments
    "https://*.vercel.sh"      # Added for Vercel preview deployments
]
```

### 2. Updated Trusted Hosts
Added Vercel domains to trusted hosts:
```python
TRUSTED_HOSTS: List[str] = ["localhost", "127.0.0.1", "*.onrender.com", "*.vercel.app", "*.vercel.sh"]
```

### 3. Enhanced CORS Middleware Configuration
Modified `backend/app/main.py` to properly handle wildcard domains using regex pattern matching:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=static_origins,
    allow_origin_regex=r"https://.*\.(vercel\.app|vercel\.sh|onrender\.com)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📋 Deployment Steps

1. **Commit and Push Changes**:
   ```bash
   git add backend/app/core/config.py backend/app/main.py
   git commit -m "Fix CORS configuration for Vercel frontend"
   git push
   ```

2. **Render will automatically redeploy** when you push to your repository.

3. **No Environment Variables Needed**: The CORS configuration now automatically allows all Vercel domains.

## ✅ Verification

After deployment, the backend should:
1. Accept OPTIONS preflight requests from Vercel domains
2. Return proper CORS headers
3. Allow POST requests from your Vercel frontend

### Test CORS Headers
You can verify CORS is working by checking the response headers:
```bash
curl -I -X OPTIONS https://your-backend.onrender.com/api/news/fetch \
  -H "Origin: https://your-app.vercel.app" \
  -H "Access-Control-Request-Method: POST"
```

Expected headers in response:
```
Access-Control-Allow-Origin: https://your-app.vercel.app
Access-Control-Allow-Methods: *
Access-Control-Allow-Headers: *
Access-Control-Allow-Credentials: true
```

## 🔍 How It Works

1. **Static Origins**: Exact domain matches (localhost, etc.) are handled directly
2. **Regex Pattern**: The pattern `https://.*\.(vercel\.app|vercel\.sh|onrender\.com)$` matches:
   - `https://your-app.vercel.app`
   - `https://your-app-git-branch.vercel.app`
   - `https://your-app.vercel.sh`
   - Any subdomain on these platforms

3. **Preflight Handling**: FastAPI's CORS middleware automatically handles OPTIONS requests when configured properly

## 🚀 Benefits

- ✅ No need to hardcode specific Vercel URLs
- ✅ Works with Vercel preview deployments
- ✅ Supports multiple deployment environments
- ✅ Maintains security by only allowing specific domain patterns

## 🐛 Troubleshooting

If CORS issues persist:

1. **Check Browser Console**: Look for specific CORS error messages
2. **Verify Frontend URL**: Ensure your frontend is using HTTPS
3. **Check API Endpoint**: Verify the full URL including `/api/news/fetch`
4. **Review Render Logs**: Check for any startup errors in the backend

## 📝 Notes

- The wildcard pattern `*.vercel.app` in the configuration is converted to a regex pattern for proper matching
- The CORS middleware handles both simple and preflight requests
- Credentials are allowed (`allow_credentials=True`) for session management
