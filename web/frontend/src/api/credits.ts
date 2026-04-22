// web/frontend/src/api/credits.ts
import client from "./client";

// --- Types ---

export interface PackageResponse {
  id: number;
  name: string;
  price_cents: number;
  credits: number;
  bonus_credits: number;
}

export interface BalanceResponse {
  balance: number;
  total_recharged: number;
  total_consumed: number;
}

export interface RechargeRequest {
  package_id: number;
  pay_method: "pc_web" | "h5";
}

export interface RechargeResponse {
  order_id: number;
  pay_url: string;
}

export interface OrderResponse {
  id: number;
  out_trade_no: string;
  amount_cents: number;
  credits_granted: number;
  status: string;
  pay_method: string;
  created_at: string;
  paid_at: string | null;
}

export interface TransactionResponse {
  id: number;
  type: string;
  amount: number;
  balance_after: number;
  remark: string | null;
  created_at: string;
}

export interface TransactionListResponse {
  items: TransactionResponse[];
  total: number;
  page: number;
  size: number;
}

// --- API Functions ---

export async function getPackages(): Promise<PackageResponse[]> {
  const resp = await client.get<PackageResponse[]>("/credits/packages");
  return resp.data;
}

export async function getBalance(): Promise<BalanceResponse> {
  const resp = await client.get<BalanceResponse>("/credits/balance");
  return resp.data;
}

export async function createRecharge(
  req: RechargeRequest
): Promise<RechargeResponse> {
  const resp = await client.post<RechargeResponse>("/credits/recharge", req);
  return resp.data;
}

export async function getOrder(orderId: number): Promise<OrderResponse> {
  const resp = await client.get<OrderResponse>(`/credits/orders/${orderId}`);
  return resp.data;
}

export async function getTransactions(params?: {
  type?: string;
  page?: number;
  size?: number;
}): Promise<TransactionListResponse> {
  const resp = await client.get<TransactionListResponse>(
    "/credits/transactions",
    { params }
  );
  return resp.data;
}
