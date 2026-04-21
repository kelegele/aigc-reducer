// web/frontend/src/pages/Settings.tsx
import { Card, Descriptions, Typography } from "antd";
import { useAuthStore } from "../stores/auth";

const { Title } = Typography;

export default function Settings() {
  const { user } = useAuthStore();

  return (
    <div>
      <Title level={4}>个人设置</Title>
      <Card>
        <Descriptions column={1}>
          <Descriptions.Item label="手机号">{user?.phone}</Descriptions.Item>
          <Descriptions.Item label="昵称">{user?.nickname}</Descriptions.Item>
          <Descriptions.Item label="积分余额">{user?.credit_balance}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
