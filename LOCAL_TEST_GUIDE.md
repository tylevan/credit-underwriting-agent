# 🧪 HƯỚNG DẪN TEST LOCAL

## Yêu cầu
- Python 3.11+
- Node.js 20+
- GOOGLE_API_KEY (Gemini)

---

## Bước 1: Setup Backend

```bash
cd backend

# Tạo virtual environment
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate   # Windows

# Cài dependencies
pip install -r requirements.txt

# Tạo file .env
cp .env.example .env
# Mở .env và paste GOOGLE_API_KEY vào
```

**Sửa file `.env`:**
```
GOOGLE_API_KEY=AIzaSy...your-key-here...
```

**Chạy backend:**
```bash
uvicorn app.main:app --reload --port 8000
```

**Test nhanh backend:**
```bash
# Health check
curl http://localhost:8000/health

# Danh sách khách hàng
curl http://localhost:8000/api/v1/customers

# Thông tin 1 khách hàng
curl http://localhost:8000/api/v1/customers/1

# Credit policy
curl http://localhost:8000/api/v1/policy

# Thẩm định (sẽ mất 10-30 giây vì agent gọi nhiều tools)
curl -X POST http://localhost:8000/api/v1/assess \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "1", "loan_amount": 100000000, "term_months": 24}'
```

**Xem API docs tự động (Swagger):**
Mở browser: http://localhost:8000/docs

---

## Bước 2: Setup Frontend

**Mở terminal mới** (giữ backend chạy):

```bash
cd frontend

# Cài dependencies
npm install

# Chạy dev server
npm run dev:client
```

**Mở browser:** http://localhost:5000

Frontend tự động proxy `/api/*` → `http://localhost:8000` qua Vite config.

---

## Bước 3: Test End-to-End

1. Mở http://localhost:5000
2. Nhập ID khách hàng (ví dụ: `1`, `2`, `100`, `999`)
3. Chọn số tiền vay và kỳ hạn
4. Click "Gửi yêu cầu thẩm định"
5. Chờ 10-30 giây (agent đang gọi Gemini + chạy tools)
6. Xem kết quả: APPROVED / REVIEW / REJECTED

---

## Các ID thú vị để test

| ID | Mong đợi | Lý do |
|----|----------|-------|
| 1  | Xem CIC 725 | CIC tốt, chủ doanh nghiệp |
| 2  | Xem CIC 689 | CIC khá, nội trợ/sinh viên, balance thấp |
| 3  | Xem CIC 702 | CIC khá, thu nhập cao |
| 4  | APPROVED? | CIC 766, rất tốt |

---

## Troubleshooting

**Backend không start:**
- Kiểm tra GOOGLE_API_KEY trong `.env`
- Kiểm tra file CSV tồn tại: `backend/data/bank_churn_dataset_80k.csv`

**Frontend lỗi kết nối:**
- Đảm bảo backend đang chạy ở port 8000
- Kiểm tra Vite proxy trong `vite.config.ts`

**Agent trả về lỗi:**
- Xem log backend trong terminal
- API key hết quota? Check Google AI Studio

**Thẩm định quá lâu (> 60s):**
- Gemini API có thể chậm lần đầu
- Kiểm tra network / VPN
