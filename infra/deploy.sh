#!/bin/bash
# ══════════════════════════════════════════════════════════════
# DEPLOY SCRIPT: Credit Underwriting Agent → Google Cloud Run
# ══════════════════════════════════════════════════════════════
#
# Chỉ deploy BACKEND lên Cloud Run.
# Frontend deploy riêng trên Cloudflare Pages.
#
# Cách dùng:
#   export GCP_PROJECT_ID=your-project-id
#   export SUPABASE_DATABASE_URL=postgresql://...
#   chmod +x infra/deploy.sh
#   ./infra/deploy.sh
#
# Yêu cầu:
#   - gcloud CLI đã cài đặt và đăng nhập
#   - Docker đã cài đặt
#   - GCP Project đã tạo
# ══════════════════════════════════════════════════════════════

set -euo pipefail

# ── CẤU HÌNH ──
PROJECT_ID="${GCP_PROJECT_ID:-your-project-id}"
REGION="${GCP_REGION:-asia-southeast1}"           # Singapore - gần VN nhất
REPO_NAME="credit-agent"
BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/backend"
BACKEND_SERVICE="credit-agent-backend"

# Frontend URL trên Cloudflare Pages (cập nhật sau khi deploy)
FRONTEND_URL="${CLOUDFLARE_PAGES_URL:-https://your-app.pages.dev}"

# Màu sắc cho output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ════════════════════════════════════════════
# STEP 0: Kiểm tra prerequisites
# ════════════════════════════════════════════

log_info "Step 0: Kiểm tra prerequisites..."

if ! command -v gcloud &> /dev/null; then
    log_error "gcloud CLI chưa được cài đặt. Xem: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    log_error "Docker chưa được cài đặt."
    exit 1
fi

if [ "$PROJECT_ID" = "your-project-id" ]; then
    log_error "Hãy set GCP_PROJECT_ID: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

log_info "Project: ${PROJECT_ID}"
log_info "Region: ${REGION}"

# ════════════════════════════════════════════
# STEP 1: Setup GCP Project
# ════════════════════════════════════════════

log_info "Step 1: Setup GCP Project..."

gcloud config set project ${PROJECT_ID}

# Enable APIs (chỉ những gì cần cho backend)
log_info "  Enabling APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    --quiet

# Create Artifact Registry repo
log_info "  Creating Artifact Registry repo..."
gcloud artifacts repositories create ${REPO_NAME} \
    --repository-format=docker \
    --location=${REGION} \
    --description="Credit Underwriting Agent Docker images" \
    --quiet 2>/dev/null || log_warn "  Repo already exists, skipping."

# Configure Docker auth
log_info "  Configuring Docker auth..."
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet

# ════════════════════════════════════════════
# STEP 2: Store secrets in Secret Manager
# ════════════════════════════════════════════

log_info "Step 2: Store secrets..."

# ── Google API Key ──
if gcloud secrets describe google-api-key --project=${PROJECT_ID} &>/dev/null; then
    log_warn "  Secret 'google-api-key' already exists."
    read -p "  Cập nhật secret? (y/N): " update_secret
    if [ "$update_secret" = "y" ]; then
        read -sp "  Nhập GOOGLE_API_KEY: " api_key
        echo
        echo -n "$api_key" | gcloud secrets versions add google-api-key --data-file=-
        log_info "  Secret updated."
    fi
else
    read -sp "  Nhập GOOGLE_API_KEY: " api_key
    echo
    echo -n "$api_key" | gcloud secrets create google-api-key --data-file=- --replication-policy="automatic"
    log_info "  Secret created."
fi

# ── Supabase Database URL ──
if gcloud secrets describe supabase-database-url --project=${PROJECT_ID} &>/dev/null; then
    log_warn "  Secret 'supabase-database-url' already exists."
    read -p "  Cập nhật secret? (y/N): " update_db
    if [ "$update_db" = "y" ]; then
        read -sp "  Nhập SUPABASE_DATABASE_URL: " db_url
        echo
        echo -n "$db_url" | gcloud secrets versions add supabase-database-url --data-file=-
        log_info "  Secret updated."
    fi
else
    if [ -n "${SUPABASE_DATABASE_URL:-}" ]; then
        echo -n "$SUPABASE_DATABASE_URL" | gcloud secrets create supabase-database-url --data-file=- --replication-policy="automatic"
        log_info "  Database secret created from env."
    else
        read -sp "  Nhập SUPABASE_DATABASE_URL: " db_url
        echo
        echo -n "$db_url" | gcloud secrets create supabase-database-url --data-file=- --replication-policy="automatic"
        log_info "  Database secret created."
    fi
fi

# ════════════════════════════════════════════
# STEP 3: Build & Push Backend
# ════════════════════════════════════════════

log_info "Step 3: Build & Push Backend..."

cd backend
docker build -t ${BACKEND_IMAGE}:latest -t ${BACKEND_IMAGE}:$(date +%Y%m%d) .
docker push ${BACKEND_IMAGE}:latest
cd ..

log_info "  Backend image pushed: ${BACKEND_IMAGE}:latest"

# ════════════════════════════════════════════
# STEP 4: Deploy Backend to Cloud Run
# ════════════════════════════════════════════

log_info "Step 4: Deploy Backend to Cloud Run..."

gcloud run deploy ${BACKEND_SERVICE} \
    --image ${BACKEND_IMAGE}:latest \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --port 8000 \
    --memory 1Gi \
    --cpu 1 \
    --timeout 120 \
    --min-instances 0 \
    --max-instances 2 \
    --concurrency 80 \
    --cpu-boost \
    --set-env-vars "LLM_MODEL=gemini-2.5-flash,LLM_TEMPERATURE=0,DATA_PATH=data/bank_churn_dataset_80k.csv,LOG_LEVEL=INFO,FRONTEND_URL=${FRONTEND_URL}" \
    --set-secrets "GOOGLE_API_KEY=google-api-key:latest,DATABASE_URL=supabase-database-url:latest" \
    --quiet

# Lấy Backend URL
BACKEND_URL=$(gcloud run services describe ${BACKEND_SERVICE} --region ${REGION} --format 'value(status.url)')
log_info "  Backend deployed: ${BACKEND_URL}"

# Test health
log_info "  Testing backend health..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" ${BACKEND_URL}/health)
if [ "$HTTP_CODE" = "200" ]; then
    log_info "  ✅ Backend healthy!"
else
    log_error "  ❌ Backend health check failed (HTTP ${HTTP_CODE})"
fi

# ════════════════════════════════════════════
# DONE
# ════════════════════════════════════════════

echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  🎉 BACKEND DEPLOY HOÀN TẤT!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Backend  : ${BACKEND_URL}"
echo -e "  API Docs : ${BACKEND_URL}/docs"
echo -e "  Health   : ${BACKEND_URL}/health"
echo ""
echo -e "  ${YELLOW}Bước tiếp theo:${NC}"
echo -e "  1. Deploy frontend lên Cloudflare Pages"
echo -e "  2. Set VITE_API_URL = ${BACKEND_URL}/api/v1"
echo -e "  3. Update CLOUDFLARE_PAGES_URL và re-deploy nếu cần CORS"
echo ""
echo -e "  Test nhanh:"
echo -e "    curl ${BACKEND_URL}/health"
echo -e "    curl ${BACKEND_URL}/api/v1/customers"
echo ""
