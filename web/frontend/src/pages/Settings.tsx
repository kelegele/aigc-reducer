// web/frontend/src/pages/Settings.tsx
import { useState } from "react";
import { App as AntApp, Avatar, Card, Descriptions, Input, Typography } from "antd";
import { UserOutlined } from "@ant-design/icons";
import { useAuthStore } from "../stores/auth";
import { updateProfile } from "../api/auth";

const { Title } = Typography;

export default function Settings() {
  const { user, fetchUser } = useAuthStore();
  const { message } = AntApp.useApp();
  const [nicknameEditing, setNicknameEditing] = useState(false);
  const [nickname, setNickname] = useState(user?.nickname ?? "");

  const handleNicknameSave = async () => {
    if (!nickname.trim()) return;
    try {
      await updateProfile({ nickname: nickname.trim() });
      await fetchUser();
      message.success("昵称已更新");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || "更新失败");
    }
    setNicknameEditing(false);
  };

  return (
    <div>
      <Title level={4}>个人设置</Title>
      <Card>
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <Avatar size={80} src={user?.avatar_url} icon={!user?.avatar_url && <UserOutlined />} />
        </div>
        <Descriptions column={1}>
          <Descriptions.Item label="手机号">{user?.phone}</Descriptions.Item>
          <Descriptions.Item label="昵称">
            {nicknameEditing ? (
              <Input.Search
                enterButton="保存"
                size="small"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                onSearch={handleNicknameSave}
                onBlur={() => setNicknameEditing(false)}
                style={{ maxWidth: 240 }}
                autoFocus
              />
            ) : (
              <span
                style={{ cursor: "pointer" }}
                onClick={() => { setNickname(user?.nickname ?? ""); setNicknameEditing(true); }}
              >
                {user?.nickname} <a>修改</a>
              </span>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="积分余额">{user?.credit_balance}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  );
}
