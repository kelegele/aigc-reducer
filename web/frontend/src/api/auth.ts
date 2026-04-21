// web/frontend/src/api/auth.ts
import client from "./client";

export interface UserResponse {
  id: number;
  phone: string;
  nickname: string;
  avatar_url: string | null;
  is_active: boolean;
  credit_balance: number;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: UserResponse;
}

export async function sendSms(phone: string): Promise<void> {
  await client.post("/auth/sms/send", { phone });
}

export async function loginByPhone(
  phone: string,
  code: string
): Promise<LoginResponse> {
  const resp = await client.post<LoginResponse>("/auth/login/phone", {
    phone,
    code,
  });
  return resp.data;
}

export async function refreshToken(
  refresh_token: string
): Promise<{ access_token: string }> {
  const resp = await client.post("/auth/refresh", { refresh_token });
  return resp.data;
}

export async function getMe(): Promise<UserResponse> {
  const resp = await client.get<UserResponse>("/auth/me");
  return resp.data;
}
