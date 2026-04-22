// web/frontend/src/pages/Dashboard.tsx
import { Card, Col, Row, Statistic, Typography, Steps } from "antd";
import {
  CreditCardOutlined,
  FileTextOutlined,
  SearchOutlined,
  EditOutlined,
  DownloadOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
  FileProtectOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../stores/auth";

const { Title, Text, Paragraph } = Typography;

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

      {/* 产品介绍 */}
      <Card style={{ marginTop: 24 }}>
        <Title level={4} style={{ marginBottom: 8 }}>
          什么是 AIGC Reducer？
        </Title>
        <Paragraph style={{ fontSize: 16, color: "#666" }}>
          AIGC Reducer 是一款专业的学术论文 AIGC 查重率降低工具。通过检测 AI 写作特征并提供多种改写风格，
          有效降低知网、GoCheck 等主流平台的 AI 查重率，帮助您的论文顺利通过审核。
        </Paragraph>

        <Title level={5} style={{ marginTop: 24 }}>
          核心功能
        </Title>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={8}>
            <Card size="small" variant="borderless" style={{ background: "#f6ffed" }}>
              <SafetyCertificateOutlined style={{ fontSize: 28, color: "#52c41a" }} />
              <Title level={5} style={{ marginTop: 8, marginBottom: 4 }}>
                双引擎检测
              </Title>
              <Text type="secondary">
                规则引擎（5 维特征分析）+ LLM 反查模拟，精准识别 AI 痕迹
              </Text>
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card size="small" variant="borderless" style={{ background: "#e6f7ff" }}>
              <EditOutlined style={{ fontSize: 28, color: "#1890ff" }} />
              <Title level={5} style={{ marginTop: 8, marginBottom: 4 }}>
                5 种改写风格
              </Title>
              <Text type="secondary">
                学术人文化、口语化、文言文化、中英混杂、粗犷草稿风，满足不同需求
              </Text>
            </Card>
          </Col>
          <Col xs={24} sm={8}>
            <Card size="small" variant="borderless" style={{ background: "#fff7e6" }}>
              <FileProtectOutlined style={{ fontSize: 28, color: "#fa8c16" }} />
              <Title level={5} style={{ marginTop: 8, marginBottom: 4 }}>
                完整输出
              </Title>
              <Text type="secondary">
                改写全文 + 差异对比 + 整改建议报告，一目了然
              </Text>
            </Card>
          </Col>
        </Row>
      </Card>

      {/* 操作流程 */}
      <Card style={{ marginTop: 16 }}>
        <Title level={5} style={{ marginBottom: 16 }}>
          使用流程
        </Title>
        <Steps
          current={-1}
          items={[
            {
              title: "上传文档",
              description: "支持 Word、PDF、Markdown 格式",
              icon: <FileTextOutlined />,
            },
            {
              title: "扫描风险",
              description: "AI 特征检测，标记高风险段落",
              icon: <SearchOutlined />,
            },
            {
              title: "选择风格",
              description: "5 种改写风格，aggressive/conservative 两档",
              icon: <ThunderboltOutlined />,
            },
            {
              title: "AI 改写",
              description: "逐段 A/B 改写，人工确认每一处",
              icon: <EditOutlined />,
            },
            {
              title: "下载结果",
              description: "改写全文 + 差异对比 + 整改报告",
              icon: <DownloadOutlined />,
            },
          ]}
        />
      </Card>
    </div>
  );
}
