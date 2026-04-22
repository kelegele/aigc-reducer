// web/frontend/src/pages/credits/Packages.tsx
import { useEffect, useState } from "react";
import {
  Card,
  Row,
  Col,
  Button,
  Typography,
  Tag,
  Modal,
  message,
} from "antd";
import { useCreditsStore } from "../../stores/credits";
import { createRecharge } from "../../api/credits";

const { Title, Text } = Typography;

export default function Packages() {
  const { packages, fetchPackages, fetchBalance } = useCreditsStore();
  const [payingOrderId, setPayingOrderId] = useState<number | null>(null);
  const [polling, setPolling] = useState(false);

  useEffect(() => {
    fetchPackages();
  }, [fetchPackages]);

  const handleRecharge = async (pkgId: number, pkgName: string, price: number) => {
    Modal.confirm({
      title: "确认充值",
      content: `套餐：${pkgName}，金额：¥${(price / 100).toFixed(2)}`,
      onOk: async () => {
        try {
          const result = await createRecharge({
            package_id: pkgId,
            pay_method: "pc_web",
          });
          setPayingOrderId(result.order_id);
          window.location.href = result.pay_url;
          startPolling(result.order_id);
        } catch {
          message.error("创建订单失败");
        }
      },
    });
  };

  const startPolling = (orderId: number) => {
    setPolling(true);
    let count = 0;
    const interval = setInterval(async () => {
      count++;
      if (count > 30) {
        clearInterval(interval);
        setPolling(false);
        return;
      }
      try {
        const { getOrder } = await import("../../api/credits");
        const order = await getOrder(orderId);
        if (order.status === "paid") {
          clearInterval(interval);
          setPolling(false);
          setPayingOrderId(null);
          message.success("充值成功！");
          fetchBalance();
        }
      } catch {
        // 继续轮询
      }
    }, 2000);
  };

  return (
    <div>
      <Title level={5}>选择充值套餐</Title>
      <Row gutter={[16, 16]}>
        {packages.map((pkg) => (
          <Col xs={24} sm={12} md={8} key={pkg.id}>
            <Card hoverable>
              <Title level={4} style={{ textAlign: "center" }}>
                {pkg.name}
              </Title>
              <div style={{ textAlign: "center", margin: "16px 0" }}>
                <Text style={{ fontSize: 32, fontWeight: "bold" }}>
                  ¥{(pkg.price_cents / 100).toFixed(0)}
                </Text>
              </div>
              <div style={{ textAlign: "center", marginBottom: 8 }}>
                <Text>{pkg.credits} 积分</Text>
                {pkg.bonus_credits > 0 && (
                  <Tag color="red" style={{ marginLeft: 8 }}>
                    赠送 {pkg.bonus_credits}
                  </Tag>
                )}
              </div>
              <Button
                type="primary"
                block
                loading={polling && payingOrderId !== null}
                onClick={() =>
                  handleRecharge(pkg.id, pkg.name, pkg.price_cents)
                }
              >
                立即充值
              </Button>
            </Card>
          </Col>
        ))}
      </Row>
      {packages.length === 0 && (
        <Card>
          <Text type="secondary">暂无可用套餐</Text>
        </Card>
      )}
    </div>
  );
}
