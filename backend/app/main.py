"""
FastAPI Application: Credit Underwriting Agent API.
"""

import uuid
import logging
import re
from contextlib import asynccontextmanager
from datetime import date, datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, AIMessage

from .config.settings import settings
from .config.policy_constants import CreditPolicy
from .models.schemas import (
    AssessmentRequest, AssessmentResponse,
    ChatRequest, ChatResponse,
    HumanReviewRequest, HealthResponse,
)
from .models.database import get_customer_by_id, list_all_customers, get_total_customer_count
from .models import assessment_repo
from .agent.graph import credit_agent
from .middleware.logging import setup_logging
from .middleware.error_handler import global_exception_handler
from .middleware.rate_limiter import RateLimitMiddleware
from .utils.helpers import clean_agent_content

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.LOG_LEVEL)
    await assessment_repo.init_db(settings.DATABASE_PATH)
    logger.info("Credit Underwriting Agent API starting... DB initialized.")
    yield
    logger.info("API shutting down")


app = FastAPI(
    title="Credit Underwriting Agent API",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS: cho phép frontend gọi API cross-origin ──
origins = [
    settings.FRONTEND_URL,                          # Cloud Run env: Cloudflare Pages URL
    "https://credit-underwriting-agent.pages.dev",  # Cloudflare Pages production
    "https://fagent.aimarketinghubs.com",            # custom domain
    "http://localhost:5173",                         # Vite default
    "http://localhost:5000",                         # Vite custom port
    "http://localhost:3000",                         # Fallback
]
# Lọc bỏ chuỗi rỗng
origins = [o for o in origins if o]

# ── Rate Limiting (inner — chạy sau CORS) ──
app.add_middleware(RateLimitMiddleware)

# ── CORS (outer — bọc ngoài cùng, đảm bảo mọi response đều có CORS headers) ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(Exception, global_exception_handler)


# ── Health ──

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse()


# ── Assess ──

@app.post("/api/v1/assess", response_model=AssessmentResponse)
async def assess_credit(request: AssessmentRequest):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    # ═══════════════════════════════════════════════
    # PRE-VALIDATION: reject immediately if basic rules fail
    # ═══════════════════════════════════════════════
    pre_errors = []

    # 1. Customer existence
    try:
        customer = get_customer_by_id(int(request.customer_id))
        if customer is None:
            pre_errors.append(f"Khách hàng ID {request.customer_id} không tồn tại trong hệ thống.")
    except (ValueError, TypeError):
        pre_errors.append(f"ID khách hàng '{request.customer_id}' không hợp lệ.")

    # 2. Loan amount range
    if request.loan_amount < CreditPolicy.LOAN_MIN:
        pre_errors.append(
            f"Số tiền vay {request.loan_amount:,.0f} VND thấp hơn mức tối thiểu {CreditPolicy.LOAN_MIN:,.0f} VND."
        )
    if request.loan_amount > CreditPolicy.LOAN_MAX:
        pre_errors.append(
            f"Số tiền vay {request.loan_amount:,.0f} VND vượt quá trần tối đa {CreditPolicy.LOAN_MAX:,.0f} VND."
        )

    # 3. Term months range
    if request.term_months < CreditPolicy.TERM_MIN_MONTHS:
        pre_errors.append(
            f"Kỳ hạn {request.term_months} tháng ngắn hơn tối thiểu {CreditPolicy.TERM_MIN_MONTHS} tháng."
        )
    if request.term_months > CreditPolicy.TERM_MAX_MONTHS:
        pre_errors.append(
            f"Kỳ hạn {request.term_months} tháng vượt quá tối đa {CreditPolicy.TERM_MAX_MONTHS} tháng (5 năm)."
        )

    if pre_errors:
        rejection_reason = " ".join(pre_errors)
        rejection_trail = [{
            "step": 0,
            "action": "Kiểm tra điều kiện đầu vào",
            "result": "KHÔNG ĐẠT",
            "decision": "FAIL",
            "detail": rejection_reason,
            "policy_ref": "Điều kiện cơ bản — Mục 1, 2",
        }]
        report = (
            f"## QUYẾT ĐỊNH: REJECTED\n\n"
            f"## LÝ DO\n{rejection_reason}\n\n"
            f"## ĐỀ XUẤT\n"
            f"Vui lòng kiểm tra lại thông tin và đảm bảo:\n"
            f"- ID khách hàng tồn tại trong hệ thống\n"
            f"- Số tiền vay từ {CreditPolicy.LOAN_MIN:,.0f} đến {CreditPolicy.LOAN_MAX:,.0f} VND\n"
            f"- Kỳ hạn vay từ {CreditPolicy.TERM_MIN_MONTHS} đến {CreditPolicy.TERM_MAX_MONTHS} tháng\n"
        )

        # Save to DB
        try:
            await assessment_repo.save_assessment({
                "thread_id": thread_id,
                "customer_id": request.customer_id,
                "customer_name": "",
                "loan_amount": request.loan_amount,
                "term_months": request.term_months,
                "decision": "REJECTED",
                "cic_score": None,
                "dti": None,
                "approved_limit": None,
                "reasoning_trail": rejection_trail,
                "report": report,
                "needs_human_review": False,
            })
        except Exception as db_err:
            logger.warning(f"Failed to save pre-validation rejection: {db_err}")

        logger.info("pre_validation_rejected", extra={
            "thread_id": thread_id,
            "customer_id": request.customer_id,
            "errors": pre_errors,
        })

        return AssessmentResponse(
            success=True,
            thread_id=thread_id,
            decision="REJECTED",
            report=report,
            reasoning_trail=rejection_trail,
            needs_human_review=False,
        )

    # ═══════════════════════════════════════════════
    # PASSED PRE-VALIDATION → Run AI Agent
    # ═══════════════════════════════════════════════
    prompt = (
        f"Thẩm định hồ sơ vay tín chấp tiêu dùng:\n"
        f"- ID Khách hàng: {request.customer_id}\n"
        f"- Số tiền vay: {request.loan_amount:,.0f} VND\n"
        f"- Kỳ hạn: {request.term_months} tháng\n\n"
        f"Hãy thực hiện đầy đủ quy trình thẩm định và đưa ra quyết định."
    )

    try:
        inputs = {
            "messages": [HumanMessage(content=prompt)],
            "scratchpad": "",
            "reasoning_trail": [],
            "needs_human_review": False,
            "human_decision": None,
            "human_note": None,
            "final_decision": None,
        }

        final_content = ""
        reasoning_trail = []

        for state in credit_agent.stream(inputs, config=config, stream_mode="values"):
            last_msg = state["messages"][-1]
            if isinstance(last_msg, AIMessage) and last_msg.content and not last_msg.tool_calls:
                final_content = clean_agent_content(last_msg.content)
            reasoning_trail = state.get("reasoning_trail", [])

        final_state = credit_agent.get_state(config)
        final_decision = final_state.values.get("final_decision")
        needs_review = final_state.values.get("needs_human_review", False)

        # ── Extract data from trail for DB ──
        customer_name = ""
        cic_score = None
        dti_value = None
        approved_limit = None
        for step in reasoning_trail:
            if step.get("step") == 1:
                name_match = re.match(r"^([^,]+),", step.get("result", ""))
                customer_name = name_match.group(1) if name_match else ""
            elif step.get("step") == 2:
                cic_match = re.search(r"CIC\s*=?\s*(\d+)", step.get("result", ""))
                cic_score = int(cic_match.group(1)) if cic_match else None
            elif step.get("step") == 4:
                dti_match = re.search(r"([\d.]+)%", step.get("result", ""))
                dti_value = float(dti_match.group(1)) if dti_match else None
            elif step.get("step") in (5, 6):
                limit_match = re.search(r"([\d,]+)\s*VND", step.get("result", ""))
                if limit_match:
                    approved_limit = float(limit_match.group(1).replace(",", ""))

        # ── Save to DB ──
        try:
            await assessment_repo.save_assessment({
                "thread_id": thread_id,
                "customer_id": request.customer_id,
                "customer_name": customer_name,
                "loan_amount": request.loan_amount,
                "term_months": request.term_months,
                "decision": final_decision,
                "cic_score": cic_score,
                "dti": dti_value,
                "approved_limit": approved_limit,
                "reasoning_trail": reasoning_trail,
                "report": final_content,
                "needs_human_review": needs_review,
            })
        except Exception as db_err:
            logger.warning(f"Failed to save assessment to DB: {db_err}")

        logger.info("assessment_completed", extra={
            "thread_id": thread_id,
            "customer_id": request.customer_id,
            "decision": final_decision,
            "needs_review": needs_review,
        })

        return AssessmentResponse(
            success=True,
            thread_id=thread_id,
            decision=final_decision,
            report=final_content,
            reasoning_trail=reasoning_trail,
            needs_human_review=needs_review,
        )

    except Exception as e:
        logger.error(f"assessment_error: {e}", exc_info=True)
        return AssessmentResponse(success=False, thread_id=thread_id, error=str(e))


# ── Chat ──

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        # ── Pre-validation: detect customer ID and check existence early ──
        id_match = re.search(r"(?:CCCD|cccd|ID|id)\s*[:\s]*(\d{4,})", request.message)
        if not id_match:
            id_match = re.search(r"\b(\d{4,})\b", request.message)
        if id_match:
            try:
                cust = get_customer_by_id(int(id_match.group(1)))
                if cust is None:
                    return ChatResponse(
                        success=True,
                        thread_id=thread_id,
                        message=f"Khách hàng ID {id_match.group(1)} không tồn tại trong hệ thống. Vui lòng kiểm tra lại số CCCD.",
                    )
            except (ValueError, TypeError):
                pass

        inputs = {"messages": [HumanMessage(content=request.message)]}

        # Capture existing trail length to only return NEW steps from this message
        existing_state = credit_agent.get_state(config)
        trail_offset = len(existing_state.values.get("reasoning_trail", [])) if existing_state.values else 0

        final_content = ""
        reasoning_trail = []

        for state in credit_agent.stream(inputs, config=config, stream_mode="values"):
            last_msg = state["messages"][-1]
            if isinstance(last_msg, AIMessage) and last_msg.content and not last_msg.tool_calls:
                final_content = clean_agent_content(last_msg.content)
            reasoning_trail = state.get("reasoning_trail", [])

        # Only return trail steps added during THIS chat message
        new_trail = reasoning_trail[trail_offset:]

        # If a REAL assessment was performed (has trail AND final_decision), save to DB
        if new_trail:
            final_state = credit_agent.get_state(config)
            final_decision = final_state.values.get("final_decision")
            needs_review = final_state.values.get("needs_human_review", False)

            # Only save when agent reached a final decision (not just a lookup)
            if final_decision:
                # Extract structured data from trail (same logic as /assess)
                customer_name = ""
                customer_id = ""
                cic_score = None
                dti_value = None
                approved_limit = None
                loan_amount = 0.0
                term_months = 0

                for step in new_trail:
                    if step.get("step") == 1:
                        name_match = re.match(r"^([^,]+),", step.get("result", ""))
                        customer_name = name_match.group(1) if name_match else ""
                        id_match = re.search(r"ID\s*[=:]?\s*(\d+)", step.get("detail", ""))
                        if not id_match:
                            id_match = re.search(r"ID\s*[=:]?\s*(\d+)", step.get("result", ""))
                        customer_id = id_match.group(1) if id_match else ""
                    elif step.get("step") == 2:
                        cic_match = re.search(r"CIC\s*=?\s*(\d+)", step.get("result", ""))
                        cic_score = int(cic_match.group(1)) if cic_match else None
                    elif step.get("step") == 4:
                        dti_match = re.search(r"([\d.]+)%", step.get("result", ""))
                        dti_value = float(dti_match.group(1)) if dti_match else None
                    elif step.get("step") in (5, 6):
                        limit_match = re.search(r"([\d,]+)\s*VND", step.get("result", ""))
                        if limit_match:
                            approved_limit = float(limit_match.group(1).replace(",", ""))

                # Extract loan info from message — handle triệu/tỷ/tr multipliers
                amount_match = re.search(
                    r"([\d,.]+)\s*(?:tỷ|triệu|tr(?:iệu)?|VND)",
                    request.message, re.IGNORECASE,
                )
                if amount_match:
                    raw = amount_match.group(1).replace(",", "")
                    unit = amount_match.group(0).lower()
                    try:
                        loan_amount = float(raw)
                        if "tỷ" in unit:
                            loan_amount *= 1_000_000_000
                        elif "tr" in unit or "triệu" in unit:
                            loan_amount *= 1_000_000
                    except ValueError:
                        pass
                term_match = re.search(r"(\d+)\s*tháng", request.message)
                if term_match:
                    term_months = int(term_match.group(1))

                try:
                    await assessment_repo.save_assessment({
                        "thread_id": thread_id,
                        "customer_id": customer_id,
                        "customer_name": customer_name,
                        "loan_amount": loan_amount,
                        "term_months": term_months,
                        "decision": final_decision,
                        "cic_score": cic_score,
                        "dti": dti_value,
                        "approved_limit": approved_limit,
                        "reasoning_trail": new_trail,
                        "report": final_content,
                        "needs_human_review": needs_review,
                    })
                except Exception as db_err:
                    logger.warning(f"Failed to save chat assessment to DB: {db_err}")

        return ChatResponse(
            success=True,
            thread_id=thread_id,
            message=final_content,
            reasoning_trail=new_trail,
        )

    except Exception as e:
        logger.error(f"chat_error: {e}", exc_info=True)
        return ChatResponse(success=False, thread_id=thread_id, message="", error=str(e))


# ── Human Review ──

@app.post("/api/v1/review", response_model=AssessmentResponse)
async def submit_review(request: HumanReviewRequest):
    config = {"configurable": {"thread_id": request.thread_id}}

    try:
        current_state = credit_agent.get_state(config)

        if not current_state or not current_state.values:
            raise HTTPException(status_code=404, detail="Thread not found")

        if not current_state.values.get("needs_human_review"):
            raise HTTPException(status_code=400, detail="Thread does not need review")

        # Resume với human decision
        credit_agent.update_state(
            config,
            {
                "human_decision": request.decision,
                "human_note": request.reviewer_note,
            },
            as_node="human_review",
        )

        # Resume execution
        result = credit_agent.invoke(None, config=config)

        final_state = credit_agent.get_state(config)
        reasoning_trail = final_state.values.get("reasoning_trail", [])

        logger.info("human_review_completed", extra={
            "thread_id": request.thread_id,
            "decision": request.decision,
            "note": request.reviewer_note,
        })

        return AssessmentResponse(
            success=True,
            thread_id=request.thread_id,
            decision=request.decision,
            report=f"Human reviewer quyết định: {request.decision}. Ghi chú: {request.reviewer_note}",
            reasoning_trail=reasoning_trail,
            needs_human_review=False,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"review_error: {e}", exc_info=True)
        return AssessmentResponse(success=False, thread_id=request.thread_id, error=str(e))


# ── Customer Endpoints ──

@app.get("/api/v1/customers")
async def get_customers():
    try:
        customers = list_all_customers(limit=20)
        total = get_total_customer_count()
        return {"success": True, "data": {"total": total, "showing": len(customers), "customers": customers}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/v1/customers/{customer_id}")
async def get_customer(customer_id: int):
    customer = get_customer_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"success": True, "data": customer}


# ── Policy Endpoint ──

@app.get("/api/v1/policy")
async def get_policy():
    return {
        "success": True,
        "data": {
            "readable": CreditPolicy.get_readable_policy(),
            "thresholds": {
                "age": [CreditPolicy.AGE_MIN, CreditPolicy.AGE_MAX],
                "cic_reject": CreditPolicy.CIC_AUTO_REJECT,
                "dti_pass": CreditPolicy.DTI_PASS,
                "dti_review": CreditPolicy.DTI_REVIEW,
                "cic_tiers": CreditPolicy.CIC_TIERS,
            }
        }
    }


# ════════════════════════════════════════════
# DASHBOARD ENDPOINTS
# ════════════════════════════════════════════

@app.get("/api/v1/dashboard/stats")
async def dashboard_stats(
    date_from: date = Query(None, alias="from"),
    date_to: date = Query(None, alias="to"),
):
    """Thống kê thẩm định theo khoảng thời gian."""
    try:
        stats = await assessment_repo.get_stats(date_from, date_to)
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"dashboard_stats_error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@app.get("/api/v1/dashboard/assessments")
async def dashboard_assessments(
    date_from: date = Query(None, alias="from"),
    date_to: date = Query(None, alias="to"),
    decision: str = Query(None),
    search: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Danh sách assessments với filter + phân trang."""
    try:
        result = await assessment_repo.list_assessments(
            date_from=date_from,
            date_to=date_to,
            decision=decision,
            search=search,
            page=page,
            page_size=page_size,
        )
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"dashboard_assessments_error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@app.get("/api/v1/dashboard/assessments/{assessment_id}")
async def get_assessment_detail(assessment_id: str):
    """Chi tiết 1 assessment (bao gồm reasoning trail).
    Hỗ trợ tra cứu theo DB id (số) hoặc thread_id (chuỗi UUID).
    """
    if assessment_id.isdigit():
        result = await assessment_repo.get_assessment_by_id(int(assessment_id))
    else:
        result = await assessment_repo.get_assessment_by_thread_id(assessment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {"success": True, "data": result}

