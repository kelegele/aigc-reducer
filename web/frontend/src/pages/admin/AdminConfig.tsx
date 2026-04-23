import { useEffect, useState } from "react";
import { App as AntApp, Button, Card, Form, InputNumber, Typography } from "antd";
import { getConfig, updateConfig } from "../../api/admin";

const { Title } = Typography;

export default function AdminConfig() {
  const { message } = AntApp.useApp();
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    getConfig().then((data) => {
      form.setFieldsValue(data);
    });
  }, [form]);

  const handleSave = async () => {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const updated = await updateConfig(values);
      form.setFieldsValue(updated);
      message.success("配置已更新（运行时生效，重启后恢复默认）");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      if (detail) message.error(detail);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <Title level={4}>积分配置</Title>
      <Card style={{ maxWidth: 500 }}>
        <Form form={form} layout="vertical">
          <Form.Item name="credits_per_token" label="每 1000 Token 积分价格" rules={[{ required: true }]}>
            <InputNumber min={0.01} step={0.1} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="new_user_bonus_credits" label="新人赠送积分" rules={[{ required: true }]}>
            <InputNumber min={0} step={10} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" onClick={handleSave} loading={saving}>保存</Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
