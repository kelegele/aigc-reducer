// web/frontend/src/pages/Dashboard.tsx
import { useNavigate } from "react-router-dom";
import { Card, Col, Row, Statistic, Typography, Button, Empty, Steps, theme } from "antd";
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

const { Title, Text, Paragraph } = Typography;

export default function Dashboard() {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const { token } = theme.useToken();

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
              value={0}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="改写段落"
              value={0}
              prefix={<EditOutlined />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="通过率"
              value={0}
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
        <Empty description="暂无检测记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </Card>
    </div>
  );
}
