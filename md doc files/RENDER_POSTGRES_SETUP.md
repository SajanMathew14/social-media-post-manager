# Setting Up PostgreSQL on Render

## Step 1: Create a PostgreSQL Database

1. **Log in to Render Dashboard**
   - Go to https://dashboard.render.com

2. **Create New PostgreSQL Database**
   - Click on "New +" button
   - Select "PostgreSQL"

3. **Configure Database Settings**
   - **Name**: Choose a name (e.g., "social-media-post-manager-db")
   - **Database**: Leave as default or specify a name
   - **User**: Leave as default or specify a username
   - **Region**: Select the same region as your web service
   - **PostgreSQL Version**: Select 15 or latest stable
   - **Plan**: Choose "Free" for testing or appropriate paid plan

4. **Create Database**
   - Click "Create Database"
   - Wait for the database to be provisioned (usually takes 1-2 minutes)

## Step 2: Get Database Connection Details

1. **Access Database Dashboard**
   - Click on your newly created database

2. **Copy Connection Details**
   - Find the "Connections" section
   - Copy the "Internal Database URL" (for services within Render)
   - It will look like: `postgresql://user:password@hostname/database_name`

## Step 3: Add Database URL to Your Web Service

1. **Go to Your Web Service**
   - Navigate to your backend web service on Render

2. **Add Environment Variable**
   - Go to "Environment" tab
   - Click "Add Environment Variable"
   - Add:
     - **Key**: `DATABASE_URL`
     - **Value**: Paste the Internal Database URL from Step 2

3. **Save Changes**
   - Click "Save Changes"
   - This will trigger a new deployment

## Step 4: Verify Connection

Once the deployment completes, your application should connect to the PostgreSQL database successfully.

## Important Notes:

- **Internal vs External URL**: Use the Internal Database URL for services running on Render (better performance, no internet round-trip)
- **Free Tier Limitations**: Free PostgreSQL databases on Render expire after 90 days
- **Backups**: Consider setting up regular backups for production use
- **Connection Pooling**: The free tier has connection limits, so connection pooling is important
