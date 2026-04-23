// web/frontend/src/pages/credits/Packages.tsx
import { useEffect, useState } from "react";
import {
  App as AntApp,
  Card,
  Row,
  Col,
  Button,
  Typography,
  Tag,
  Alert,
  Spin,
} from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";
import { useCreditsStore } from "../../stores/credits";
import { createRecharge, getOrder } from "../../api/credits";

const { Title, Text } = Typography;

const packageScenes: Record<string, string> = {
  "体验包": "适合体验用户",
  "基础包": "适合本科论文",
  "标准包": "适合硕博论文",
  "专业包": "适合多篇论文",
  "豪华包": "适合团队使用",
};

export default function Packages() {
  const { packages, fetchPackages, fetchBalance, fetchTransactions } = useCreditsStore();
  const { message, modal } = AntApp.useApp();
  const [payingOrderId, setPayingOrderId] = useState<number | null>(null);
  const [polling, setPolling] = useState(false);
  const [confirming, setConfirming] = useState(false);

  useEffect(() => {
    fetchPackages();
  }, [fetchPackages]);

  useEffect(() => {
    // 支付宝回跳自动检测（return_url 带 order_id 参数）
    const params = new URLSearchParams(window.location.search);
    const orderId = params.get("order_id");
    if (orderId) {
      window.history.replaceState({}, "", "/credits");
      const id = parseInt(orderId, 10);
      if (!isNaN(id)) {
        setPayingOrderId(id);
        setConfirming(true);
        startPolling(id);
      }
    }
  }, []);

  const handleRecharge = async (pkgId: number, pkgName: string, price: number) => {
    modal.confirm({
      title: "确认充值",
      content: `套餐：${pkgName}，金额：¥${(price / 100).toFixed(2)}`,
      onOk: async () => {
        try {
          const result = await createRecharge({
            package_id: pkgId,
            pay_method: "pc_web",
          });
          setPayingOrderId(result.order_id);
          // 新 tab 打开支付页面
          window.open(result.pay_url, "_blank");
          // 弹窗确认是否已完成支付
          modal.confirm({
            title: "支付确认",
            content: "请在新打开的页面完成支付，完成后点击下方按钮确认",
            okText: "已充值",
            cancelText: "未完成",
            onOk: () => {
              startPolling(result.order_id);
            },
          });
        } catch (err: unknown) {
          const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
          message.error(detail || "创建订单失败");
        }
      },
    });
  };

  const startPolling = (orderId: number) => {
    setPolling(true);
    setConfirming(true);
    let count = 0;
    const interval = setInterval(async () => {
      count++;
      if (count > 30) {
        clearInterval(interval);
        setPolling(false);
        setConfirming(false);
        message.warning("支付结果未确认，请稍后在订单列表中查看");
        return;
      }
      try {
        const order = await getOrder(orderId);
        if (order.status === "paid") {
          clearInterval(interval);
          setPolling(false);
          setConfirming(false);
          setPayingOrderId(null);
          message.success("充值成功！");
          fetchBalance();
          fetchTransactions({ page: 1, size: 5 });
        }
      } catch {
        // 继续轮询
      }
    }, 2000);
  };

  return (
    <div>
      <Title level={5}>选择充值套餐</Title>

      {/* 支付结果确认中 */}
      {confirming && (
        <Alert
          type="info"
          showIcon
          icon={<Spin size="small" />}
          message="支付结果确认中..."
          description="正在查询支付结果，请稍候"
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 积分用途说明 */}
      <Alert
        type="info"
        showIcon
        icon={<InfoCircleOutlined />}
        message="积分用途说明"
        description="积分用于文档检测和 AI 改写。系统按实际消耗的 Token 数量扣减积分（每 1000 Token 消耗一定积分，具体价格请参见套餐详情）。"
        style={{ marginBottom: 16 }}
      />

      <Row gutter={[16, 16]}>
        {packages.map((pkg) => {
          const pricePerCredit = pkg.price_cents / (pkg.credits + pkg.bonus_credits);
          const scene = packageScenes[pkg.name] || "通用套餐";

          return (
            <Col xs={24} sm={12} md={8} key={pkg.id}>
              <Card hoverable>
                <div style={{ textAlign: "center" }}>
                  <Title level={4} style={{ marginBottom: 4 }}>
                    {pkg.name}
                  </Title>
                  <Tag color="blue" style={{ marginBottom: 12 }}>
                    {scene}
                  </Tag>
                  <div style={{ margin: "16px 0" }}>
                    <Text style={{ fontSize: 32, fontWeight: "bold" }}>
                      ¥{(pkg.price_cents / 100).toFixed(0)}
                    </Text>
                  </div>
                  <div style={{ marginBottom: 8 }}>
                    <Text>{pkg.credits} 积分</Text>
                    {pkg.bonus_credits > 0 && (
                      <Tag color="red" style={{ marginLeft: 8 }}>
                        赠送 {pkg.bonus_credits}
                      </Tag>
                    )}
                  </div>
                  <div style={{ marginBottom: 12 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      约 ¥{(pricePerCredit / 100).toFixed(3)}/积分
                    </Text>
                  </div>
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
          );
        })}
      </Row>
      {packages.length === 0 && (
        <Card>
          <Text type="secondary">暂无可用套餐</Text>
        </Card>
      )}
    </div>
  );
}
