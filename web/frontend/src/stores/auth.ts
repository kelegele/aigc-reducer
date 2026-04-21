// web/frontend/src/stores/auth.ts
import { create } from "zustand";
import {
  getMe,
  loginByPhone,
  sendSms,
  type LoginResponse,
  type UserResponse,
} from "../api/auth";

interface AuthState {
  user: UserResponse | null;
  loading: boolean;
  sendSms: (phone: string) => Promise<void>;
  login: (phone: string, code: string) => Promise<void>;
  fetchUser: () => Promise<void>;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,

  sendSms: async (phone: string) => {
    await sendSms(phone);
  },

  login: async (phone: string, code: string) => {
    set({ loading: true });
    try {
      const resp: LoginResponse = await loginByPhone(phone, code);
      localStorage.setItem("access_token", resp.access_token);
      localStorage.setItem("refresh_token", resp.refresh_token);
      set({ user: resp.user, loading: false });
    } catch {
      set({ loading: false });
      throw new Error("登录失败");
    }
  },

  fetchUser: async () => {
    try {
      const user = await getMe();
      set({ user });
    } catch {
      set({ user: null });
    }
  },

  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({ user: null });
  },
}));
