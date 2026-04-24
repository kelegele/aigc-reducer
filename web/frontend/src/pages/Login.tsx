// web/frontend/src/pages/Login.tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { App as AntApp, Button, Card, Form, Input, Spin, Typography, theme } from "antd";
import { MobileOutlined, SafetyOutlined, BulbOutlined, LeftOutlined } from "@ant-design/icons";
import { useAuthStore } from "../stores/auth";
import { useThemeStore } from "../stores/theme";

const { Title, Text } = Typography;

export default function Login() {
  const [form] = Form.useForm();
  const [sending, setSending] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [checking, setChecking] = useState(true);
  const { login, sendSms, loading, user, fetchUser } = useAuthStore();
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const { isDark, toggle } = useThemeStore();
  const { message } = AntApp.useApp();

  // 已登录自动跳转
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token && user) {
      navigate("/dashboard", { replace: true });
    } else if (token) {
      fetchUser().then(() => setChecking(false));
    } else {
      setChecking(false);
    }
  }, []);

  // fetchUser 完成后 user 变化，再跳转
  useEffect(() => {
    if (user) {
      navigate("/dashboard", { replace: true });
    }
  }, [user]);

  if (checking) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <Spin size="large" />
      </div>
    );
  }

  const handleSendCode = async () => {
    try {
      const phone = form.getFieldValue("phone");
      if (!phone || !/^1[3-9]\d{9}$/.test(phone)) {
        message.error("请输入正确的手机号");
        return;
      }
      setSending(true);
      await sendSms(phone);
      message.success("验证码已发送（开发模式下查看后端控制台）");
      setCountdown(60);
      const timer = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(timer);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || "发送失败，请稍后重试");
    } finally {
      setSending(false);
    }
  };

  const handleLogin = async (values: { phone: string; code: string }) => {
    try {
      await login(values.phone, values.code);
      message.success("登录成功");
      navigate("/dashboard");
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { detail?: string | Array<{ msg: string }> } } })?.response?.data;
      if (resp?.detail) {
        if (typeof resp.detail === "string") {
          message.error(resp.detail);
        } else if (Array.isArray(resp.detail)) {
          message.error(resp.detail.map((e: { msg: string }) => e.msg).join("; "));
        }
      } else {
        message.error("登录失败，请检查验证码");
      }
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        background: token.colorBgLayout,
        position: "relative",
      }}
    >
      <Button
        type="text"
        icon={<LeftOutlined />}
        onClick={() => navigate("/")}
        style={{
          position: "absolute",
          top: 16,
          left: 16,
          color: token.colorTextSecondary,
        }}
      />
      <Button
        type="text"
        icon={<BulbOutlined />}
        onClick={toggle}
        style={{
          position: "absolute",
          top: 16,
          right: 16,
          color: token.colorTextSecondary,
        }}
      />
      <Card style={{ width: 400, maxWidth: "90vw" }}>
        <Title level={3} style={{ textAlign: "center", marginBottom: 32, cursor: "pointer" }} onClick={() => navigate("/")}>
          AIGC<span style={{ color: token.colorPrimary }}>Reducer</span>
        </Title>
        <Form form={form} onFinish={handleLogin} size="large">
          <Form.Item
            name="phone"
            rules={[{ required: true, message: "请输入手机号" }]}
          >
            <Input
              prefix={<MobileOutlined />}
              placeholder="手机号"
              maxLength={11}
            />
          </Form.Item>
          <Form.Item
            name="code"
            rules={[{ required: true, message: "请输入验证码" }]}
          >
            <Input
              prefix={<SafetyOutlined />}
              placeholder="验证码"
              maxLength={6}
              addonAfter={
                <Button
                  type="link"
                  size="small"
                  onClick={handleSendCode}
                  loading={sending}
                  disabled={countdown > 0}
                  style={{ padding: 0 }}
                >
                  {countdown > 0 ? `${countdown}s` : "获取验证码"}
                </Button>
              }
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block loading={loading}>
              登录 / 注册
            </Button>
          </Form.Item>
        </Form>
        <Text
          type="secondary"
          style={{ display: "block", textAlign: "center" }}
        >
          首次登录将自动创建账户
        </Text>
      </Card>
    </div>
  );
}
