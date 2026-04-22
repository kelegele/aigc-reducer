// web/frontend/src/pages/MockPay.tsx
import { useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Button, Card, Result, Spin, Typography, message } from "antd";
import client from "../api/client";

const { Title, Text } = Typography;

export default function MockPay() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const orderNo = searchParams.get("order") || "";
  const amount = searchParams.get("amount") || "0";
  const returnUrl = searchParams.get("return") || "/credits";

  const handlePay = async () => {
    setLoading(true);
    try {
      await client.post("/credits/payment/callback", {
        mock_sign: "ok",
        out_trade_no: orderNo,
      });
      setSuccess(true);
      message.success("模拟支付成功！");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || "模拟支付失败");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: "100vh",
          background: "#f0f2f5",
        }}
      >
        <Result
          status="success"
          title="支付成功"
          subTitle={`订单 ${orderNo} 已完成支付，积分即将到账`}
          extra={[
            <Button
              key="back"
              type="primary"
              onClick={() => {
                window.location.href = returnUrl;
              }}
            >
              返回积分页面
            </Button>,
          ]}
        />
      </div>
    );
  }

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        background: "#f0f2f5",
      }}
    >
      <Card style={{ width: 420, maxWidth: "90vw", textAlign: "center" }}>
        <Title level={3}>模拟支付</Title>
        <Text type="secondary" style={{ display: "block", marginBottom: 24 }}>
          开发环境 Mock 支付页面
        </Text>
        <div style={{ marginBottom: 24, textAlign: "left" }}>
          <p>
            <Text strong>订单号：</Text>
            <Text code>{orderNo}</Text>
          </p>
          <p>
            <Text strong>支付金额：</Text>
            <Text style={{ fontSize: 24, fontWeight: "bold", color: "#f50" }}>
              ¥{(parseInt(amount, 10) / 100).toFixed(2)}
            </Text>
          </p>
        </div>
        <Button
          type="primary"
          size="large"
          block
          loading={loading}
          onClick={handlePay}
        >
          模拟支付成功
        </Button>
        <div style={{ marginTop: 16 }}>
          <Button type="link" onClick={() => navigate(returnUrl)}>
            返回
          </Button>
        </div>
      </Card>
    </div>
  );
}
