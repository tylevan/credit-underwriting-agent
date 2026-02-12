# Credit Underwriting AI Agent

AI-powered credit assessment system built with LangGraph, FastAPI, and React.

## Architecture

```
Frontend (React/Vite) → Backend (FastAPI + LangGraph) → Google Gemini
                                    ↓
                              9 Custom Tools
                              (Customer Info, CIC, DTI, DSCR, Max Loan, ...)
```

## Quick Start (Local)

### Backend
```bash
cd backend
cp .env.example .env  # Edit with your GOOGLE_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Docker Compose
```bash
docker-compose up --build
```

## Deploy to Google Cloud Run

```bash
export GCP_PROJECT_ID=your-project-id
chmod +x infra/deploy.sh
./infra/deploy.sh
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/assess` | Run credit assessment |
| POST | `/api/v1/chat` | Free chat with agent |
| POST | `/api/v1/review` | Human reviewer submit decision |
| GET | `/api/v1/customers` | List customers |
| GET | `/api/v1/customers/{id}` | Customer details |
| GET | `/api/v1/policy` | Credit policy lookup |

## Features

- **Structured Reasoning**: Every tool returns an audit trail step
- **Human-in-the-Loop**: REVIEW cases pause for human approval
- **Guardrails**: Validation node checks LLM decisions against policy
- **Error Handling**: Tools fail gracefully, no agent crashes
- **Audit Logging**: Structured JSON logs for compliance
