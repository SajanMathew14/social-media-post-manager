# 🚀 Deployment Guide

This guide will walk you through deploying the Social Media Post Manager to production using Vercel (frontend) and Render (backend).

## 📋 Prerequisites

- ✅ GitHub repository with your code
- ✅ API keys (Serper, Anthropic, OpenAI, Google)
- ✅ Vercel account (vercel.com)
- ✅ Render account (render.com)

## 🎯 Deployment Overview

- **Frontend**: Vercel (Next.js)
- **Backend**: Render (FastAPI + PostgreSQL)
- **Database**: Render PostgreSQL (Free tier)

## 📝 Step-by-Step Deployment

### Phase 1: Backend Deployment (Render)

#### 1. Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up with GitHub
3. Connect your GitHub account

#### 2. Deploy from GitHub
1. **Dashboard** → **New** → **Blueprint**
2. **Connect GitHub repository**: `your-username/social-media-post-manager`
3. **Blueprint file**: `render.yaml` (already created)
4. **Service Group Name**: `social-media-manager`
5. Click **Apply**

#### 3. Set Environment Variables
Render will create two services from the `render.yaml`:
- `social-media-db` (PostgreSQL database)
- `social-media-backend` (FastAPI application)

For the **backend service**, add these environment variables:

```bash
# Required API Keys (get from your .env file)
SERPER_API_KEY=your_serper_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
GOOGLE_API_KEY=your_google_api_key_here

# Will be auto-set by Render
DATABASE_URL=postgresql://... (auto-generated)
ALLOWED_HOSTS=https://your-frontend-domain.vercel.app,http://localhost:3000
```

#### 4. Wait for Deployment
- Database creation: ~2-3 minutes
- Backend deployment: ~5-7 minutes
- Check logs for any errors

#### 5. Get Backend URL
Once deployed, note your backend URL:
```
https://social-media-backend-xxxx.onrender.com
```

### Phase 2: Frontend Deployment (Vercel)

#### 1. Create Vercel Account
1. Go to [vercel.com](https://vercel.com)
2. Sign up with GitHub
3. Connect your GitHub account

#### 2. Import Project
1. **Dashboard** → **New Project**
2. **Import Git Repository**: Select your repo
3. **Framework Preset**: Next.js (auto-detected)
4. **Root Directory**: Leave empty (monorepo config in vercel.json)
5. **Build Settings**: 
   - Build Command: `cd frontend && pnpm build`
   - Install Command: `pnpm install`

#### 3. Set Environment Variables
Add this environment variable:

```bash
NEXT_PUBLIC_API_URL=https://your-backend-name.onrender.com
```

Replace `your-backend-name` with your actual Render backend URL.

#### 4. Deploy
1. Click **Deploy**
2. Wait ~3-5 minutes for build and deployment
3. Get your frontend URL: `https://your-project-name.vercel.app`

### Phase 3: Update CORS Settings

#### 1. Update Backend CORS
1. Go to Render dashboard
2. Select your backend service
3. Go to **Environment**
4. Update `ALLOWED_HOSTS`:
```bash
ALLOWED_HOSTS=https://your-project-name.vercel.app,http://localhost:3000
```

#### 2. Redeploy Backend
The backend will automatically redeploy with new CORS settings.

### Phase 4: Database Setup

#### 1. Seed Database
Once backend is running, seed the database with topic configurations:

**Option A: Via Render Shell**
1. Go to Render dashboard
2. Select your backend service
3. Go to **Shell** tab
4. Run: `python scripts/seed_topics.py`

**Option B: Locally with Production DB**
1. Get DATABASE_URL from Render environment variables
2. Set it in your local `.env`
3. Run: `pnpm seed:db`

## 🧪 Testing Deployment

### 1. Backend Health Check
Visit: `https://your-backend-name.onrender.com/health`

Expected response:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### 2. Frontend Test
1. Visit: `https://your-project-name.vercel.app`
2. Create a session (should work automatically)
3. Try fetching news with a topic like "AI"
4. Verify the complete workflow works

### 3. API Documentation
Visit: `https://your-backend-name.onrender.com/docs`

## ⚠️ Important Notes

### Render Free Tier Limitations
- **Sleep after 15 minutes** of inactivity
- **750 hours/month** total
- **Cold starts** may take 30-60 seconds
- **PostgreSQL**: 1GB storage, 97 connection limit

### Environment Variables Security
- ✅ Never commit `.env` files to Git
- ✅ Use Render/Vercel environment variable settings
- ✅ Rotate API keys regularly

### Domain Configuration
- Vercel provides free `.vercel.app` subdomain
- Render provides free `.onrender.com` subdomain
- Custom domains available on paid plans

## 🔧 Troubleshooting

### Backend Issues
1. **Build Fails**: Check Python dependencies in `requirements.txt`
2. **Database Connection**: Verify DATABASE_URL is set correctly
3. **API Keys**: Ensure all required API keys are set
4. **CORS Errors**: Update ALLOWED_HOSTS with correct frontend URL

### Frontend Issues
1. **Build Fails**: Check if `NEXT_PUBLIC_API_URL` is set
2. **API Calls Fail**: Verify backend URL is correct and accessible
3. **404 Errors**: Check Vercel routing configuration

### Common Solutions
```bash
# Test backend locally
cd backend
uvicorn app.main:app --reload

# Test frontend locally
cd frontend
pnpm dev

# Check build process
pnpm deploy:check
```

## 📊 Monitoring

### Render Monitoring
- **Logs**: Real-time application logs
- **Metrics**: CPU, memory, response times
- **Alerts**: Email notifications for downtime

### Vercel Monitoring
- **Analytics**: Page views, performance metrics
- **Functions**: Serverless function monitoring
- **Speed Insights**: Core Web Vitals

## 🔄 Updates and Redeployment

### Automatic Deployments
Both Vercel and Render are configured for automatic deployments:
- **Push to main branch** → Automatic deployment
- **Pull request** → Preview deployments (Vercel)

### Manual Redeployment
- **Render**: Dashboard → Service → Manual Deploy
- **Vercel**: Dashboard → Project → Deployments → Redeploy

## 🎉 Success!

Once deployed, you'll have:
- ✅ **Frontend**: `https://your-project.vercel.app`
- ✅ **Backend**: `https://your-backend.onrender.com`
- ✅ **Database**: PostgreSQL on Render
- ✅ **API Docs**: `https://your-backend.onrender.com/docs`

Your Social Media Post Manager is now live and ready for users! 🚀

## 📞 Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review Render/Vercel logs
3. Verify all environment variables are set correctly
4. Test locally first to isolate the issue
