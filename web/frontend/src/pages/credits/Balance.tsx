// web/frontend/src/pages/credits/Balance.tsx
import { useEffect } from "react";
import { Card, Col, Row, Statistic, Button, Typography, List } from "antd";
import { CreditCardOutlined } from "@ant-design/icons";
import { useCreditsStore } from "../../stores/credits";

const { Text } = Typography;

interface BalanceProps {
  onGoPackages: () => void;
}

export default function Balance({ onGoPackages }: BalanceProps) {
  const { balance, transactions, fetchBalance, fetchTransactions } =
    useCreditsStore();

  useEffect(() => {
    fetchBalance();
    fetchTransactions({ page: 1, size: 5 });
  }, [fetchBalance, fetchTransactions]);

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="当前积分"
              value={balance?.balance ?? 0}
              prefix={<CreditCardOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="累计充值" value={balance?.total_recharged ?? 0} />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic title="累计消费" value={balance?.total_consumed ?? 0} />
          </Card>
        </Col>
      </Row>

      <Card
        title="最近流水"
        style={{ marginTop: 16 }}
        extra={
          <Button type="link" onClick={onGoPackages}>
            充值积分
          </Button>
        }
      >
        {transactions && transactions.items.length > 0 ? (
          <List
            size="small"
            dataSource={transactions.items.slice(0, 5)}
            renderItem={(item) => (
              <List.Item>
                <List.Item.Meta
                  title={item.remark || (item.type === "recharge" ? "充值" : "消费")}
                  description={item.created_at}
                />
                <Text type={item.amount > 0 ? "success" : "danger"}>
                  {item.amount > 0 ? "+" : ""}
                  {item.amount}
                </Text>
              </List.Item>
            )}
          />
        ) : (
          <Text type="secondary">暂无流水记录</Text>
        )}
      </Card>
    </div>
  );
}
