// web/frontend/src/pages/Dashboard.tsx
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { App as AntApp, Card, Col, Row, Statistic, Steps, Typography, Button, Empty, List, Tag, Spin, theme } from "antd";
import {
  CreditCardOutlined,
  FileTextOutlined,
  SafetyCertificateOutlined,
  EditOutlined,
  DownloadOutlined,
  SearchOutlined,
  ThunderboltOutlined,
  RightOutlined,
  PlusCircleOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../stores/auth";
import { getUserStats, getTasks, type TaskListItem, type UserStatsResponse } from "../api/reduce";
import { TASK_STATUS_LABELS } from "../constants/reduce";

const { Title, Text, Paragraph } = Typography;

function taskStatusColor(status: string): string {
  switch (status) {
    case "completed": return "success";
    case "failed": return "error";
    default: return "processing";
  }
}

export default function Dashboard() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { token } = theme.useToken();
  const { message } = AntApp.useApp();

  const [stats, setStats] = useState<UserStatsResponse | null>(null);
  const [recentTasks, setRecentTasks] = useState<TaskListItem[]>([]);
  const [loading, setLoading] = useState(true);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    try {
      const [s, resp] = await Promise.all([
        getUserStats(),
        getTasks({ page: 1, page_size: 5 }),
      ]);
      setStats(s);
      setRecentTasks(resp.items);
    } catch {
      // 静默失败——统计数据不是关键数据
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Title level={4} style={{ fontFamily: "system-ui, -apple-system, sans-serif", margin: 0 }}>
          欢迎，{user?.nickname}
        </Title>
        <Button
          type="primary"
          size="large"
          icon={<PlusCircleOutlined />}
          onClick={() => navigate("/reduce/new")}
          style={{ height: 44, paddingInline: 28, fontSize: 15, fontWeight: 600 }}
        >
          开始检测降重
        </Button>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={12} sm={6}>
          <Card style={{ borderTop: `2px solid ${token.colorPrimary}` }}>
            <Statistic
              title="积分余额"
              value={user?.credit_balance ?? 0}
              prefix={<CreditCardOutlined />}
              valueStyle={{ color: token.colorPrimary }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="检测次数"
              value={stats?.detection_count ?? 0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="改写段落"
              value={stats?.rewritten_paragraphs ?? 0}
              prefix={<EditOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="通过率"
              value={stats?.pass_rate ?? 0}
              suffix="%"
              prefix={<SafetyCertificateOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 快速上手 */}
      <Card style={{ marginTop: 24 }}>
        <Title level={5} style={{ marginBottom: 16 }}>
          快速上手
        </Title>
        <Paragraph type="secondary" style={{ marginBottom: 20 }}>
          上传论文 → AI 检测风险段落 → 选择改写风格 → 下载降重结果。支持 Word、PDF、Markdown 格式，双引擎检测 + 5 种改写风格。
        </Paragraph>
        <Steps
          size="small"
          current={-1}
          style={{ cursor: "pointer" }}
          onClick={() => navigate("/reduce/new")}
          items={[
            {
              title: "上传文档",
              icon: <FileTextOutlined style={{ color: token.colorPrimary }} />,
              style: { color: token.colorPrimary },
            },
            {
              title: "扫描风险",
              icon: <SearchOutlined style={{ color: token.colorPrimary }} />,
              style: { color: token.colorPrimary },
            },
            {
              title: "AI 改写",
              icon: <ThunderboltOutlined style={{ color: token.colorPrimary }} />,
              style: { color: token.colorPrimary },
            },
            {
              title: "下载结果",
              icon: <DownloadOutlined style={{ color: token.colorPrimary }} />,
              style: { color: token.colorPrimary },
            },
          ]}
        />
      </Card>

      {/* 最近检测记录 */}
      <Card
        style={{ marginTop: 16 }}
        title="最近检测记录"
        extra={
          <Button type="link" icon={<RightOutlined />} onClick={() => navigate("/history")}>
            查看全部
          </Button>
        }
      >
        {loading ? (
          <div style={{ textAlign: "center", padding: 20 }}>
            <Spin />
          </div>
        ) : recentTasks.length === 0 ? (
          <Empty description="暂无检测记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        ) : (
          <List
            dataSource={recentTasks}
            renderItem={(item) => (
              <List.Item
                style={{ cursor: "pointer", padding: "8px 0" }}
                onClick={() => navigate(`/reduce/${item.id}`)}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12, width: "100%" }}>
                  <Text ellipsis style={{ flex: 1, fontSize: 14 }}>{item.title}</Text>
                  <Tag color={taskStatusColor(item.status)} style={{ margin: 0 }}>
                    {TASK_STATUS_LABELS[item.status] ?? item.status}
                  </Tag>
                  <Text type="secondary" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
                    {new Date(item.created_at + "Z").toLocaleString("zh-CN")}
                  </Text>
                </div>
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  );
}
