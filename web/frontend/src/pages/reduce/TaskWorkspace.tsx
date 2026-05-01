// web/frontend/src/pages/reduce/TaskWorkspace.tsx
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  App as AntApp,
  Button,
  Card,
  Col,
  Progress,
  Radio,
  Row,
  Space,
  Spin,
  Steps,
  Tag,
  Typography,
  theme,
  Input,
  Tooltip,
  Divider,
  Empty,
} from "antd";
import {
  CopyOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  LeftOutlined,
  RightOutlined,
  ThunderboltOutlined,
  UnorderedListOutlined,
  OrderedListOutlined,
  FileTextOutlined,
  ExpandAltOutlined,
  ShrinkOutlined,
} from "@ant-design/icons";
import {
  getTask,
  estimateCredits,
  connectSSE,
  confirmParagraph,
  finalizeTask,
  type TaskResponse,
  getExportUrl,
} from "../../api/reduce";
import {
  TASK_STATUS,
  TASK_STATUS_LABELS,
  RISK_LEVEL,
  RISK_LEVEL_LABELS,
  RISK_LEVEL_COLORS,
  PARAGRAPH_CHOICE,
  PARAGRAPH_CHOICE_LABELS,
  type ParagraphChoice,
} from "../../constants/reduce";

const { Title, Text } = Typography;
const { TextArea } = Input;

function riskColor(level: string, token: ReturnType<typeof theme.useToken>["token"]): string {
  switch (level) {
    case RISK_LEVEL.LOW:
      return token.colorSuccess;
    case RISK_LEVEL.MEDIUM:
      return token.colorInfo;
    case RISK_LEVEL.MEDIUM_HIGH:
      return token.colorWarning;
    case RISK_LEVEL.HIGH:
      return token.colorError;
    default:
      return token.colorTextTertiary;
  }
}

function riskTagColor(level: string): string {
  return RISK_LEVEL_COLORS[level] ?? "default";
}

// ---- 组件 ----

export default function TaskWorkspace() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { token: themeToken } = theme.useToken();
  const { message, modal } = AntApp.useApp();

  // ---- 核心状态 ----
  const [task, setTask] = useState<TaskResponse | null>(null);
  const [currentStep, setCurrentStep] = useState(0); // 0-4
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [reconstructing, setReconstructing] = useState(false);
  const [rewriting, setRewriting] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [sseController, setSseController] = useState<AbortController | null>(null);

  // ---- 检测阶段状态 ----
  const [detectProgress, setDetectProgress] = useState(0);
  const [detectCurrent, setDetectCurrent] = useState(0);
  const [detectTotal, setDetectTotal] = useState(0);

  // ---- 改写阶段状态 ----
  const [rewriteProgress, setRewriteProgress] = useState(0);
  const [rewriteCurrent, setRewriteCurrent] = useState(0);
  const [rewriteTotal, setRewriteTotal] = useState(0);
  const [reconProgress, setReconProgress] = useState(0);
  const [reconCurrent, setReconCurrent] = useState(0);
  const [reconTotal, setReconTotal] = useState(0);
  const [viewMode, setViewMode] = useState<"wizard" | "list">("list");
  const [wizardIndex, setWizardIndex] = useState(0);
  const [expandedCards, setExpandedCards] = useState<Set<number>>(new Set());
  const [paragraphChoices, setParagraphChoices] = useState<Map<number, ParagraphChoice>>(new Map());
  const [manualTexts, setManualTexts] = useState<Map<number, string>>(new Map());
  const [confirmingIndex, setConfirmingIndex] = useState<number | null>(null);

  // ---- 结果阶段状态 ----
  const [resultTask, setResultTask] = useState<TaskResponse | null>(null);

  // ---- 只读模式 ----
  const isReadonly = task ? [TASK_STATUS.COMPLETED, TASK_STATUS.FAILED].includes(task.status as typeof TASK_STATUS.COMPLETED) : false;

  // ---- 活动日志（用户可见的实时进度） ----
  const [activityLog, setActivityLog] = useState<string[]>([]);
  const logEndRef = useRef<HTMLDivElement | null>(null);
  const appendLog = useCallback((msg: string) => {
    const now = new Date().toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    setActivityLog((prev) => [...prev, `[${now}] ${msg}`]);
  }, []);

  // ---- 引用 ----
  const taskRef = useRef(task);
  taskRef.current = task;

  // ---- 初始化加载 ----
  useEffect(() => {
    if (!taskId) {
      message.error("无效的任务 ID");
      navigate("/dashboard");
      return;
    }

    loadTask();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);

  const loadTask = useCallback(async () => {
    setLoading(true);
    try {
      const t = await getTask(taskId);
      setTask(t);
      // 根据状态确定当前步骤
      syncStepFromStatus(t);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || "加载任务失败");
      navigate("/dashboard");
    } finally {
      setLoading(false);
    }
  }, [taskId, message, navigate]);

  const syncStepFromStatus = useCallback((t: TaskResponse) => {
    switch (t.status) {
      case TASK_STATUS.PARSING:
        setCurrentStep(0);
        break;
      case TASK_STATUS.DETECTING:
        setCurrentStep(1);
        break;
      case TASK_STATUS.DETECTED:
        setCurrentStep(1);
        break;
      case TASK_STATUS.REWRITING:
        setCurrentStep(3);
        break;
      case TASK_STATUS.REWRITTEN:
        setCurrentStep(3);
        break;
      case TASK_STATUS.COMPLETED:
        setCurrentStep(4);
        break;
      case TASK_STATUS.FAILED:
        // 保持当前步骤，显示错误
        break;
      default:
        setCurrentStep(0);
    }
  }, []);

  // ---- 自动启动检测 ----
  useEffect(() => {
    if (task && task.status === TASK_STATUS.DETECTING && !detecting && !sseController) {
      startDetection();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task?.status]);

  // ---- 自动启动改写 SSE ----
  useEffect(() => {
    if (task && task.status === TASK_STATUS.REWRITING && !rewriting && !sseController) {
      startRewriteSSE();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [task?.status]);

  // ---- 组件卸载 abort SSE ----
  useEffect(() => {
    return () => {
      sseController?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---- 日志自动滚动到底部 ----
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activityLog]);

  // ---- 检测 SSE ----
  const startDetection = useCallback(() => {
    setDetecting(true);
    setDetectProgress(0);
    setDetectCurrent(0);
    setDetectTotal(0);
    setActivityLog([]);
    appendLog("开始 AI 风险检测…");

    const ctrl = connectSSE(
      `/api/reduce/tasks/${taskId}/detect`,
      (data) => {
        if (data.type === "paragraph_done") {
          const idx = Number(data.index ?? 0);
          const current = Number(data.current ?? 0);
          const total = Number(data.total ?? 0);
          setDetectCurrent(current);
          setDetectTotal(total);
          if (total > 0) setDetectProgress(Math.round((current / total) * 100));
          const riskLabel = RISK_LEVEL_LABELS[String(data.risk_level ?? RISK_LEVEL.LOW)] ?? "";
          appendLog(`第 ${idx + 1} 段检测完成：${riskLabel}（综合分 ${data.composite_score ?? 0}）`);

          // 更新段落风险
          setTask((prev) => {
            if (!prev) return prev;
            const newParagraphs = [...prev.paragraphs];
            if (newParagraphs[idx]) {
              newParagraphs[idx] = {
                ...newParagraphs[idx],
                risk_level: String(data.risk_level ?? RISK_LEVEL.LOW),
                composite_score: data.composite_score != null ? Number(data.composite_score) : null,
                status: TASK_STATUS.DETECTED,
              };
            }
            return { ...prev, paragraphs: newParagraphs };
          });
        } else if (data.type === "complete") {
          ctrl.abort();
          setSseController(null);
          setDetecting(false);
          setDetectProgress(100);
          appendLog(`检测完成，${data.needs_processing ?? 0} 段需要改写`);
          // 刷新任务
          getTask(taskId).then((t) => {
            setTask(t);
            syncStepFromStatus(t);
          });
          message.success("检测完成");
        } else if (data.type === "error") {
          ctrl.abort();
          setSseController(null);
          setDetecting(false);
          appendLog(`检测出错：${data.message ?? "未知错误"}`);
          message.error(String(data.message ?? "检测失败"));
        }
      },
      (error) => {
        setSseController(null);
        setDetecting(false);
        appendLog(`检测连接失败：${error}`);
        message.error(error || "检测连接失败");
      },
    );
    setSseController(ctrl);
  }, [taskId, message, syncStepFromStatus]);

  // ---- 全量重构 ----
  const handleReconstruct = useCallback(async () => {
    try {
      const est = await estimateCredits(taskId, "reconstruct");
      modal.confirm({
        title: "确认全量语义重构",
        icon: <ExclamationCircleOutlined />,
        content: (
          <div>
            <p>
              预估消耗积分：<Text strong>{est.estimated_credits}</Text>
            </p>
            <p>
              当前余额：
              <Text strong style={{ color: est.sufficient ? themeToken.colorSuccess : themeToken.colorError }}>
                {est.current_balance}
              </Text>
            </p>
            {!est.sufficient && <p style={{ color: themeToken.colorError }}>余额不足，请先充值</p>}
          </div>
        ),
        okText: "确认重构",
        cancelText: "取消",
        okButtonProps: { disabled: !est.sufficient },
        onOk: () => startReconstruct(),
      });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || "预估积分失败");
    }
  }, [taskId, message, modal, themeToken]);

  const startReconstruct = useCallback(() => {
    setReconstructing(true);
    setCurrentStep(2);
    setActivityLog([]);
    appendLog("开始全量语义重构…");
    const ctrl = connectSSE(
      `/api/reduce/tasks/${taskId}/reconstruct`,
      async (data) => {
        if (data.type === "progress") {
          const current = Number(data.current ?? 0);
          const total = Number(data.total ?? 0);
          const idx = Number(data.index ?? 0);
          setReconProgress(Math.round((current / total) * 100));
          setReconCurrent(current);
          setReconTotal(total);
          appendLog(`第 ${idx + 1} 段重构完成 (${current}/${total})`);
        } else if (data.type === "complete") {
          ctrl.abort();
          setSseController(null);
          setReconstructing(false);
          setReconProgress(100);
          appendLog(`重构完成，消耗积分 ${data.credits_used ?? 0}`);
          const t = await getTask(taskId);
          setTask(t);
          setCurrentStep(1);
          message.success(`重构完成，消耗积分 ${data.credits_used ?? 0}`);
        } else if (data.type === "error") {
          ctrl.abort();
          setSseController(null);
          setReconstructing(false);
          appendLog(`重构出错：${data.message ?? "未知错误"}`);
          message.error(String(data.message ?? "重构失败"));
        }
      },
      (error) => {
        setSseController(null);
        setReconstructing(false);
        appendLog(`重构连接失败：${error}`);
        message.error(error || "重构连接失败");
      },
    );
    setSseController(ctrl);
  }, [taskId, message]);

  // ---- 改写 SSE ----
  const handleStartRewrite = useCallback(async () => {
    try {
      const est = await estimateCredits(taskId, "rewrite");
      modal.confirm({
        title: "确认开始改写",
        icon: <ExclamationCircleOutlined />,
        content: (
          <div>
            <p>
              预估消耗积分：<Text strong>{est.estimated_credits}</Text>
            </p>
            <p>
              当前余额：
              <Text strong style={{ color: est.sufficient ? themeToken.colorSuccess : themeToken.colorError }}>
                {est.current_balance}
              </Text>
            </p>
            {!est.sufficient && <p style={{ color: themeToken.colorError }}>余额不足，请先充值</p>}
          </div>
        ),
        okText: "开始改写",
        cancelText: "取消",
        okButtonProps: { disabled: !est.sufficient },
        onOk: () => startRewriteSSE(),
      });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || "预估积分失败");
    }
  }, [taskId, message, modal, themeToken]);

  const startRewriteSSE = useCallback(() => {
    setRewriting(true);
    setRewriteProgress(0);
    setRewriteCurrent(0);
    setRewriteTotal(0);
    // 同步更新 task 状态和步骤，确保 UI 立即切换到改写进度
    setCurrentStep(3);
    setTask((prev) => prev ? { ...prev, status: TASK_STATUS.REWRITING } : prev);

    const ctrl = connectSSE(
      `/api/reduce/tasks/${taskId}/rewrite`,
      (data) => {
        if (data.type === "progress") {
          const current = Number(data.current ?? 0);
          const total = Number(data.total ?? 0);
          setRewriteCurrent(current);
          setRewriteTotal(total);
          if (total > 0) setRewriteProgress(Math.round((current / total) * 100));
          appendLog(`正在为第 ${current}/${total} 段生成改写方案 A（激进）和方案 B（保守）…`);
        } else if (data.type === "paragraph_ready") {
          const idx = Number(data.index ?? 0);
          const aggressive = String(data.aggressive ?? "");
          const conservative = String(data.conservative ?? "");
          appendLog(`第 ${idx + 1} 段改写完成，方案 A ${aggressive.length} 字，方案 B ${conservative.length} 字`);
          setTask((prev) => {
            if (!prev) return prev;
            const newParagraphs = [...prev.paragraphs];
            if (newParagraphs[idx]) {
              newParagraphs[idx] = {
                ...newParagraphs[idx],
                rewrite_aggressive: aggressive,
                rewrite_conservative: conservative,
                status: TASK_STATUS.REWRITTEN,
              };
            }
            return { ...prev, paragraphs: newParagraphs };
          });
        } else if (data.type === "complete") {
          ctrl.abort();
          setSseController(null);
          setRewriting(false);
          setRewriteProgress(100);
          appendLog(`全部改写完成，共消耗积分 ${data.total_credits_used ?? 0}`);
          // 刷新完整任务状态
          getTask(taskId).then((t) => {
            setTask(t);
            syncStepFromStatus(t);
          });
          message.success(`改写完成，消耗积分 ${data.total_credits_used ?? 0}`);
        } else if (data.type === "error") {
          ctrl.abort();
          setSseController(null);
          setRewriting(false);
          appendLog(`改写出错：${data.message ?? "未知错误"}`);
          message.error(String(data.message ?? "改写失败"));
        }
      },
      (error) => {
        setSseController(null);
        setRewriting(false);
        message.error(error || "改写连接失败");
      },
    );
    setSseController(ctrl);
  }, [taskId, message, syncStepFromStatus]);

  // ---- 确认段落选择 ----
  const handleConfirmParagraph = useCallback(
    async (index: number, choice: ParagraphChoice) => {
      setConfirmingIndex(index);
      try {
        let manualText: string | undefined;
        if (choice === PARAGRAPH_CHOICE.MANUAL) {
          manualText = manualTexts.get(index);
          if (!manualText?.trim()) {
            message.error("请输入手动改写内容");
            setConfirmingIndex(null);
            return;
          }
        }
        await confirmParagraph(taskId, index, choice, manualText);
        setParagraphChoices((prev) => new Map(prev).set(index, choice));
        // 同步更新 task 中的 user_choice，使 allConfirmed 正确计算
        setTask((prev) => {
          if (!prev) return prev;
          const newParagraphs = [...prev.paragraphs];
          if (newParagraphs[index]) {
            newParagraphs[index] = { ...newParagraphs[index], user_choice: choice, status: "confirmed" };
          }
          return { ...prev, paragraphs: newParagraphs };
        });
        message.success(`段落 ${index + 1} 已确认`);
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        message.error(detail || "确认段落失败");
      } finally {
        setConfirmingIndex(null);
      }
    },
    [taskId, message, manualTexts],
  );

  // ---- 完成任务 ----
  const handleFinalize = useCallback(async () => {
    setFinalizing(true);
    try {
      const t = await finalizeTask(taskId);
      setTask(t);
      setResultTask(t);
      setCurrentStep(4);
      message.success("任务完成");
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || "生成最终文档失败");
    } finally {
      setFinalizing(false);
    }
  }, [taskId, message]);

  // ---- 批量选择 ----
  const handleBatchChoice = useCallback(
    (choice: PARAGRAPH_CHOICE.AGGRESSIVE | PARAGRAPH_CHOICE.CONSERVATIVE) => {
      if (!task) return;
      const paragraphsNeedingRewrite = task.paragraphs.filter(
        (p) => p.status === TASK_STATUS.REWRITTEN && p.risk_level && p.risk_level !== RISK_LEVEL.LOW,
      );
      const promises = paragraphsNeedingRewrite.map((p) =>
        confirmParagraph(taskId, p.index, choice).then(() => p.index),
      );
      Promise.allSettled(promises).then((results) => {
        const newChoices = new Map(paragraphChoices);
        let successCount = 0;
        results.forEach((r, i) => {
          if (r.status === "fulfilled") {
            newChoices.set(paragraphsNeedingRewrite[i].index, choice);
            successCount++;
          }
        });
        setParagraphChoices(newChoices);
        message.success(`已批量选择 ${successCount} 段`);
      });
    },
    [task, taskId, message, paragraphChoices],
  );

  // ---- 复制文本 ----
  const copyText = useCallback(
    (text: string, label: string) => {
      navigator.clipboard.writeText(text).then(
        () => message.success(`${label}已复制`),
        () => message.error("复制失败"),
      );
    },
    [message],
  );

  // ---- 展开/收起所有段落 ----
  const toggleExpandAll = useCallback(() => {
    if (!task) return;
    if (expandedCards.size === task.paragraphs.length) {
      setExpandedCards(new Set());
    } else {
      setExpandedCards(new Set(task.paragraphs.map((p) => p.index)));
    }
  }, [task, expandedCards]);

  // ---- 统计 ----
  const stats = useMemo(() => {
    if (!task) return { low: 0, medium: 0, medium_high: 0, high: 0, needsProcessing: 0, total: 0 };
    const counts = { low: 0, medium: 0, medium_high: 0, high: 0, needsProcessing: 0, total: task.paragraphs.length };
    for (const p of task.paragraphs) {
      const lvl = p.risk_level ?? RISK_LEVEL.LOW;
      if (lvl in counts) {
        (counts as Record<string, number>)[lvl]++;
      }
      if (lvl !== RISK_LEVEL.LOW && lvl !== null) counts.needsProcessing++;
    }
    return counts;
  }, [task]);

  const allConfirmed = useMemo(() => {
    if (!task) return false;
    const needsProcessing = task.paragraphs.filter(
      (p) => p.risk_level && p.risk_level !== RISK_LEVEL.LOW,
    );
    if (needsProcessing.length === 0) {
      // 所有段落低风险或无检测结果时，可以直接 finalize
      return task.status === TASK_STATUS.DETECTED || task.status === TASK_STATUS.REWRITTEN;
    }
    return needsProcessing.every((p) => !!p.user_choice);
  }, [task]);

  const paragraphsNeedingReview = useMemo(() => {
    if (!task) return [];
    return task.paragraphs.filter(
      (p) => p.risk_level && p.risk_level !== RISK_LEVEL.LOW && p.status === TASK_STATUS.REWRITTEN,
    );
  }, [task]);

  // ---- 向导模式导航 ----
  const currentWizardPara = useMemo(() => {
    if (paragraphsNeedingReview.length === 0) return null;
    return paragraphsNeedingReview[wizardIndex] ?? null;
  }, [paragraphsNeedingReview, wizardIndex]);

  // ---- Steps ----
  const steps = [
    { title: "解析" },
    { title: "检测" },
    { title: "重构" },
    { title: "改写" },
    { title: "结果" },
  ];

  // ---- 加载中 ----
  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "120px 0" }}>
        <Spin size="large" tip="加载任务..." />
      </div>
    );
  }

  if (!task) {
    return (
      <div style={{ textAlign: "center", padding: "120px 0" }}>
        <Empty description="任务不存在" />
        <Button type="primary" onClick={() => navigate("/dashboard")} style={{ marginTop: 16 }}>
          返回仪表盘
        </Button>
      </div>
    );
  }

  // ---- 步骤渲染 ----

  const renderDetectStep = () => (
    <div>
      {detecting && (
        <Card style={{ marginBottom: 16, textAlign: "center", padding: 24 }}>
          <Progress
            percent={detectProgress}
            status={detectProgress < 100 ? "active" : "success"}
            style={{ maxWidth: 400, margin: "0 auto 12px" }}
          />
          <Text type="secondary">
            正在检测 {detectCurrent}/{detectTotal} 段...
          </Text>
          {activityLog.length > 0 && (
            <div
              className="activity-log"
              style={{
                marginTop: 16,
                textAlign: "left",
                maxHeight: 200,
                overflow: "auto",
                padding: "8px 12px",
                background: themeToken.colorBgLayout,
                borderRadius: 6,
                fontSize: 12,
                lineHeight: 1.8,
                fontFamily: "monospace",
                color: themeToken.colorTextSecondary,
              }}
            >
              {activityLog.map((line, i) => (
                <div key={i}>{line}</div>
              ))}
              <div ref={logEndRef} />
            </div>
          )}
        </Card>
      )}

      {/* 段落风险列表 */}
      <Card
        title="段落检测结果"
        style={{ marginBottom: 16 }}
        extra={
          !detecting && task.status === TASK_STATUS.DETECTED && (
            <Space>
              <Tag color="success">{stats.low} 段低风险</Tag>
              <Tag color="warning">{stats.needsProcessing} 段需处理</Tag>
            </Space>
          )
        }
      >
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {task.paragraphs.map((p) => {
            const color = p.risk_level ? riskColor(p.risk_level, themeToken) : themeToken.colorTextTertiary;
            return (
              <div
                key={p.index}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  padding: "8px 12px",
                  borderRadius: 6,
                  borderLeft: `3px solid ${color}`,
                  background: themeToken.colorBgContainer,
                }}
              >
                <Text strong style={{ minWidth: 32 }}>
                  #{p.index + 1}
                </Text>
                {p.is_heading && <Tag style={{ fontSize: 11 }}>标题</Tag>}
                <Tag color={riskTagColor(p.risk_level ?? RISK_LEVEL.LOW)} style={{ margin: 0 }}>
                  {RISK_LEVEL_LABELS[p.risk_level ?? RISK_LEVEL.LOW] ?? p.risk_level ?? "低风险"}
                </Tag>
                {p.composite_score != null && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    综合分: {p.composite_score}
                  </Text>
                )}
                <Text
                  ellipsis
                  style={{
                    flex: 1,
                    fontSize: 13,
                    color: themeToken.colorTextSecondary,
                  }}
                >
                  {p.original_text.slice(0, 100)}
                  {p.original_text.length > 100 ? "..." : ""}
                </Text>
              </div>
            );
          })}
        </div>
      </Card>

      {/* 检测完成后操作按钮 */}
      {!detecting && task.status === TASK_STATUS.DETECTED && (
        <Card>
          <Space>
            <Button
              icon={<ThunderboltOutlined />}
              onClick={handleReconstruct}
              loading={reconstructing}
            >
              全量语义重构
            </Button>
            <Button type="primary" onClick={handleStartRewrite}>
              开始改写
            </Button>
          </Space>
          <Text type="secondary" style={{ display: "block", marginTop: 8, fontSize: 12 }}>
            全量语义重构为可选步骤，可跳过直接改写
          </Text>
        </Card>
      )}
    </div>
  );

  const renderReconstructStep = () => (
    <div>
      {reconstructing && (
        <Card style={{ marginBottom: 16, textAlign: "center", padding: 24 }}>
          <Progress
            percent={reconProgress}
            status={reconProgress < 100 ? "active" : "success"}
            style={{ maxWidth: 400, margin: "0 auto 12px" }}
          />
          <Text type="secondary">
            正在重构 {reconCurrent}/{reconTotal} 段...
          </Text>
          {activityLog.length > 0 && (
            <div
              className="activity-log"
              style={{
                marginTop: 16,
                textAlign: "left",
                maxHeight: 240,
                overflow: "auto",
                padding: "8px 12px",
                background: themeToken.colorBgLayout,
                borderRadius: 6,
                fontSize: 12,
                lineHeight: 1.8,
                fontFamily: "monospace",
                color: themeToken.colorTextSecondary,
              }}
            >
              {activityLog.map((line, i) => (
                <div key={i}>{line}</div>
              ))}
              <div ref={logEndRef} />
            </div>
          )}
        </Card>
      )}

      {!reconstructing && task.full_reconstruct && (
        <div style={{ textAlign: "center", padding: "40px 0" }}>
          <CheckCircleOutlined
            style={{ fontSize: 48, color: themeToken.colorSuccess, marginBottom: 16 }}
          />
          <Title level={5}>重构完成</Title>
          <Button type="primary" onClick={handleStartRewrite} style={{ marginTop: 16 }}>
            开始改写
          </Button>
        </div>
      )}
    </div>
  );

  const renderRewriteStep = () => {
    // 改写进行中
    if (rewriting && task.status === TASK_STATUS.REWRITING) {
      return (
        <Card style={{ textAlign: "center", padding: 32 }}>
          <Progress
            percent={rewriteProgress}
            status={rewriteProgress < 100 ? "active" : "success"}
            style={{ maxWidth: 400, margin: "0 auto 12px" }}
          />
          <Text type="secondary">
            正在生成改写方案 {rewriteCurrent}/{rewriteTotal} 段...
          </Text>
          {activityLog.length > 0 && (
            <div
              className="activity-log"
              style={{
                marginTop: 20,
                textAlign: "left",
                maxHeight: 280,
                overflow: "auto",
                padding: "12px 16px",
                background: themeToken.colorBgLayout,
                borderRadius: 8,
                fontSize: 12,
                lineHeight: 2,
                fontFamily: "monospace",
                color: themeToken.colorTextSecondary,
              }}
            >
              {activityLog.map((line, i) => (
                <div key={i}>{line}</div>
              ))}
              <div ref={logEndRef} />
            </div>
          )}
        </Card>
      );
    }

    // 审阅模式
    if (task.status === TASK_STATUS.REWRITTEN || (paragraphsNeedingReview.length > 0 && !rewriting)) {
      return (
        <div>
          {/* 工具栏 */}
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space>
              <Radio.Group
                value={viewMode}
                onChange={(e) => setViewMode(e.target.value)}
                optionType="button"
                buttonStyle="solid"
                size="small"
              >
                <Radio.Button value="list">
                  <UnorderedListOutlined /> 列表模式
                </Radio.Button>
                <Radio.Button value="wizard">
                  <OrderedListOutlined /> 向导模式
                </Radio.Button>
              </Radio.Group>
              {viewMode === "list" && (
                <>
                  <Tooltip title={expandedCards.size === paragraphsNeedingReview.length ? "全部收起" : "全部展开"}>
                    <Button
                      size="small"
                      icon={expandedCards.size === paragraphsNeedingReview.length ? <ShrinkOutlined /> : <ExpandAltOutlined />}
                      onClick={toggleExpandAll}
                    />
                  </Tooltip>
                  <Button size="small" onClick={() => handleBatchChoice(PARAGRAPH_CHOICE.AGGRESSIVE)}>
                    全选方案 A（激进）
                  </Button>
                  <Button size="small" onClick={() => handleBatchChoice(PARAGRAPH_CHOICE.CONSERVATIVE)}>
                    全选方案 B（保守）
                  </Button>
                </>
              )}
            </Space>
          </Card>

          {/* 列表模式 */}
          {viewMode === "list" && renderListMode()}

          {/* 向导模式 */}
          {viewMode === "wizard" && renderWizardMode()}

          {/* 生成最终文档 */}
          {allConfirmed && (
            <Card style={{ textAlign: "center", marginTop: 16, padding: 16 }}>
              <Button
                type="primary"
                size="large"
                icon={<DownloadOutlined />}
                loading={finalizing}
                onClick={handleFinalize}
              >
                生成最终文档
              </Button>
            </Card>
          )}
        </div>
      );
    }

    return (
      <div style={{ textAlign: "center", padding: "60px 0" }}>
        <Text type="secondary">等待改写...</Text>
      </div>
    );
  };

  const renderListMode = () => (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {paragraphsNeedingReview.map((p) => {
        const isExpanded = expandedCards.has(p.index);
        const confirmed = !!p.user_choice;
        const choice = paragraphChoices.get(p.index) ?? (p.user_choice as ParagraphChoice | undefined);

        return (
          <Card
            key={p.index}
            size="small"
            style={{
              borderLeft: `3px solid ${riskColor(p.risk_level ?? RISK_LEVEL.LOW, themeToken)}`,
              opacity: confirmed ? 0.7 : 1,
            }}
          >
            {/* 标题行 */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                cursor: "pointer",
              }}
              onClick={() => {
                setExpandedCards((prev) => {
                  const next = new Set(prev);
                  if (next.has(p.index)) next.delete(p.index);
                  else next.add(p.index);
                  return next;
                });
              }}
            >
              <Text strong>
                段落 #{p.index + 1}
              </Text>
              <Tag color={riskTagColor(p.risk_level ?? RISK_LEVEL.LOW)} style={{ margin: 0 }}>
                {RISK_LEVEL_LABELS[p.risk_level ?? RISK_LEVEL.LOW]}
              </Tag>
              {p.composite_score != null && (
                <Text type="secondary" style={{ fontSize: 12 }}>
                  综合分: {p.composite_score}
                </Text>
              )}
              {confirmed && (
                <Tag color="success" style={{ marginLeft: "auto" }}>
                  <CheckCircleOutlined /> 已确认
                </Tag>
              )}
            </div>

            {/* 展开内容 */}
            {isExpanded && (
              <div style={{ marginTop: 12 }}>
                {/* 原文 */}
                <div style={{ marginBottom: 16 }}>
                  <Text type="secondary" style={{ fontSize: 12, fontWeight: 500 }}>原文</Text>
                  <div
                    style={{
                      padding: 12,
                      marginTop: 4,
                      background: themeToken.colorBgLayout,
                      borderRadius: 6,
                      fontSize: 13,
                      lineHeight: 1.8,
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {p.original_text}
                  </div>
                </div>

                {/* 方案选择 */}
                <Radio.Group
                  value={choice ?? null}
                  onChange={(e) => {
                    const selected = e.target.value as ParagraphChoice;
                    setParagraphChoices((prev) => new Map(prev).set(p.index, selected));
                  }}
                  style={{ width: "100%" }}
                >
                  <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                    {/* 方案 A */}
                    <div
                      style={{
                        padding: 12,
                        background: themeToken.colorBgLayout,
                        borderRadius: 6,
                        border: choice === PARAGRAPH_CHOICE.AGGRESSIVE ? `1px solid ${themeToken.colorPrimary}` : "1px solid transparent",
                      }}
                    >
                      <Radio value={PARAGRAPH_CHOICE.AGGRESSIVE} disabled={confirmed && choice !== PARAGRAPH_CHOICE.AGGRESSIVE}>
                        <Text strong style={{ color: themeToken.colorPrimary }}>方案 A（激进）</Text>
                      </Radio>
                      {p.rewrite_aggressive && (
                        <div
                          style={{
                            marginTop: 8,
                            fontSize: 13,
                            lineHeight: 1.8,
                            whiteSpace: "pre-wrap",
                            color: themeToken.colorTextSecondary,
                          }}
                        >
                          {p.rewrite_aggressive}
                        </div>
                      )}
                    </div>

                    {/* 方案 B */}
                    <div
                      style={{
                        padding: 12,
                        background: themeToken.colorBgLayout,
                        borderRadius: 6,
                        border: choice === PARAGRAPH_CHOICE.CONSERVATIVE ? `1px solid ${themeToken.colorPrimary}` : "1px solid transparent",
                      }}
                    >
                      <Radio value={PARAGRAPH_CHOICE.CONSERVATIVE} disabled={confirmed && choice !== PARAGRAPH_CHOICE.CONSERVATIVE}>
                        <Text strong style={{ color: themeToken.colorInfo }}>方案 B（保守）</Text>
                      </Radio>
                      {p.rewrite_conservative && (
                        <div
                          style={{
                            marginTop: 8,
                            fontSize: 13,
                            lineHeight: 1.8,
                            whiteSpace: "pre-wrap",
                            color: themeToken.colorTextSecondary,
                          }}
                        >
                          {p.rewrite_conservative}
                        </div>
                      )}
                    </div>

                    {/* 保留原文 */}
                    <div
                      style={{
                        padding: 12,
                        background: themeToken.colorBgLayout,
                        borderRadius: 6,
                        border: choice === PARAGRAPH_CHOICE.ORIGINAL ? `1px solid ${themeToken.colorPrimary}` : "1px solid transparent",
                      }}
                    >
                      <Radio value={PARAGRAPH_CHOICE.ORIGINAL} disabled={confirmed && choice !== PARAGRAPH_CHOICE.ORIGINAL}>
                        <Text strong>保留原文</Text>
                      </Radio>
                    </div>

                    {/* 手动输入 */}
                    <div
                      style={{
                        padding: 12,
                        background: themeToken.colorBgLayout,
                        borderRadius: 6,
                        border: choice === PARAGRAPH_CHOICE.MANUAL ? `1px solid ${themeToken.colorPrimary}` : "1px solid transparent",
                      }}
                    >
                      <Radio value={PARAGRAPH_CHOICE.MANUAL} disabled={confirmed && choice !== PARAGRAPH_CHOICE.MANUAL}>
                        <Text strong>手动输入</Text>
                      </Radio>
                      {choice === PARAGRAPH_CHOICE.MANUAL && !confirmed && (
                        <div style={{ marginTop: 8 }}>
                          <TextArea
                            rows={4}
                            placeholder="输入你的改写内容..."
                            value={manualTexts.get(p.index) ?? ""}
                            onChange={(e) =>
                              setManualTexts((prev) => new Map(prev).set(p.index, e.target.value))
                            }
                          />
                          <Button
                            size="small"
                            type="primary"
                            style={{ marginTop: 8 }}
                            loading={confirmingIndex === p.index}
                            onClick={() => handleConfirmParagraph(p.index, PARAGRAPH_CHOICE.MANUAL)}
                          >
                            确认
                          </Button>
                        </div>
                      )}
                    </div>
                  </div>
                </Radio.Group>
              </div>
            )}
          </Card>
        );
      })}
      {/* 全部已选择后显示统一提交按钮 */}
      {paragraphsNeedingReview.length > 0 &&
        paragraphsNeedingReview.every((p) => paragraphChoices.has(p.index) || p.user_choice) &&
        !paragraphsNeedingReview.every((p) => !!p.user_choice) && (
        <Card style={{ textAlign: "center", padding: 16 }}>
          <Button
            type="primary"
            size="large"
            loading={confirmingIndex !== null}
            onClick={async () => {
              for (const p of paragraphsNeedingReview) {
                if (p.user_choice) continue;
                const c = paragraphChoices.get(p.index);
                if (c) await handleConfirmParagraph(p.index, c);
              }
            }}
          >
            确认提交
          </Button>
        </Card>
      )}
    </div>
  );

  const renderWizardMode = () => {
    if (!currentWizardPara) {
      return (
        <Empty description="所有段落已审阅完成" />
      );
    }

    const p = currentWizardPara;
    const confirmed = !!p.user_choice;
    const choice = paragraphChoices.get(p.index) ?? (p.user_choice as ParagraphChoice | undefined);

    return (
      <div>
        <div style={{ textAlign: "center", marginBottom: 16 }}>
          <Text type="secondary">
            {wizardIndex + 1} / {paragraphsNeedingReview.length} 段
          </Text>
          <Progress
            percent={Math.round(((wizardIndex + 1) / paragraphsNeedingReview.length) * 100)}
            size="small"
            showInfo={false}
            style={{ maxWidth: 300, margin: "8px auto 0" }}
          />
        </div>

        <Row gutter={24}>
          {/* 左侧原文 */}
          <Col span={12}>
            <Card
              title="原文"
              size="small"
              style={{ height: "100%" }}
              extra={
                <Tag color={riskTagColor(p.risk_level ?? RISK_LEVEL.LOW)}>
                  {RISK_LEVEL_LABELS[p.risk_level ?? RISK_LEVEL.LOW]} {p.composite_score != null ? `(${p.composite_score})` : ""}
                </Tag>
              }
            >
              <div
                style={{
                  fontSize: 13,
                  lineHeight: 1.8,
                  whiteSpace: "pre-wrap",
                  maxHeight: 400,
                  overflow: "auto",
                }}
              >
                {p.original_text}
              </div>
            </Card>
          </Col>

          {/* 右侧 A/B 对比 */}
          <Col span={12}>
            <Card title="改写方案" size="small" style={{ height: "100%" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {/* 方案 A */}
                <div
                  style={{
                    padding: 12,
                    borderRadius: 6,
                    border:
                      choice === PARAGRAPH_CHOICE.AGGRESSIVE
                        ? `2px solid ${themeToken.colorPrimary}`
                        : `1px solid ${themeToken.colorBorderSecondary}`,
                    cursor: confirmed ? "default" : "pointer",
                  }}
                  onClick={() => {
                    if (!confirmed) setParagraphChoices((prev) => new Map(prev).set(p.index, PARAGRAPH_CHOICE.AGGRESSIVE));
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <Text strong style={{ color: themeToken.colorPrimary }}>方案 A（激进）</Text>
                    {choice === PARAGRAPH_CHOICE.AGGRESSIVE && <CheckCircleOutlined style={{ color: themeToken.colorSuccess }} />}
                  </div>
                  <div
                    style={{
                      fontSize: 13,
                      lineHeight: 1.8,
                      whiteSpace: "pre-wrap",
                      color: themeToken.colorTextSecondary,
                      maxHeight: 140,
                      overflow: "auto",
                    }}
                  >
                    {p.rewrite_aggressive ?? "生成中..."}
                  </div>
                </div>

                {/* 方案 B */}
                <div
                  style={{
                    padding: 12,
                    borderRadius: 6,
                    border:
                      choice === PARAGRAPH_CHOICE.CONSERVATIVE
                        ? `2px solid ${themeToken.colorPrimary}`
                        : `1px solid ${themeToken.colorBorderSecondary}`,
                    cursor: confirmed ? "default" : "pointer",
                  }}
                  onClick={() => {
                    if (!confirmed) setParagraphChoices((prev) => new Map(prev).set(p.index, PARAGRAPH_CHOICE.CONSERVATIVE));
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <Text strong style={{ color: themeToken.colorInfo }}>方案 B（保守）</Text>
                    {choice === PARAGRAPH_CHOICE.CONSERVATIVE && <CheckCircleOutlined style={{ color: themeToken.colorSuccess }} />}
                  </div>
                  <div
                    style={{
                      fontSize: 13,
                      lineHeight: 1.8,
                      whiteSpace: "pre-wrap",
                      color: themeToken.colorTextSecondary,
                      maxHeight: 140,
                      overflow: "auto",
                    }}
                  >
                    {p.rewrite_conservative ?? "生成中..."}
                  </div>
                </div>

                {/* 保留原文 + 手动输入 */}
                <Space>
                  <Button
                    size="small"
                    onClick={() => setParagraphChoices((prev) => new Map(prev).set(p.index, PARAGRAPH_CHOICE.ORIGINAL))}
                    disabled={confirmed}
                    type={choice === PARAGRAPH_CHOICE.ORIGINAL ? "primary" : "default"}
                  >
                    保留原文
                  </Button>
                  <Button
                    size="small"
                    onClick={() => {
                      setParagraphChoices((prev) => new Map(prev).set(p.index, PARAGRAPH_CHOICE.MANUAL));
                    }}
                    disabled={confirmed}
                    type={choice === PARAGRAPH_CHOICE.MANUAL ? "primary" : "default"}
                  >
                    手动输入
                  </Button>
                </Space>
                {choice === PARAGRAPH_CHOICE.MANUAL && !confirmed && (
                  <div style={{ marginTop: 8 }}>
                    <TextArea
                      rows={3}
                      placeholder="输入你的改写内容..."
                      value={manualTexts.get(p.index) ?? ""}
                      onChange={(e) =>
                        setManualTexts((prev) => new Map(prev).set(p.index, e.target.value))
                      }
                    />
                    <Button
                      size="small"
                      type="primary"
                      style={{ marginTop: 8 }}
                      loading={confirmingIndex === p.index}
                      onClick={() => handleConfirmParagraph(p.index, PARAGRAPH_CHOICE.MANUAL)}
                    >
                      确认
                    </Button>
                  </div>
                )}
              </div>
            </Card>
          </Col>
        </Row>

        {/* 导航 + 提交按钮 */}
        <div style={{ display: "flex", justifyContent: "center", gap: 16, marginTop: 16 }}>
          <Button
            icon={<LeftOutlined />}
            disabled={wizardIndex === 0}
            onClick={() => setWizardIndex((i) => Math.max(0, i - 1))}
          >
            上一段
          </Button>
          {wizardIndex === paragraphsNeedingReview.length - 1 &&
            paragraphsNeedingReview.every((pp) => paragraphChoices.has(pp.index) || pp.user_choice) &&
            !paragraphsNeedingReview.every((pp) => !!pp.user_choice) && (
            <Button
              type="primary"
              loading={confirmingIndex !== null}
              onClick={async () => {
                for (const pp of paragraphsNeedingReview) {
                  if (pp.user_choice) continue;
                  const c = paragraphChoices.get(pp.index);
                  if (c) await handleConfirmParagraph(pp.index, c);
                }
              }}
            >
              确认提交
            </Button>
          )}
          <Button
            icon={<RightOutlined />}
            disabled={wizardIndex >= paragraphsNeedingReview.length - 1}
            onClick={() =>
              setWizardIndex((i) => Math.min(paragraphsNeedingReview.length - 1, i + 1))
            }
          >
            下一段
          </Button>
        </div>
      </div>
    );
  };

  const renderResultStep = () => {
    const t = resultTask ?? task;
    if (!t) return null;

    const originalParagraphs = t.paragraphs;
    const rewrittenCount = originalParagraphs.filter((p) => p.user_choice && p.user_choice !== PARAGRAPH_CHOICE.ORIGINAL).length;

    return (
      <div>
        {/* 统计栏 */}
        <Card size="small" style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={6} style={{ textAlign: "center" }}>
              <Text type="secondary" style={{ fontSize: 12 }}>总段落数</Text>
              <div style={{ fontSize: 20, fontWeight: 600 }}>{t.paragraphs.length}</div>
            </Col>
            <Col span={6} style={{ textAlign: "center" }}>
              <Text type="secondary" style={{ fontSize: 12 }}>改写数</Text>
              <div style={{ fontSize: 20, fontWeight: 600, color: themeToken.colorPrimary }}>{rewrittenCount}</div>
            </Col>
            <Col span={6} style={{ textAlign: "center" }}>
              <Text type="secondary" style={{ fontSize: 12 }}>消耗积分</Text>
              <div style={{ fontSize: 20, fontWeight: 600, color: themeToken.colorWarning }}>
                {t.total_credits}
              </div>
            </Col>
            <Col span={6} style={{ textAlign: "center" }}>
              <Text type="secondary" style={{ fontSize: 12 }}>耗时</Text>
              <div style={{ fontSize: 14, fontWeight: 500 }}>
                {t.completed_at && t.created_at
                  ? (() => {
                      const ms = new Date(t.completed_at + "Z").getTime() - new Date(t.created_at + "Z").getTime();
                      const sec = Math.round(ms / 1000);
                      return sec > 60 ? `${Math.floor(sec / 60)}分${sec % 60}秒` : `${sec}秒`;
                    })()
                  : "--"}
              </div>
            </Col>
          </Row>
        </Card>

        {/* 左右对比 */}
        <Row gutter={16}>
          {/* 左侧原文 */}
          <Col span={12}>
            <Card
              title="原文"
              size="small"
              extra={
                <Button
                  size="small"
                  icon={<CopyOutlined />}
                  onClick={() => copyText(t.original_text, "原文")}
                >
                  复制全文
                </Button>
              }
            >
              <div style={{ maxHeight: 600, overflow: "auto", padding: "0 4px" }}>
                {originalParagraphs.map((p) => (
                  <div
                    key={p.index}
                    style={{
                      position: "relative",
                      paddingLeft: p.risk_level && p.risk_level !== RISK_LEVEL.LOW ? 12 : 0,
                      borderLeft:
                        p.risk_level && p.risk_level !== RISK_LEVEL.LOW
                          ? `3px solid ${riskColor(p.risk_level, themeToken)}`
                          : "none",
                      marginBottom: 12,
                    }}
                  >
                    {p.is_heading && (
                      <Text strong style={{ fontSize: 14 }}>
                        {p.original_text}
                      </Text>
                    )}
                    {!p.is_heading && (
                      <Text style={{ fontSize: 13, lineHeight: 1.8, whiteSpace: "pre-wrap" }}>
                        {p.original_text}
                      </Text>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          </Col>

          {/* 右侧改写后 */}
          <Col span={12}>
            <Card
              title="改写后"
              size="small"
              extra={
                <Button
                  size="small"
                  icon={<CopyOutlined />}
                  onClick={() => copyText(t.reduced_text ?? "", "改写结果")}
                >
                  复制全文
                </Button>
              }
            >
              <div style={{ maxHeight: 600, overflow: "auto", padding: "0 4px" }}>
                {originalParagraphs.map((p) => {
                  const displayText = p.final_text ?? p.original_text;
                  const wasRewritten = p.user_choice && p.user_choice !== PARAGRAPH_CHOICE.ORIGINAL;
                  return (
                    <div
                      key={p.index}
                      style={{
                        position: "relative",
                        paddingLeft: wasRewritten ? 12 : 0,
                        borderLeft: wasRewritten
                          ? `3px solid ${riskColor(p.risk_level ?? RISK_LEVEL.LOW, themeToken)}`
                          : "none",
                        marginBottom: 12,
                      }}
                    >
                      {p.is_heading ? (
                        <Text strong style={{ fontSize: 14 }}>{displayText}</Text>
                      ) : (
                        <Text style={{ fontSize: 13, lineHeight: 1.8, whiteSpace: "pre-wrap" }}>
                          {displayText}
                        </Text>
                      )}
                    </div>
                  );
                })}
              </div>
            </Card>
          </Col>
        </Row>

        {/* 底部操作 */}
        <Divider />
        <div style={{ textAlign: "center" }}>
          <Space>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={async () => {
                try {
                  const token = localStorage.getItem("access_token");
                  const resp = await fetch(getExportUrl(t.id, "docx"), {
                    headers: { Authorization: `Bearer ${token}` },
                  });
                  if (!resp.ok) {
                    const body = await resp.json().catch(() => ({}));
                    message.error(body.detail || "导出失败");
                    return;
                  }
                  const blob = await resp.blob();
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `${t.title.slice(0, 50) || "result"}.docx`;
                  a.click();
                  URL.revokeObjectURL(url);
                } catch { message.error("导出失败"); }
              }}
            >
              导出 Word
            </Button>
            <Button
              icon={<FileTextOutlined />}
              onClick={async () => {
                try {
                  const token = localStorage.getItem("access_token");
                  const resp = await fetch(getExportUrl(t.id, "markdown"), {
                    headers: { Authorization: `Bearer ${token}` },
                  });
                  if (!resp.ok) {
                    const body = await resp.json().catch(() => ({}));
                    message.error(body.detail || "导出失败");
                    return;
                  }
                  const blob = await resp.blob();
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `${t.title.slice(0, 50) || "result"}.md`;
                  a.click();
                  URL.revokeObjectURL(url);
                } catch { message.error("导出失败"); }
              }}
            >
              导出 Markdown
            </Button>
            <Button
              onClick={() => copyText(t.reduced_text ?? "", "改写结果")}
            >
              复制全文
            </Button>
            <Button onClick={() => navigate("/reduce/new")}>
              新建任务
            </Button>
          </Space>
        </div>
      </div>
    );
  };

  // ---- 主渲染 ----
  return (
    <div style={{ maxWidth: 1100, margin: "0 auto" }}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 16,
        }}
      >
        <Button
          type="text"
          icon={<LeftOutlined />}
          onClick={() => navigate(-1)}
        />
        <Title level={4} style={{ margin: 0, flex: 1 }}>
          {task.title || "任务工作区"}
        </Title>
        <Tag
          style={{ fontSize: 12 }}
          color={
            task.status === TASK_STATUS.COMPLETED
              ? "success"
              : [TASK_STATUS.DETECTING, TASK_STATUS.RECONSTRUCTING, TASK_STATUS.REWRITING, TASK_STATUS.FINALIZING].includes(task.status)
                ? "processing"
                : "default"
          }
        >
          {TASK_STATUS_LABELS[task.status] ?? task.status}
        </Tag>
      </div>

      <Steps current={currentStep} items={steps} size="small" style={{ marginBottom: 24, ...(isReadonly ? { display: "none" } : {}) }} />

      {isReadonly && task.status === TASK_STATUS.FAILED && (
        <Card style={{ marginBottom: 16, textAlign: "center" }}>
          <ExclamationCircleOutlined style={{ fontSize: 36, color: themeToken.colorError, marginBottom: 12 }} />
          <Title level={5} style={{ color: themeToken.colorError }}>任务失败</Title>
          <Text type="secondary">任务在执行过程中遇到错误，以下是已完成的检测结果。</Text>
          <div style={{ marginTop: 16 }}>
            <Button type="primary" onClick={() => navigate("/reduce/new")}>新建任务</Button>
            <Button style={{ marginLeft: 8 }} onClick={() => navigate(-1)}>返回</Button>
          </div>
        </Card>
      )}

      {currentStep === 0 && (
        <div style={{ textAlign: "center", padding: "80px 0" }}>
          <Spin size="large" tip="解析中..." />
        </div>
      )}
      {currentStep === 1 && renderDetectStep()}
      {currentStep === 2 && renderReconstructStep()}
      {currentStep === 3 && renderRewriteStep()}
      {currentStep === 4 && renderResultStep()}
    </div>
  );
}
