import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Table, Typography } from "antd";
import {
  UserOutlined,
  DollarOutlined,
  ThunderboltOutlined,
  RiseOutlined,
  FileSearchOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  getDashboard,
  type DashboardResponse,
  type TopUserEntry,
} from "../../api/admin";

const { Title } = Typography;

export default function AdminDashboard() {
  const [data, setData] = useState<DashboardResponse | null>(null);

  useEffect(() => {
    getDashboard().then(setData).catch(() => {});
  }, []);

  const topColumns: ColumnsType<TopUserEntry> = [
    { title: "用户", dataIndex: "nickname", key: "nickname" },
    { title: "手机号", dataIndex: "phone", key: "phone" },
    { title: "金额/积分", dataIndex: "amount", key: "amount" },
  ];

  return (
    <div>
      <Title level={4}>数据看板</Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="总用户" value={data?.total_users ?? 0} prefix={<UserOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="总收入(元)" value={((data?.total_revenue_cents ?? 0) / 100).toFixed(2)} prefix={<DollarOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="总发放积分" value={data?.total_credits_granted ?? 0} prefix={<ThunderboltOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="总消费积分" value={data?.total_credits_consumed ?? 0} prefix={<ThunderboltOutlined />} /></Card>
        </Col>
      </Row>
      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="今日新增用户" value={data?.today_new_users ?? 0} prefix={<RiseOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="总检测量" value={data?.total_detections ?? 0} prefix={<FileSearchOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card><Statistic title="今日检测量" value={data?.today_detections ?? 0} prefix={<FileSearchOutlined />} /></Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} md={12}>
          <Card title="充值 Top 10">
            <Table columns={topColumns} dataSource={data?.top_recharge_users ?? []} rowKey="user_id" size="small" pagination={false} />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="消费 Top 10">
            <Table columns={topColumns} dataSource={data?.top_consume_users ?? []} rowKey="user_id" size="small" pagination={false} />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
