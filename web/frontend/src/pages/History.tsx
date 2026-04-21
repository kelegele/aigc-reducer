// web/frontend/src/pages/History.tsx
import { Card, Empty, Typography } from "antd";

const { Title } = Typography;

export default function History() {
  return (
    <div>
      <Title level={4}>检测历史</Title>
      <Card>
        <Empty description="检测功能开发中（P3）" />
      </Card>
    </div>
  );
}
