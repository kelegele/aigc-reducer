// web/frontend/src/components/AppLayout.tsx
import { useEffect, useState } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  Layout,
  Menu,
  Avatar,
  Button,
  Drawer,
  Dropdown,
  Typography,
  theme,
} from "antd";
import {
  DashboardOutlined,
  CreditCardOutlined,
  HistoryOutlined,
  SettingOutlined,
  LogoutOutlined,
  UserOutlined,
  TeamOutlined,
  ShoppingOutlined,
  ControlOutlined,
  FileTextOutlined,
  BulbOutlined,
  EditOutlined,
  MenuOutlined,
  DatabaseOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../stores/auth";
import { useThemeStore } from "../stores/theme";

const { Header, Content } = Layout;
const { Text } = Typography;

const getMenuItems = (isAdmin: boolean) => [
  { key: "/dashboard", icon: <DashboardOutlined />, label: "仪表盘" },
  { key: "/reduce/new", icon: <EditOutlined />, label: "检测降重" },
  { key: "/task-list", icon: <HistoryOutlined />, label: "检测记录" },
  { key: "/credits", icon: <CreditCardOutlined />, label: "积分" },
  { key: "/settings", icon: <SettingOutlined />, label: "设置" },
  ...(isAdmin
    ? [
        {
          key: "admin",
          icon: <ControlOutlined />,
          label: "管理",
          children: [
            { key: "/admin/dashboard", icon: <DashboardOutlined />, label: "数据看板" },
            { key: "/admin/packages", icon: <ShoppingOutlined />, label: "套餐管理" },
            { key: "/admin/orders", icon: <FileTextOutlined />, label: "订单管理" },
            { key: "/admin/users", icon: <TeamOutlined />, label: "用户管理" },
            { key: "/admin/transactions", icon: <HistoryOutlined />, label: "流水管理" },
            { key: "/admin/content", icon: <DatabaseOutlined />, label: "内容管理" },
            { key: "/admin/config", icon: <SettingOutlined />, label: "积分配置" },
          ],
        },
      ]
    : []),
];

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, fetchUser } = useAuthStore();
  const { token: themeToken } = theme.useToken();
  const { isDark, toggle } = useThemeStore();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (!user) {
      fetchUser();
    }
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/");
  };

  const userMenu = {
    items: [
      {
        key: "logout",
        icon: <LogoutOutlined />,
        label: "退出登录",
        onClick: handleLogout,
      },
    ],
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 24px",
          background: themeToken.colorBgContainer,
          borderBottom: `1px solid ${themeToken.colorBorderSecondary}`,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <Text strong style={{ fontSize: 18, whiteSpace: "nowrap", cursor: "pointer" }} onClick={() => navigate("/")}>
            AIGC<span style={{ color: themeToken.colorPrimary }}>Reducer</span>
          </Text>
          <Menu
            mode="horizontal"
            selectedKeys={[location.pathname]}
            items={getMenuItems(!!user?.is_admin)}
            onClick={({ key }) => navigate(key)}
            style={{ border: "none", flex: 1 }}
          />
          <Button
            type="text"
            icon={<MenuOutlined />}
            onClick={() => setMobileMenuOpen(true)}
            className="show-on-mobile"
            style={{ color: themeToken.colorText }}
          />
        </div>
        <Drawer
          placement="left"
          open={mobileMenuOpen}
          onClose={() => setMobileMenuOpen(false)}
          width={240}
          styles={{ body: { padding: 0 } }}
        >
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={getMenuItems(!!user?.is_admin)}
            onClick={({ key }) => { navigate(key); setMobileMenuOpen(false); }}
            style={{ border: "none" }}
          />
        </Drawer>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Button
            type="text"
            size="small"
            icon={<BulbOutlined />}
            onClick={toggle}
            style={{ color: themeToken.colorTextSecondary }}
          />
          <Dropdown menu={userMenu} placement="bottomRight">
            <div style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
              <Avatar icon={<UserOutlined />} />
              <Text style={{ display: "none" }}>
                {user?.nickname}
              </Text>
            </div>
          </Dropdown>
        </div>
      </Header>
      <Content style={{ padding: "24px", maxWidth: 1200, margin: "0 auto", width: "100%" }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
