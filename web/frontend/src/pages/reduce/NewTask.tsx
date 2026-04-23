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
  Tabs,
  Tag,
  Typography,
  Upload,
  theme,
  Space,
} from "antd";
import {
  UploadOutlined,
  ThunderboltOutlined,
  RobotOutlined,
} from "@ant-design/icons";
import type { UploadFile } from "antd/es/upload/interface";
import { createTask } from "../../api/reduce";

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

// ---- 改写风格配置 ----

interface StyleOption {
  key: string;
  label: string;
  preview: string;
  tag?: string;
}

const STYLE_OPTIONS: StyleOption[] = [
  {
    key: "学术人文化",
    label: "学术人文化",
    tag: "推荐",
    preview:
      "本文通过梳理相关领域的理论脉络，结合实证分析的视角，尝试探讨该议题背后更深层次的逻辑...",
  },
  {
    key: "口语化",
    label: "口语化",
    preview:
      "说到底，这个问题其实挺值得琢磨的。我们可以从几个方面来看，首先是实际操作中的经验...",
  },
  {
    key: "文言文化",
    label: "文言文化",
    preview:
      "观此议题，渊源颇深。古云：知其然，亦当知其所以然。故循理而推，溯本求源...",
  },
  {
    key: "中英混杂化",
    label: "中英混杂化",
    preview:
      "从 perspective 来看，这个 issue 涉及到 methodology 的选择。基于 literature review 的发现...",
  },
  {
    key: "粗犷草稿风",
    label: "粗犷草稿风",
    preview:
      "大概就是那么个意思——先把问题摆出来，然后想办法解决。这里头有几个关键点...",
  },
];

// ---- 检测模式配置 ----

interface DetectModeOption {
  key: "rules" | "llm";
  label: string;
  description: string;
  icon: React.ReactNode;
  tags: string[];
}

const DETECT_MODES: DetectModeOption[] = [
  {
    key: "rules",
    label: "Rules 模式",
    description: "基于多维规则引擎，本地即时分析",
    icon: <ThunderboltOutlined style={{ fontSize: 24 }} />,
    tags: ["免费", "秒级完成"],
  },
  {
    key: "llm",
    label: "LLM 模式",
    description: "调用大语言模型深度反查，结果更精准",
    icon: <RobotOutlined style={{ fontSize: 24 }} />,
    tags: ["消耗积分", "更精准"],
  },
];

export default function NewTask() {
  const navigate = useNavigate();
  const { token: themeToken } = theme.useToken();
  const { message } = AntApp.useApp();

  // 表单状态
  const [sourceType, setSourceType] = useState<"file" | "text">("text");
  const [textContent, setTextContent] = useState("");
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [detectMode, setDetectMode] = useState<"rules" | "llm">("rules");
  const [style, setStyle] = useState("学术人文化");
  const [submitting, setSubmitting] = useState(false);

  // 提交
  const handleSubmit = async () => {
    // 校验
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
      message.success("任务创建成功，正在跳转...");
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

  // 卡片通用样式
  const cardStyle = (selected: boolean) => ({
    cursor: "pointer" as const,
    transition: "all 0.2s ease",
    borderColor: selected ? themeToken.colorPrimary : undefined,
    position: "relative" as const,
  });

  return (
    <div style={{ maxWidth: 1100, margin: "0 auto" }}>
      <Title level={4}>新建降重任务</Title>

      <Row gutter={24} style={{ marginTop: 16 }}>
        {/* ===== 左侧：输入源 ===== */}
        <Col xs={24} lg={14}>
          <Card
            title="输入源"
            styles={{ body: { padding: "16px 24px" } }}
            style={{ height: "100%" }}
          >
            <Tabs
              activeKey={sourceType}
              onChange={(key) => setSourceType(key as "file" | "text")}
              items={[
                {
                  key: "text",
                  label: (
                    <span>
                      <UploadOutlined style={{ marginRight: 6 }} />
                      文本粘贴
                    </span>
                  ),
                  children: (
                    <TextArea
                      value={textContent}
                      onChange={(e) => setTextContent(e.target.value)}
                      placeholder="粘贴论文内容..."
                      autoSize={{ minRows: 10, maxRows: 20 }}
                      style={{ fontSize: 14 }}
                    />
                  ),
                },
                {
                  key: "file",
                  label: (
                    <span>
                      <UploadOutlined style={{ marginRight: 6 }} />
                      文件上传
                    </span>
                  ),
                  children: (
                    <Upload.Dragger
                      accept=".docx,.pdf,.doc,.md"
                      maxCount={1}
                      fileList={fileList}
                      onChange={({ fileList: fl }) => setFileList(fl)}
                      beforeUpload={() => false}
                    >
                      <p style={{ marginBottom: 8 }}>
                        <UploadOutlined
                          style={{
                            fontSize: 32,
                            color: themeToken.colorTextSecondary,
                          }}
                        />
                      </p>
                      <Text>点击或拖拽文件到此处上传</Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        支持 .docx / .pdf / .doc / .md
                      </Text>
                    </Upload.Dragger>
                  ),
                },
              ]}
            />
          </Card>
        </Col>

        {/* ===== 右侧：配置 ===== */}
        <Col xs={24} lg={10} style={{ marginTop: 24 }}>
          {/* -- 检测模式 -- */}
          <Card
            title="检测模式"
            styles={{ body: { padding: "16px 20px" } }}
            style={{ marginBottom: 16 }}
          >
            <Row gutter={12}>
              {DETECT_MODES.map((mode) => (
                <Col span={12} key={mode.key}>
                  <Card
                    size="small"
                    hoverable
                    style={cardStyle(detectMode === mode.key)}
                    styles={{ body: { padding: 16 } }}
                    onClick={() => setDetectMode(mode.key)}
                  >
                    {/* 推荐角标（仅 LLM 模式） */}
                    {mode.key === "llm" && (
                      <Tag
                        color={themeToken.colorPrimary}
                        style={{
                          position: "absolute",
                          top: 8,
                          right: 8,
                          fontSize: 11,
                          lineHeight: "18px",
                          padding: "0 6px",
                          borderRadius: 4,
                        }}
                      >
                        推荐
                      </Tag>
                    )}

                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                        marginBottom: 8,
                      }}
                    >
                      <span
                        style={{
                          color:
                            detectMode === mode.key
                              ? themeToken.colorPrimary
                              : themeToken.colorTextSecondary,
                        }}
                      >
                        {mode.icon}
                      </span>
                      <Text strong>{mode.label}</Text>
                    </div>

                    <Paragraph
                      type="secondary"
                      style={{ fontSize: 12, marginBottom: 8, lineHeight: 1.5 }}
                    >
                      {mode.description}
                    </Paragraph>

                    <Space size={4}>
                      {mode.tags.map((tag) => (
                        <Tag
                          key={tag}
                          style={{
                            fontSize: 11,
                            margin: 0,
                            borderRadius: 4,
                          }}
                        >
                          {tag}
                        </Tag>
                      ))}
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>

          {/* -- 改写风格 -- */}
          <Card
            title="改写风格"
            styles={{ body: { padding: "16px 20px" } }}
            style={{ marginBottom: 16 }}
          >
            <Radio.Group
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              style={{ width: "100%" }}
            >
              <Row gutter={[12, 12]}>
                {STYLE_OPTIONS.map((s) => (
                  <Col span={24} key={s.key}>
                    <Card
                      size="small"
                      hoverable
                      style={cardStyle(style === s.key)}
                      styles={{ body: { padding: "12px 16px" } }}
                      onClick={() => setStyle(s.key)}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                          marginBottom: 6,
                        }}
                      >
                        <Radio value={s.key} />
                        <Text strong style={{ fontSize: 14 }}>
                          {s.label}
                        </Text>
                        {s.tag && (
                          <Tag
                            color={themeToken.colorPrimary}
                            style={{
                              fontSize: 10,
                              lineHeight: "16px",
                              padding: "0 5px",
                              borderRadius: 4,
                            }}
                          >
                            {s.tag}
                          </Tag>
                        )}
                      </div>
                      <Paragraph
                        type="secondary"
                        ellipsis={{ rows: 2 }}
                        style={{
                          fontSize: 12,
                          marginBottom: 0,
                          lineHeight: 1.6,
                          marginLeft: 30,
                        }}
                      >
                        {s.preview}
                      </Paragraph>
                    </Card>
                  </Col>
                ))}
              </Row>
            </Radio.Group>
          </Card>

          {/* -- 提交按钮 -- */}
          <Button
            type="primary"
            size="large"
            block
            loading={submitting}
            onClick={handleSubmit}
            style={{
              height: 48,
              fontSize: 16,
              fontWeight: 500,
              borderRadius: 8,
            }}
          >
            开始检测
          </Button>
        </Col>
      </Row>
    </div>
  );
}
