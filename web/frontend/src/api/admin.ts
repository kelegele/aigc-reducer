// web/frontend/src/api/admin.ts
import client from "./client";

// --- Types ---

export interface AdminPackageResponse {
  id: number;
  name: string;
  price_cents: number;
  credits: number;
  bonus_credits: number;
  sort_order: number;
  is_active: boolean;
  created_at: string;
}

export interface PackageCreateRequest {
  name: string;
  price_cents: number;
  credits: number;
  bonus_credits?: number;
  sort_order?: number;
  is_active?: boolean;
}

export interface PackageUpdateRequest {
  name?: string;
  price_cents?: number;
  credits?: number;
  bonus_credits?: number;
  sort_order?: number;
  is_active?: boolean;
}

export interface AdminUserResponse {
  id: number;
  phone: string;
  nickname: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
  credit_balance: number;
  total_recharged: number;
  total_consumed: number;
  total_recharge_cents: number;
}

export interface UserListResponse {
  items: AdminUserResponse[];
  total: number;
  page: number;
  size: number;
}

export interface TopUserEntry {
  user_id: number;
  nickname: string;
  phone: string;
  amount: number;
}

export interface DashboardResponse {
  total_users: number;
  total_revenue_cents: number;
  total_credits_granted: number;
  total_credits_consumed: number;
  today_new_users: number;
  total_detections: number;
  today_detections: number;
  top_recharge_users: TopUserEntry[];
  top_consume_users: TopUserEntry[];
}

export interface ConfigResponse {
  credits_per_1k_tokens: number;
  new_user_bonus_credits: number;
}

// --- API Functions ---

export async function getDashboard(): Promise<DashboardResponse> {
  const resp = await client.get<DashboardResponse>("/admin/dashboard");
  return resp.data;
}

export async function listAllPackages(): Promise<AdminPackageResponse[]> {
  const resp = await client.get<AdminPackageResponse[]>("/admin/packages");
  return resp.data;
}

export async function createPackage(req: PackageCreateRequest): Promise<AdminPackageResponse> {
  const resp = await client.post<AdminPackageResponse>("/admin/packages", req);
  return resp.data;
}

export async function updatePackage(
  id: number, req: PackageUpdateRequest
): Promise<AdminPackageResponse> {
  const resp = await client.put<AdminPackageResponse>(`/admin/packages/${id}`, req);
  return resp.data;
}

export async function deletePackage(id: number): Promise<void> {
  await client.delete(`/admin/packages/${id}`);
}

export async function listUsers(params?: {
  search?: string;
  page?: number;
  size?: number;
}): Promise<UserListResponse> {
  const resp = await client.get<UserListResponse>("/admin/users", { params });
  return resp.data;
}

export async function adjustCredits(
  userId: number, amount: number, remark: string
): Promise<void> {
  await client.put(`/admin/users/${userId}/credits`, { amount, remark });
}

export async function setUserStatus(
  userId: number, isActive: boolean
): Promise<void> {
  await client.put(`/admin/users/${userId}/status`, { is_active: isActive });
}

export async function getConfig(): Promise<ConfigResponse> {
  const resp = await client.get<ConfigResponse>("/admin/config");
  return resp.data;
}

export async function updateConfig(req: {
  credits_per_1k_tokens?: number;
  new_user_bonus_credits?: number;
}): Promise<ConfigResponse> {
  const resp = await client.put<ConfigResponse>("/admin/config", req);
  return resp.data;
}

// --- 流水管理 ---

export interface AdminTransactionResponse {
  id: number;
  trade_no: string;
  user_id: number;
  user_phone: string;
  user_nickname: string;
  type: string;
  amount: number;
  balance_after: number;
  ref_type: string | null;
  ref_id: number | null;
  remark: string | null;
  created_at: string;
}

export interface AdminTransactionListResponse {
  items: AdminTransactionResponse[];
  total: number;
  page: number;
  size: number;
}

// --- 内容管理（检测记录） ---

import type { TaskResponse } from "./reduce";

export interface AdminTaskResponse {
  id: string;
  user_id: number;
  user_phone: string;
  user_nickname: string;
  title: string;
  status: string;
  detect_mode: string;
  style: string;
  full_reconstruct: boolean;
  total_credits: number;
  paragraph_count: number;
  created_at: string;
  completed_at: string | null;
}

export interface AdminTaskListResponse {
  items: AdminTaskResponse[];
  total: number;
  page: number;
  size: number;
}

export async function listAdminTasks(params?: {
  status?: string;
  search?: string;
  page?: number;
  size?: number;
}): Promise<AdminTaskListResponse> {
  const resp = await client.get<AdminTaskListResponse>("/admin/tasks", { params });
  return resp.data;
}

/** 管理员查看任意任务详情。 */
export async function getAdminTask(taskId: string): Promise<TaskResponse> {
  const resp = await client.get<TaskResponse>(`/admin/tasks/${taskId}`);
  return resp.data;
}

// --- 流水管理 ---

export async function listAdminTransactions(params?: {
  user_id?: number;
  type?: string;
  search?: string;
  page?: number;
  size?: number;
}): Promise<AdminTransactionListResponse> {
  const resp = await client.get<AdminTransactionListResponse>("/admin/transactions", { params });
  return resp.data;
}
