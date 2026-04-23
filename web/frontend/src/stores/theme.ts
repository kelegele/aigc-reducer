// web/frontend/src/stores/theme.ts
import { create } from "zustand";

function applyThemeBg(isDark: boolean) {
  document.documentElement.style.backgroundColor = isDark ? "#050507" : "#f5f5f5";
}

interface ThemeState {
  isDark: boolean;
  toggle: () => void;
}

export const useThemeStore = create<ThemeState>((set) => {
  const initial = localStorage.getItem("theme") !== "light";
  applyThemeBg(initial);

  return {
    isDark: initial,
    toggle: () =>
      set((state) => {
        const next = !state.isDark;
        localStorage.setItem("theme", next ? "dark" : "light");
        applyThemeBg(next);
        return { isDark: next };
      }),
  };
});
