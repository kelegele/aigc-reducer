// web/frontend/src/stores/credits.ts
import { create } from "zustand";
import {
  getBalance,
  getPackages,
  getTransactions,
  type BalanceResponse,
  type PackageResponse,
  type TransactionListResponse,
} from "../api/credits";

interface CreditsState {
  balance: BalanceResponse | null;
  packages: PackageResponse[];
  transactions: TransactionListResponse | null;
  loading: boolean;
  fetchBalance: () => Promise<void>;
  fetchPackages: () => Promise<void>;
  fetchTransactions: (params?: {
    type?: string;
    page?: number;
    size?: number;
  }) => Promise<void>;
}

export const useCreditsStore = create<CreditsState>((set) => ({
  balance: null,
  packages: [],
  transactions: null,
  loading: false,

  fetchBalance: async () => {
    const balance = await getBalance();
    set({ balance });
  },

  fetchPackages: async () => {
    const packages = await getPackages();
    set({ packages });
  },

  fetchTransactions: async (params) => {
    set({ loading: true });
    try {
      const transactions = await getTransactions(params);
      set({ transactions, loading: false });
    } catch {
      set({ loading: false });
    }
  },
}));
