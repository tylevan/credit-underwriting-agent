import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Slider } from "@/components/ui/slider";
import { Button } from "@/components/ui/button";
import { ClipboardCheck, Info, Search } from "lucide-react";

/**
 * Định dạng số thành tiền tệ VNĐ
 */
function formatCurrencyLocal(amount: number): string {
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0
  }).format(amount)
}

interface LoanFormProps {
  onSubmit: (data: { id: string; amount: number; term: number }) => void;
  isLoading?: boolean;
}

export function LoanForm({ onSubmit, isLoading }: LoanFormProps) {
  const [formData, setFormData] = useState({
    id: "",
    amount: 100000000,
    term: 24
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  return (
    <Card className="border border-slate-200 shadow-sm bg-white rounded-2xl overflow-hidden">
      <div className="bg-slate-50/50 p-6 border-b border-slate-100">
        <div className="flex items-center gap-3 mb-1">
          <div className="bg-primary/10 p-2 rounded-xl">
            <Search className="w-5 h-5 text-primary" />
          </div>
          <h2 className="text-xl font-bold text-slate-900">Thẩm định nhanh</h2>
        </div>
        <p className="text-xs font-medium text-slate-500 leading-relaxed">
          Nhập thông tin chi tiết để hệ thống phân tích.
        </p>
      </div>

      <div className="p-6">
        <form onSubmit={handleSubmit} className="space-y-8">
          <div className="space-y-3">
            <Label htmlFor="customer-id" className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">ID Khách hàng</Label>
            <div className="relative group">
              <Input
                id="customer-id"
                placeholder="Nhập số CCCD khách hàng"
                value={formData.id}
                onChange={(e) => setFormData({ ...formData, id: e.target.value })}
                className="h-12 bg-slate-50 border-slate-200 focus:ring-primary/10 rounded-xl font-medium text-base text-slate-600"
                required
              />
              <div className="absolute right-3 top-3.5">
                <Info className="w-5 h-5 text-slate-300 group-focus-within:text-primary/40 transition-colors" />
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="flex justify-between items-end">
              <Label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">Số tiền đề nghị</Label>
              <span className="text-xl font-black text-primary tracking-tight">{formatCurrencyLocal(formData.amount)}</span>
            </div>
            <div className="px-1">
              <Slider
                value={[formData.amount]}
                min={10000000}
                max={500000000}
                step={5000000}
                onValueChange={([val]) => setFormData({ ...formData, amount: val })}
                className="py-2"
              />
              <div className="flex justify-between text-[9px] font-black text-slate-300 uppercase tracking-widest mt-1">
                <span>10 Tr</span>
                <span>500 Tr</span>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="flex justify-between items-end">
              <Label className="text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400">Thời hạn vay</Label>
              <span className="text-xl font-black text-primary tracking-tight">{formData.term} tháng</span>
            </div>
            <div className="px-1">
              <Slider
                value={[formData.term]}
                min={6}
                max={60}
                step={6}
                onValueChange={([val]) => setFormData({ ...formData, term: val })}
                className="py-2"
              />
              <div className="flex justify-between text-[9px] font-black text-slate-300 uppercase tracking-widest mt-1">
                <span>6 Th</span>
                <span>60 Th</span>
              </div>
            </div>
          </div>

          <Button type="submit" disabled={isLoading} className="w-full h-14 text-base font-bold rounded-xl shadow-xl shadow-primary/20 hover:shadow-primary/30 hover:-translate-y-0.5 transition-all active:scale-[0.98] active:translate-y-0">
            {isLoading ? "⏳ Đang thẩm định..." : "Gửi yêu cầu thẩm định"}
          </Button>
        </form>
      </div>
    </Card>
  );
}
