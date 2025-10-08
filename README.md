# ServiceTitan to GoHighLevel Sync API

Flask API for extracting unsold estimates from ServiceTitan and sending them to GoHighLevel.

## Files Created

- `app.py` - Main Flask application
- `requirements.txt` - Python dependencies
- `Procfile` - Railway deployment config
- `railway.json` - Railway settings

## Deploy to Railway

### 1. Initialize Git Repository

```bash
cd /Users/officemac/railway-servicetitan-api
git init
git add .
git commit -m "Initial commit: ServiceTitan sync API"
```

### 2. Deploy to Railway

**Option A: Using Railway CLI**
```bash
# Install Railway CLI if not installed
npm install -g @railway/cli

# Login to Railway
railway login

# Create new project
railway init

# Deploy
railway up
```

**Option B: Using GitHub**
1. Create a new GitHub repo
2. Push this code to GitHub
3. Go to Railway dashboard: https://railway.app
4. Click "New Project" → "Deploy from GitHub repo"
5. Select your repo
6. Railway will auto-detect Python and deploy

### 3. Get Your API URL

After deployment, Railway will give you a public URL like:
```
https://servicetitan-api-production.up.railway.app
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Sync Unsold Estimates
```bash
POST /sync
Content-Type: application/json

{
  "daysBack": 30
}
```

**Response:**
```json
{
  "success": true,
  "metrics": {
    "jobs_checked": 337,
    "unsold_estimates_found": 195,
    "total_value": 2530232,
    "enriched_with_contacts": 195,
    "sent_to_ghl": 195,
    "days_back": 30
  },
  "estimates": [...]
}
```

## Test Locally

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally
python app.py
```

Then test:
```bash
curl http://localhost:5000/health

curl -X POST http://localhost:5000/sync \
  -H "Content-Type: application/json" \
  -d '{"daysBack": 30}'
```

## Connect to n8n

Once deployed, create a simple 3-node workflow in n8n:

1. **Schedule Trigger** - Run daily at 9am
2. **HTTP Request** - POST to your Railway URL `/sync`
3. **Send Success Email** - Optional notification

### n8n HTTP Request Node Config:
- Method: POST
- URL: `https://your-railway-url.up.railway.app/sync`
- Body: `{"daysBack": 30}`
- Headers: `Content-Type: application/json`

## Credentials

All credentials are hardcoded in `app.py`:
- ServiceTitan Client ID, Secret, App Key
- GHL Webhook URL

**Security Note**: For production, move these to Railway environment variables.
