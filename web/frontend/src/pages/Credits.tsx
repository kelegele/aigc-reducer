// web/frontend/src/pages/Credits.tsx
import { Card, Empty, Typography } from "antd";

const { Title } = Typography;

export default function Credits() {
  return (
    <div>
      <Title level={4}>积分管理</Title>
      <Card>
        <Empty description="充值功能开发中（P2）" />
      </Card>
    </div>
  );
}
