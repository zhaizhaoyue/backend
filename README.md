# Domain Guardian - Backend API

FastAPI-based backend for automated domain ownership verification and legal risk assessment.

## 🚀 Features

- **RDAP/WHOIS Lookups**: Automated domain registration data retrieval
- **Legal Risk Classification**: AI-powered risk assessment based on ownership patterns
- **Evidence Generation**: Automated screenshot capture using Playwright
- **CSV Export**: Export results for legal documentation
- **Bulk Processing**: Process multiple domains in parallel
- **Privacy Protection Detection**: Identify privacy-protected registrations

## 🛠️ Tech Stack

- **FastAPI** - Modern, fast web framework for building APIs
- **Pydantic** - Data validation using Python type annotations
- **HTTPX** - Async HTTP client for RDAP queries
- **Playwright** - Browser automation for evidence screenshots
- **Uvicorn** - Lightning-fast ASGI server

## 📋 Prerequisites

- Python 3.11+
- Playwright (chromium browser)

## 🚀 Quick Start

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright Browsers

```bash
playwright install chromium
```

### 4. Run the Server

```bash
# Development mode with auto-reload
python main.py

# Or using uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 5. API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🌍 Environment Variables

Configure these environment variables for enhanced functionality:

```bash
# Optional: API Ninjas key for fallback WHOIS data
export API_NINJAS_KEY=your_api_key_here

# Optional: Momen integration
export MOMEN_API_KEY=your_momen_api_key
export MOMEN_WEBHOOK_URL=https://your-momen-webhook-url

# Evidence storage path (default: ./evidence)
export EVIDENCE_BASE_PATH=./evidence
```

## 📡 API Endpoints

### Health Check
```bash
GET /api/health
```

### Domain Lookup
```bash
POST /api/domains/lookup
Content-Type: application/json

{
  "domains": ["example.com", "test.org"],
  "expected_group_names": ["Acme Corp", "ACME"],
  "expiry_threshold_months": 6,
  "momen_context_id": null
}
```

### Download CSV Results
```bash
GET /api/results/{run_id}/csv
```

### Get Evidence Screenshot
```bash
GET /api/evidence/{run_id}/{filename}
```

## 🚀 Deployment

### Railway

1. Install Railway CLI:
```bash
npm install -g @railway/cli
```

2. Login and deploy:
```bash
railway login
railway init
railway up
```

The `railway.json` configuration is already included.

### Render

1. Create account at [render.com](https://render.com)
2. Connect your GitHub repository
3. Render will automatically detect `render.yaml`
4. Set environment variables in Render dashboard
5. Deploy!

### Docker

Build and run with Docker:

```bash
# Build image
docker build -t domain-guardian-api .

# Run container
docker run -p 8000:8000 \
  -e API_NINJAS_KEY=your_key \
  domain-guardian-api
```

### Heroku

Deploy to Heroku:

```bash
# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Set buildpack
heroku buildpacks:set heroku/python

# Set environment variables
heroku config:set API_NINJAS_KEY=your_key

# Deploy
git push heroku main
```

## 📁 Project Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── models.py               # Pydantic data models
├── rdap_client.py          # RDAP/WHOIS client
├── legal_intel.py          # Legal risk classification logic
├── evidence_generator.py   # Screenshot generation
├── csv_exporter.py         # CSV export functionality
├── momen_client.py         # Momen integration client
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
├── railway.json            # Railway deployment config
├── render.yaml             # Render deployment config
├── Procfile                # Heroku deployment config
└── runtime.txt             # Python version specification
```

## 🔍 How It Works

1. **Domain Input**: Receives domain list via API
2. **RDAP Lookup**: Queries RDAP servers for registration data
3. **Risk Classification**: Analyzes ownership patterns
4. **Evidence Capture**: Takes screenshots of RDAP sources
5. **Results Export**: Returns structured data with CSV export

## 🔒 Legal Risk Levels

- **No Risk (Low)**: Domain owned by expected organization
- **Medium Risk**: Privacy protection or unknown owner
- **High Risk**: Third-party ownership or expiring soon

## 🧪 Testing

Run the test suite:

```bash
# Simple test
python simple_test.py

# Enhanced test with screenshots
python enhanced_test.py
```

## 🛠️ Development

### Code Style

Follow PEP 8 style guidelines:

```bash
# Install dev dependencies
pip install black flake8 mypy

# Format code
black .

# Lint
flake8 .

# Type check
mypy .
```

### Adding New Features

1. Update models in `models.py`
2. Add business logic in respective modules
3. Update API endpoints in `main.py`
4. Test thoroughly
5. Update documentation

## 📊 Performance

- Processes 10-50 domains/minute (depending on RDAP server response times)
- Async implementation for concurrent lookups
- Screenshot generation runs in background

## ⚠️ Important Notes

- RDAP servers have rate limits - respect them
- Some TLDs may not have RDAP support
- Privacy-protected domains have limited information
- Screenshot generation requires ~1-2 seconds per domain

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

Proprietary - All rights reserved

## 🆘 Support

For issues or questions:
- Check API documentation at `/docs`
- Review error logs
- Contact development team

---

**Built for Legal Professionals** | Powered by RDAP & FastAPI
# backend
