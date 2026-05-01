// web/frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { App as AntApp, ConfigProvider, theme } from "antd";
import zhCN from "antd/locale/zh_CN";
import Login from "./pages/Login";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import Credits from "./pages/Credits";
import History from "./pages/History";
import Settings from "./pages/Settings";
import NewTask from "./pages/reduce/NewTask";
import TaskWorkspace from "./pages/reduce/TaskWorkspace";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminPackages from "./pages/admin/AdminPackages";
import AdminOrders from "./pages/admin/AdminOrders";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminTransactions from "./pages/admin/AdminTransactions";
import AdminConfig from "./pages/admin/AdminConfig";
import MockPay from "./pages/MockPay";
import AppLayout from "./components/AppLayout";
import ProtectedRoute from "./components/ProtectedRoute";
import { useThemeStore } from "./stores/theme";

const darkTokens = {
  colorPrimary: "#00d992",
  colorBgContainer: "#141414",
  colorBgLayout: "#050507",
  colorBgElevated: "#1a1a1a",
  colorBorder: "#3d3a39",
  colorBorderSecondary: "#2a2a2a",
  colorText: "#f2f2f2",
  colorTextSecondary: "#c8c4c0",
  colorTextTertiary: "#9a9590",
  colorLink: "#00d992",
  colorLinkHover: "#2fd6a1",
  colorLinkActive: "#00b377",
};

const lightTokens = {
  colorPrimary: "#00b377",
  colorBgContainer: "#ffffff",
  colorBgLayout: "#f5f5f5",
  colorBgElevated: "#ffffff",
  colorBorder: "#e0e0e0",
  colorBorderSecondary: "#eeeeee",
  colorText: "#1a1a1a",
  colorTextSecondary: "#555555",
  colorTextTertiary: "#888888",
  colorLink: "#00b377",
  colorLinkHover: "#00d992",
  colorLinkActive: "#009966",
};

export default function App() {
  const isDark = useThemeStore((s) => s.isDark);

  return (
    <ConfigProvider
      prefixCls="ag"
      iconPrefixCls="ag-icon"
      locale={zhCN}
      theme={{
        cssVar: { key: "ag" },
        algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
        token: {
          ...(isDark ? darkTokens : lightTokens),
          borderRadius: 8,
          fontFamily: "Inter, system-ui, -apple-system, sans-serif",
        },
        hashed: false,
      }}
    >
      <AntApp>
        <BrowserRouter>
          <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Landing />} />
          <Route path="/mock-pay" element={<MockPay />} />
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/credits" element={<Credits />} />
            <Route path="/history" element={<History />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/reduce/new" element={<NewTask />} />
            <Route path="/reduce/:taskId" element={<TaskWorkspace />} />
            <Route path="/admin/dashboard" element={<AdminDashboard />} />
            <Route path="/admin/packages" element={<AdminPackages />} />
            <Route path="/admin/orders" element={<AdminOrders />} />
            <Route path="/admin/users" element={<AdminUsers />} />
            <Route path="/admin/transactions" element={<AdminTransactions />} />
            <Route path="/admin/config" element={<AdminConfig />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}
