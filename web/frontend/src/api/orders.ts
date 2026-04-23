// web/frontend/src/api/orders.ts
import client from "./client";

// --- Types ---

export interface OrderListItem {
  id: number;
  out_trade_no: string;
  amount_cents: number;
  credits_granted: number;
  status: string;
  pay_method: string;
  created_at: string;
  paid_at: string | null;
}

export interface OrderDetail extends OrderListItem {
  credit_transaction_trade_no: string | null;
  package_name: string;
}

export interface AdminOrderDetail extends OrderDetail {
  user_id: number;
  user_phone: string;
  user_nickname: string;
}

export interface OrderListResponse {
  items: OrderListItem[];
  total: number;
  page: number;
  size: number;
}

export interface AdminOrderListResponse {
  items: AdminOrderDetail[];
  total: number;
  page: number;
  size: number;
}

// --- API Functions ---

export async function getOrders(params?: {
  status?: string;
  page?: number;
  size?: number;
}): Promise<OrderListResponse> {
  const resp = await client.get<OrderListResponse>("/credits/orders", {
    params,
  });
  return resp.data;
}

export async function getOrderDetail(
  orderId: number
): Promise<OrderDetail> {
  const resp = await client.get<OrderDetail>(
    `/credits/orders/${orderId}/detail`
  );
  return resp.data;
}

export interface RepayResponse {
  pay_url: string;
}

export async function repayOrder(orderId: number): Promise<RepayResponse> {
  const resp = await client.post<RepayResponse>(`/credits/orders/${orderId}/repay`);
  return resp.data;
}

export async function getAdminOrders(params?: {
  search?: string;
  status?: string;
  page?: number;
  size?: number;
}): Promise<AdminOrderListResponse> {
  const resp = await client.get<AdminOrderListResponse>("/admin/orders", {
    params,
  });
  return resp.data;
}

export async function getAdminOrderDetail(
  orderId: number
): Promise<AdminOrderDetail> {
  const resp = await client.get<AdminOrderDetail>(
    `/admin/orders/${orderId}`
  );
  return resp.data;
}
