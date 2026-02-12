# 🚀 Hướng dẫn Deploy — Credit Underwriting Agent

Kiến trúc tiết kiệm tối đa (ước tính **$0–3/tháng** trên $10 free GCP credit):

| Thành phần | Nền tảng | Chi phí |
|---|---|---|
| Frontend (React) | Cloudflare Pages | **$0** |
| Backend (FastAPI) | Google Cloud Run | **$0–3** |
| Database (assessments) | Supabase PostgreSQL | **$0** |
| CSV data (static) | Baked into Docker image | **$0** |

---

## Bước 1: Tạo Supabase Project (Database miễn phí)

1. Truy cập [supabase.com](https://supabase.com) → Sign up / Login
2. **New Project** → chọn region `Southeast Asia (Singapore)`
3. Đặt tên project và database password
4. Sau khi tạo xong, vào **Settings → Database → Connection string**
5. Copy **URI** (Transaction mode), format:
   ```
   postgresql://postgres.[ref]:[password]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
   ```
6. **Lưu lại connection string này** — sẽ dùng ở bước 2

> **Lưu ý**: Bảng `assessments` sẽ được tạo tự động khi backend khởi động lần đầu.

---

## Bước 2: Deploy Backend lên Google Cloud Run

### Yêu cầu
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) đã cài đặt
- [Docker](https://docs.docker.com/get-docker/) đã cài đặt
- GCP Project với billing đã bật (dùng $10 free credit)

### Deploy

```bash
# 1. Set biến môi trường
export GCP_PROJECT_ID=your-gcp-project-id
export SUPABASE_DATABASE_URL="postgresql://postgres.[ref]:[password]@..."

# 2. Chạy deploy script
chmod +x infra/deploy.sh
./infra/deploy.sh
```

Script sẽ tự động:
- Enable Cloud Run, Artifact Registry, Secret Manager APIs
- Lưu `GOOGLE_API_KEY` và `DATABASE_URL` vào Secret Manager
- Build & push Docker image
- Deploy lên Cloud Run (512Mi RAM, scale-to-zero)

### Kết quả
Sau khi deploy xong, bạn sẽ nhận được Backend URL:
```
Backend: https://credit-agent-backend-xxxxx-as.a.run.app
```

**Lưu lại URL này** — sẽ dùng ở bước 3.

---

## Bước 3: Deploy Frontend lên Cloudflare Pages

### 3a. Setup trên Cloudflare Dashboard

1. Truy cập [dash.cloudflare.com](https://dash.cloudflare.com) → Sign up / Login
2. Sidebar → **Workers & Pages** → **Create** → **Pages**
3. **Connect to Git** → chọn GitHub/GitLab repo
4. Cấu hình build:

   | Cấu hình | Giá trị |
   |---|---|
   | **Framework preset** | None |
   | **Build command** | `cd frontend && npm install && npm run build` |
   | **Build output directory** | `frontend/dist/public` |
   | **Root directory** | `/` |

5. **Environment variables** → thêm:

   | Biến | Giá trị |
   |---|---|
   | `VITE_API_URL` | `https://credit-agent-backend-xxxxx-as.a.run.app/api/v1` |
   | `NODE_VERSION` | `20` |

6. Click **Save and Deploy**

### 3b. Lấy Frontend URL

Sau khi deploy xong, Cloudflare sẽ cấp URL:
```
https://your-project.pages.dev
```

---

## Bước 4: Cập nhật CORS Backend

Sau khi có Frontend URL từ Cloudflare Pages, cập nhật CORS trên Cloud Run:

```bash
# Cập nhật backend CORS cho phép frontend gọi API
gcloud run services update credit-agent-backend \
    --region asia-southeast1 \
    --update-env-vars "FRONTEND_URL=https://your-project.pages.dev" \
    --quiet
```

Hoặc cập nhật lại deploy script:
```bash
export CLOUDFLARE_PAGES_URL=https://your-project.pages.dev
./infra/deploy.sh
```

---

## Kiểm tra

```bash
# Health check
curl https://credit-agent-backend-xxxxx-as.a.run.app/health

# Danh sách khách hàng
curl https://credit-agent-backend-xxxxx-as.a.run.app/api/v1/customers

# Frontend
# Mở https://your-project.pages.dev trên browser
```

---

## Cập nhật sau này

### Cập nhật Backend
```bash
cd backend
# Sửa code...
./infra/deploy.sh
```

### Cập nhật Frontend
```bash
git add . && git commit -m "update frontend" && git push
# Cloudflare Pages tự động rebuild & deploy!
```

---

## Local Development (không ảnh hưởng production)

```bash
# Backend (SQLite tự động, không cần Supabase)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (Vite proxy tự động, không cần VITE_API_URL)
cd frontend
npm install
npm run dev
```
