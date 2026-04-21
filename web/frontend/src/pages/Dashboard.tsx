// web/frontend/src/pages/Dashboard.tsx
import { Card, Col, Row, Statistic, Typography } from "antd";
import { CreditCardOutlined, FileTextOutlined } from "@ant-design/icons";
import { useAuthStore } from "../stores/auth";

const { Title } = Typography;

export default function Dashboard() {
  const { user } = useAuthStore();

  return (
    <div>
      <Title level={4}>欢迎，{user?.nickname}</Title>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12}>
          <Card>
            <Statistic
              title="积分余额"
              value={user?.credit_balance ?? 0}
              prefix={<CreditCardOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12}>
          <Card>
            <Statistic
              title="检测次数"
              value={0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
