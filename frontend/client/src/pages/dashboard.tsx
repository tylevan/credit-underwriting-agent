/**
 * Admin Dashboard — Quản lý Thẩm định
 * Trang riêng cho quản lý / người có phân quyền.
 */
import { useState, useEffect, useCallback } from "react";
import { useLocation } from "wouter";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
    FileText,
    CheckCircle2,
    XCircle,
    AlertTriangle,
    Search,
    ChevronRight,
    Calendar,
    LayoutDashboard,
    Zap,
    TrendingUp,
    TrendingDown,
    ChevronLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/lib/api";

/* ═══════════════════════════════════════
   Types
   ═══════════════════════════════════════ */

interface Stats {
    total: number;
    approved: number;
    rejected: number;
    review: number;
    approved_pct: number;
    rejected_pct: number;
    review_pct: number;
}

interface AssessmentItem {
    id: number;
    thread_id: string;
    customer_id: string;
    customer_name: string;
    loan_amount: number;
    term_months: number;
    decision: string;
    cic_score: number | null;
    dti: number | null;
    approved_limit: number | null;
    reasoning_trail: unknown[];
    needs_human_review: boolean;
    created_at: string;
}

interface DatePreset {
    label: string;
    getValue: () => { from: string; to: string };
}

/* ═══════════════════════════════════════
   Helpers
   ═══════════════════════════════════════ */

function formatCurrency(n: number): string {
    return new Intl.NumberFormat("vi-VN").format(n) + " ₫";
}

function formatDateTime(iso: string): string {
    const d = new Date(iso);
    const dd = d.getDate().toString().padStart(2, "0");
    const mm = (d.getMonth() + 1).toString().padStart(2, "0");
    const yyyy = d.getFullYear();
    const h = d.getHours().toString().padStart(2, "0");
    const m = d.getMinutes().toString().padStart(2, "0");
    return `${dd}/${mm}/${yyyy} ${h}:${m}`;
}

function shortSessionId(threadId: string): string {
    return threadId.slice(0, 8).toUpperCase();
}

function toISODate(d: Date): string {
    return d.toISOString().split("T")[0];
}

function getDatePresets(): DatePreset[] {
    const today = new Date();
    return [
        {
            label: `Hôm nay, ${today.getDate()} Tháng ${today.getMonth() + 1}`,
            getValue: () => ({ from: toISODate(today), to: toISODate(today) }),
        },
        {
            label: "7 ngày qua",
            getValue: () => {
                const from = new Date(today);
                from.setDate(from.getDate() - 7);
                return { from: toISODate(from), to: toISODate(today) };
            },
        },
        {
            label: "30 ngày qua",
            getValue: () => {
                const from = new Date(today);
                from.setDate(from.getDate() - 30);
                return { from: toISODate(from), to: toISODate(today) };
            },
        },
        {
            label: "Tất cả",
            getValue: () => ({ from: "", to: "" }),
        },
    ];
}

/* ═══════════════════════════════════════
   Decision Badge
   ═══════════════════════════════════════ */

function DecisionBadge({ decision }: { decision: string }) {
    const config: Record<string, { icon: React.ReactNode; text: string; cls: string }> = {
        APPROVED: { icon: <CheckCircle2 className="w-3 h-3" />, text: "Phê duyệt", cls: "bg-emerald-50 text-emerald-700 border-emerald-200" },
        REJECTED: { icon: <XCircle className="w-3 h-3" />, text: "Từ chối", cls: "bg-red-50 text-red-700 border-red-200" },
        REVIEW: { icon: <AlertTriangle className="w-3 h-3" />, text: "Xem xét", cls: "bg-amber-50 text-amber-700 border-amber-200" },
    };
    const c = config[decision] || config.REVIEW;
    return (
        <span className={cn("inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold border", c.cls)}>
            {c.icon} {c.text}
        </span>
    );
}

/* ═══════════════════════════════════════
   Main Component
   ═══════════════════════════════════════ */

export default function Dashboard() {
    const [, setLocation] = useLocation();
    const [stats, setStats] = useState<Stats | null>(null);
    const [assessments, setAssessments] = useState<AssessmentItem[]>([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [search, setSearch] = useState("");
    const [datePresetIdx, setDatePresetIdx] = useState(0);
    const [showDatePicker, setShowDatePicker] = useState(false);
    const [loading, setLoading] = useState(true);

    const presets = getDatePresets();
    const currentPreset = presets[datePresetIdx];
    const dateRange = currentPreset.getValue();

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const params = new URLSearchParams();
            if (dateRange.from) params.set("from", dateRange.from);
            if (dateRange.to) params.set("to", dateRange.to);
            if (search) params.set("search", search);
            params.set("page", page.toString());
            params.set("page_size", "10");

            const [statsRes, assessmentsRes] = await Promise.all([
                fetch(`${API_BASE}/dashboard/stats?${new URLSearchParams(
                    dateRange.from ? { from: dateRange.from, to: dateRange.to } : {}
                )}`),
                fetch(`${API_BASE}/dashboard/assessments?${params}`),
            ]);

            const statsData = await statsRes.json();
            const assessmentsData = await assessmentsRes.json();

            if (statsData.success) setStats(statsData.data);
            if (assessmentsData.success) {
                setAssessments(assessmentsData.data.items);
                setTotal(assessmentsData.data.total);
            }
        } catch (err) {
            console.error("Dashboard fetch error:", err);
        } finally {
            setLoading(false);
        }
    }, [dateRange.from, dateRange.to, search, page]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleViewTrail = (item: AssessmentItem) => {
        setLocation(`/trail/${item.thread_id}`);
    };

    const totalPages = Math.ceil(total / 10);

    return (
        <div className="flex h-screen bg-slate-50">
            {/* ══ Sidebar ══ */}
            <aside className="w-56 bg-slate-900 text-white flex flex-col">
                <div className="p-5 border-b border-slate-700">
                    <div>
                        <h1 className="text-2xl font-black text-blue-400 tracking-tight">FinSafe <span className="text-slate-400 font-light">Core</span></h1>
                        <p className="text-[11px] font-bold text-slate-500 uppercase tracking-[0.2em] mt-1">Hệ thống thẩm định nội bộ</p>
                    </div>
                </div>

                <nav className="flex-1 p-3 space-y-1">
                    <button className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg bg-slate-800 text-white text-sm font-medium">
                        <LayoutDashboard className="w-4 h-4" /> Tổng quan
                    </button>
                    <button
                        onClick={() => setLocation("/")}
                        className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors text-sm"
                    >
                        <Zap className="w-4 h-4" /> Hệ thống Thẩm định
                    </button>
                </nav>

                <div className="p-4 border-t border-slate-700">
                    <p className="text-[10px] text-slate-500 uppercase">Phiên bản</p>
                    <p className="text-xs text-slate-300 font-semibold">Admin Panel v1.0</p>
                </div>
            </aside>

            {/* ══ Main Content ══ */}
            <main className="flex-1 overflow-y-auto">
                {/* Header */}
                <div className="px-8 pt-8 pb-4 flex items-start justify-between">
                    <div>
                        <h1 className="text-2xl font-bold text-slate-800">Quản lý Thẩm định</h1>
                        <p className="text-sm text-slate-500 mt-1">Theo dõi hiệu suất và lịch sử quyết định của hệ thống AI</p>
                    </div>

                    {/* Date Picker */}
                    <div className="relative">
                        <button
                            onClick={() => setShowDatePicker(!showDatePicker)}
                            className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm text-slate-700 hover:border-slate-300 transition-colors shadow-sm"
                        >
                            <Calendar className="w-4 h-4 text-slate-400" />
                            {currentPreset.label}
                        </button>

                        {showDatePicker && (
                            <>
                                <div className="fixed inset-0 z-10" onClick={() => setShowDatePicker(false)} />
                                <div className="absolute right-0 top-12 z-20 bg-white border border-slate-200 rounded-xl shadow-lg p-2 min-w-[200px]">
                                    {presets.map((preset, idx) => (
                                        <button
                                            key={idx}
                                            onClick={() => { setDatePresetIdx(idx); setShowDatePicker(false); setPage(1); }}
                                            className={cn(
                                                "w-full text-left px-3 py-2 rounded-lg text-sm transition-colors",
                                                idx === datePresetIdx
                                                    ? "bg-blue-50 text-blue-700 font-medium"
                                                    : "text-slate-600 hover:bg-slate-50"
                                            )}
                                        >
                                            {preset.label}
                                        </button>
                                    ))}
                                </div>
                            </>
                        )}
                    </div>
                </div>

                {/* Stats Cards */}
                <div className="px-8 grid grid-cols-4 gap-4 mb-8">
                    <StatsCard
                        icon={<FileText className="w-5 h-5 text-blue-600" />}
                        iconBg="bg-blue-50"
                        label="TỔNG HỒ SƠ"
                        value={stats?.total ?? 0}
                        loading={loading}
                    />
                    <StatsCard
                        icon={<CheckCircle2 className="w-5 h-5 text-emerald-600" />}
                        iconBg="bg-emerald-50"
                        label="PHÊ DUYỆT"
                        value={stats?.approved ?? 0}
                        pct={stats?.approved_pct}
                        trend="up"
                        loading={loading}
                    />
                    <StatsCard
                        icon={<XCircle className="w-5 h-5 text-red-500" />}
                        iconBg="bg-red-50"
                        label="TỪ CHỐI"
                        value={stats?.rejected ?? 0}
                        pct={stats?.rejected_pct}
                        trend="down"
                        loading={loading}
                    />
                    <StatsCard
                        icon={<AlertTriangle className="w-5 h-5 text-amber-500" />}
                        iconBg="bg-amber-50"
                        label="ĐANG XEM XÉT"
                        value={stats?.review ?? 0}
                        pct={stats?.review_pct}
                        loading={loading}
                    />
                </div>

                {/* Assessment Table */}
                <div className="px-8 pb-8">
                    <Card className="overflow-hidden border-slate-200">
                        {/* Table Header */}
                        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
                            <h3 className="font-bold text-slate-800">Chi tiết Log Thẩm định</h3>
                            <div className="relative w-64">
                                <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                                <Input
                                    placeholder="Tìm kiếm ID, tên khách hàng..."
                                    value={search}
                                    onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                                    className="pl-9 h-9 text-sm"
                                />
                            </div>
                        </div>

                        {/* Table */}
                        <div className="overflow-x-auto">
                            <table className="w-full">
                                <thead>
                                    <tr className="border-b border-slate-100">
                                        <th className="text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest px-5 py-3">Thời gian</th>
                                        <th className="text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest px-5 py-3">Session ID</th>
                                        <th className="text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest px-5 py-3">Nhân viên</th>
                                        <th className="text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest px-5 py-3">Khách hàng</th>
                                        <th className="text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest px-5 py-3">Số tiền vay</th>
                                        <th className="text-left text-[11px] font-bold text-slate-400 uppercase tracking-widest px-5 py-3">Kết quả</th>
                                        <th className="text-right text-[11px] font-bold text-slate-400 uppercase tracking-widest px-5 py-3">Chi tiết</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {loading ? (
                                        Array.from({ length: 5 }).map((_, i) => (
                                            <tr key={i} className="border-b border-slate-50">
                                                <td className="px-5 py-4" colSpan={7}>
                                                    <div className="h-4 bg-slate-100 rounded animate-pulse w-full" />
                                                </td>
                                            </tr>
                                        ))
                                    ) : assessments.length === 0 ? (
                                        <tr>
                                            <td colSpan={7} className="text-center py-12 text-slate-400 text-sm">
                                                Chưa có dữ liệu thẩm định
                                            </td>
                                        </tr>
                                    ) : (
                                        assessments.map((item) => (
                                            <tr key={item.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                                                <td className="px-5 py-4">
                                                    <p className="text-sm text-slate-800 font-medium whitespace-nowrap">{formatDateTime(item.created_at)}</p>
                                                </td>
                                                <td className="px-5 py-4">
                                                    <code className="text-xs bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded font-mono">{shortSessionId(item.thread_id)}</code>
                                                </td>
                                                <td className="px-5 py-4">
                                                    <p className="text-sm text-slate-600">AI System</p>
                                                </td>
                                                <td className="px-5 py-4">
                                                    <p className="font-semibold text-slate-800 text-sm">{item.customer_name || `KH #${item.customer_id}`}</p>
                                                    <p className="text-xs text-slate-400">ID: {item.customer_id}</p>
                                                </td>
                                                <td className="px-5 py-4">
                                                    <p className="text-sm font-medium text-blue-600 whitespace-nowrap">{formatCurrency(item.loan_amount)}</p>
                                                </td>
                                                <td className="px-5 py-4">
                                                    <DecisionBadge decision={item.decision} />
                                                </td>
                                                <td className="px-5 py-4 text-right">
                                                    <button
                                                        onClick={() => handleViewTrail(item)}
                                                        className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors"
                                                    >
                                                        LUỒNG QUYẾT ĐỊNH <ChevronRight className="w-3 h-3" />
                                                    </button>
                                                </td>
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        </div>

                        {/* Pagination */}
                        {totalPages > 1 && (
                            <div className="p-4 border-t border-slate-100 flex items-center justify-between">
                                <p className="text-xs text-slate-400">
                                    Hiển thị {assessments.length} / {total} hồ sơ
                                </p>
                                <div className="flex items-center gap-1">
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        disabled={page <= 1}
                                        onClick={() => setPage(p => p - 1)}
                                    >
                                        <ChevronLeft className="w-4 h-4" />
                                    </Button>
                                    <span className="text-xs text-slate-600 px-2">
                                        Trang {page} / {totalPages}
                                    </span>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        disabled={page >= totalPages}
                                        onClick={() => setPage(p => p + 1)}
                                    >
                                        <ChevronRight className="w-4 h-4" />
                                    </Button>
                                </div>
                            </div>
                        )}

                        {/* Footer */}
                        {!loading && total > 0 && (
                            <div className="p-3 border-t border-slate-100 text-center">
                                <button className="text-xs text-slate-400 hover:text-slate-600 transition-colors flex items-center gap-1 mx-auto">
                                    Xem tất cả hồ sơ <ChevronRight className="w-3 h-3" />
                                </button>
                            </div>
                        )}
                    </Card>
                </div>
            </main>
        </div>
    );
}

/* ═══════════════════════════════════════
   Stats Card Component
   ═══════════════════════════════════════ */

function StatsCard({
    icon,
    iconBg,
    label,
    value,
    pct,
    trend,
    loading,
}: {
    icon: React.ReactNode;
    iconBg: string;
    label: string;
    value: number;
    pct?: number;
    trend?: "up" | "down";
    loading: boolean;
}) {
    return (
        <Card className="p-5 border-slate-200 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
                <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center", iconBg)}>
                    {icon}
                </div>
                {pct != null && (
                    <div className={cn(
                        "flex items-center gap-0.5 text-xs font-semibold",
                        trend === "up" ? "text-emerald-600" : trend === "down" ? "text-red-500" : "text-slate-400"
                    )}>
                        {trend === "up" ? <TrendingUp className="w-3 h-3" /> : trend === "down" ? <TrendingDown className="w-3 h-3" /> : null}
                        {pct}%
                    </div>
                )}
            </div>
            <p className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mt-4">{label}</p>
            {loading ? (
                <div className="h-8 bg-slate-100 rounded animate-pulse mt-1 w-20" />
            ) : (
                <p className="text-3xl font-black text-slate-800 mt-1">{value.toLocaleString()}</p>
            )}
        </Card>
    );
}
