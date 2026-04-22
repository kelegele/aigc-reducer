// web/frontend/src/components/AppLayout.tsx
import { useEffect } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import {
  Layout,
  Menu,
  Avatar,
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
} from "@ant-design/icons";
import { useAuthStore } from "../stores/auth";

const { Header, Content } = Layout;
const { Text } = Typography;

const getMenuItems = (isAdmin: boolean) => [
  { key: "/dashboard", icon: <DashboardOutlined />, label: "仪表盘" },
  { key: "/credits", icon: <CreditCardOutlined />, label: "积分" },
  { key: "/history", icon: <HistoryOutlined />, label: "历史" },
  { key: "/settings", icon: <SettingOutlined />, label: "设置" },
  ...(isAdmin
    ? [{ key: "/admin/dashboard", icon: <DashboardOutlined />, label: "管理" }]
    : []),
];

export default function AppLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, fetchUser } = useAuthStore();
  const { token: themeToken } = theme.useToken();

  useEffect(() => {
    if (!user) {
      fetchUser();
    }
  }, []);

  const handleLogout = () => {
    logout();
    navigate("/login");
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
          <Text strong style={{ fontSize: 18, whiteSpace: "nowrap" }}>
            AIGC Reducer
          </Text>
          <Menu
            mode="horizontal"
            selectedKeys={[location.pathname]}
            items={getMenuItems(!!user?.is_admin)}
            onClick={({ key }) => navigate(key)}
            style={{ border: "none", flex: 1 }}
          />
        </div>
        <Dropdown menu={userMenu} placement="bottomRight">
          <div style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: 8 }}>
            <Avatar icon={<UserOutlined />} />
            <Text style={{ display: "none" }} className="show-on-mobile">
              {user?.nickname}
            </Text>
          </div>
        </Dropdown>
      </Header>
      <Content style={{ padding: "24px", maxWidth: 1200, margin: "0 auto", width: "100%" }}>
        <Outlet />
      </Content>
    </Layout>
  );
}
