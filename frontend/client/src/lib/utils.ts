import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Định dạng số thành tiền tệ VNĐ
 */
export function formatCurrency(amount: number): string {
  return `${Math.round(amount).toLocaleString("en-US")} VND`
}
