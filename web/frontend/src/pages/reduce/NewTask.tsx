// web/frontend/src/pages/reduce/NewTask.tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  App as AntApp,
  Button,
  Card,
  Col,
  Input,
  Radio,
  Row,
  Typography,
  Upload,
  theme,
  Space,
  Tag,
} from "antd";
import {
  UploadOutlined,
  ThunderboltOutlined,
  RobotOutlined,
  FileTextOutlined,
  FormOutlined,
  RocketOutlined,
} from "@ant-design/icons";
import type { UploadFile } from "antd/es/upload/interface";
import { createTask } from "../../api/reduce";

const { Text, Paragraph } = Typography;
const { TextArea } = Input;

interface StyleOption {
  key: string;
  label: string;
  desc: string;
  tag?: string;
}

const STYLE_OPTIONS: StyleOption[] = [
  {
    key: "学术人文化",
    label: "学术人文化",
    tag: "推荐",
    desc: "保留学术严谨性，融入自然的人类写作节奏，降低 AI 痕迹同时维持论文质量",
  },
  {
    key: "口语化",
    label: "口语化",
    desc: "将书面表达转化为更自然、接地气的语言风格，适合非正式学术场景",
  },
  {
    key: "文言文化",
    label: "文言文化",
    desc: "融入文言表达，增添古韵，有效打破 AI 的现代白话模式",
  },
  {
    key: "中英混杂化",
    label: "中英混杂化",
    desc: "适度插入英文术语和短语，模拟真实学术写作中的双语混用习惯",
  },
  {
    key: "粗犷草稿风",
    label: "粗犷草稿风",
    desc: "模拟手动初稿的粗放感，句式不规则、表达更原始，AI 难以模仿",
  },
];

interface DetectModeOption {
  key: "rules" | "llm";
  label: string;
  desc: string;
  icon: React.ReactNode;
  tags: string[];
}

const DETECT_MODES: DetectModeOption[] = [
  {
    key: "rules",
    label: "规则引擎",
    desc: "5 维特征分析，即时出结果",
    icon: <ThunderboltOutlined />,
    tags: ["免费", "秒级"],
  },
  {
    key: "llm",
    label: "LLM 反查",
    desc: "大模型深度反查，模拟商业检测平台",
    icon: <RobotOutlined />,
    tags: ["消耗积分", "精准"],
  },
];

export default function NewTask() {
  const navigate = useNavigate();
  const { token: t } = theme.useToken();
  const { message } = AntApp.useApp();

  const [sourceType, setSourceType] = useState<"file" | "text">("text");
  const [textContent, setTextContent] = useState("");
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [detectMode, setDetectMode] = useState<"rules" | "llm">("rules");
  const [style, setStyle] = useState("学术人文化");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (sourceType === "text" && !textContent.trim()) {
      message.error("请输入论文内容");
      return;
    }
    if (sourceType === "file" && fileList.length === 0) {
      message.error("请上传文件");
      return;
    }

    setSubmitting(true);
    try {
      const task = await createTask({
        source_type: sourceType,
        detect_mode: detectMode,
        style,
        text: sourceType === "text" ? textContent : undefined,
        file:
          sourceType === "file" && fileList[0]?.originFileObj
            ? fileList[0].originFileObj
            : undefined,
      });
      message.success("任务创建成功");
      navigate(`/reduce/${task.id}`);
    } catch (err: unknown) {
      const detail = (
        err as { response?: { data?: { detail?: string } } }
      )?.response?.data?.detail;
      if (detail) message.error(detail);
    } finally {
      setSubmitting(false);
    }
  };

  const selected = (active: boolean) => ({
    cursor: "pointer" as const,
    transition: "all 0.2s",
    borderColor: active ? t.colorPrimary : t.colorBorderSecondary,
    boxShadow: active ? `0 0 0 1px ${t.colorPrimary}` : "none",
  });

  return (
    <div style={{ height: "calc(100vh - 120px)", display: "flex", flexDirection: "column" }}>
      <Row gutter={20} style={{ flex: 1, minHeight: 0 }}>
        {/* ── 左侧：输入源 ── */}
        <Col xs={24} lg={12} style={{ height: "100%", display: "flex", flexDirection: "column" }}>
          <Card
            title={
              <span><FileTextOutlined style={{ color: t.colorPrimary, marginRight: 6 }} />输入论文</span>
            }
            style={{ flex: 1, display: "flex", flexDirection: "column" }}
            styles={{ body: { flex: 1, display: "flex", flexDirection: "column", padding: 16 } }}
          >
            <Radio.Group
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
              style={{ marginBottom: 12 }}
              size="small"
            >
              <Radio.Button value="text">粘贴文本</Radio.Button>
              <Radio.Button value="file">上传文件</Radio.Button>
            </Radio.Group>

            {sourceType === "text" ? (
              <TextArea
                value={textContent}
                onChange={(e) => setTextContent(e.target.value)}
                placeholder="粘贴论文内容，段落间用空行分隔..."
                style={{ flex: 1, fontSize: 14, resize: "none" }}
              />
            ) : (
              <Upload.Dragger
                accept=".docx,.pdf,.doc,.md"
                maxCount={1}
                fileList={fileList}
                onChange={({ fileList: fl }) => setFileList(fl)}
                beforeUpload={() => false}
                style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}
                styles={{ body: { height: "100%" } }}
              >
                <UploadOutlined style={{ fontSize: 28, color: t.colorTextSecondary }} />
                <br />
                <Text style={{ marginTop: 8, display: "inline-block" }}>点击或拖拽文件到此处</Text>
                <br />
                <Text type="secondary" style={{ fontSize: 12 }}>
                  支持 .docx / .pdf / .doc / .md
                </Text>
              </Upload.Dragger>
            )}
          </Card>
        </Col>

        {/* ── 右侧：配置 ── */}
        <Col xs={24} lg={12} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* 检测模式 */}
          <Card
            title={
              <span><ThunderboltOutlined style={{ color: t.colorPrimary, marginRight: 6 }} />检测模式</span>
            }
            size="small"
            styles={{ body: { padding: 16 } }}
          >
            <div style={{ display: "flex", gap: 10 }}>
              {DETECT_MODES.map((mode) => {
                const active = detectMode === mode.key;
                return (
                  <Card
                    key={mode.key}
                    size="small"
                    hoverable
                    style={{ flex: 1, ...selected(active) }}
                    styles={{ body: { padding: 12 } }}
                    onClick={() => setDetectMode(mode.key)}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                      <span style={{ fontSize: 16, color: active ? t.colorPrimary : t.colorTextSecondary }}>
                        {mode.icon}
                      </span>
                      <Text strong style={{ fontSize: 13 }}>{mode.label}</Text>
                    </div>
                    <Paragraph type="secondary" style={{ fontSize: 11, marginBottom: 6, lineHeight: 1.4 }}>
                      {mode.desc}
                    </Paragraph>
                    <Space size={4}>
                      {mode.tags.map((tag) => (
                        <Tag key={tag} style={{ fontSize: 10, margin: 0, borderRadius: 3 }}>{tag}</Tag>
                      ))}
                    </Space>
                  </Card>
                );
              })}
            </div>
          </Card>

          {/* 改写风格 */}
          <Card
            title={
              <span><FormOutlined style={{ color: t.colorPrimary, marginRight: 6 }} />改写风格</span>
            }
            size="small"
            style={{ flex: 1 }}
            styles={{ body: { padding: 16 } }}
          >
            <Radio.Group
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              style={{ width: "100%" }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {STYLE_OPTIONS.map((s) => {
                  const active = style === s.key;
                  return (
                    <Card
                      key={s.key}
                      size="small"
                      hoverable
                      style={selected(active)}
                      styles={{ body: { padding: "8px 12px" } }}
                      onClick={() => setStyle(s.key)}
                    >
                      <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                        <Radio value={s.key} style={{ marginTop: 1 }} />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                            <Text strong style={{ fontSize: 13 }}>{s.label}</Text>
                            {s.tag && (
                              <Tag
                                color={t.colorPrimary}
                                style={{ fontSize: 9, lineHeight: "14px", padding: "0 4px", borderRadius: 3, margin: 0 }}
                              >
                                {s.tag}
                              </Tag>
                            )}
                          </div>
                          <Text type="secondary" style={{ fontSize: 11, lineHeight: 1.5 }}>
                            {s.desc}
                          </Text>
                        </div>
                      </div>
                    </Card>
                  );
                })}
              </div>
            </Radio.Group>
          </Card>

          {/* 提交按钮 */}
          <Button
            type="primary"
            size="large"
            block
            icon={<RocketOutlined />}
            loading={submitting}
            onClick={handleSubmit}
            style={{ height: 48, fontSize: 16, fontWeight: 600, borderRadius: 8, flexShrink: 0 }}
          >
            开始检测
          </Button>
        </Col>
      </Row>
    </div>
  );
}
