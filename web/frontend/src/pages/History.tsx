// web/frontend/src/pages/History.tsx
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  App as AntApp,
  Button,
  Card,
  Col,
  Empty,
  Input,
  List,
  Row,
  Select,
  Spin,
  Tag,
  Typography,
  theme,
} from "antd";
import {
  PlusCircleOutlined,
} from "@ant-design/icons";
import { getTasks, type TaskListItem } from "../api/reduce";
import {
  TASK_STATUS,
  TASK_STATUS_LABELS,
} from "../constants/reduce";

const { Title, Text } = Typography;

const STATUS_OPTIONS = [
  { value: "", label: "全部" },
  { value: "in_progress", label: "进行中" },
  { value: "completed", label: "已完成" },
  { value: "failed", label: "失败" },
];

function taskStatusColor(status: string): string {
  switch (status) {
    case TASK_STATUS.COMPLETED:
      return "success";
    case TASK_STATUS.FAILED:
      return "error";
    case TASK_STATUS.DETECTING:
    case TASK_STATUS.REWRITING:
    case TASK_STATUS.PARSING:
    case TASK_STATUS.RECONSTRUCTING:
    case TASK_STATUS.FINALIZING:
      return "processing";
    default:
      return "default";
  }
}

function formatDuration(created: string, completed: string | null): string {
  if (!completed) return "--";
  const ms = new Date(completed + "Z").getTime() - new Date(created + "Z").getTime();
  const sec = Math.round(ms / 1000);
  if (sec < 60) return `${sec}秒`;
  return `${Math.floor(sec / 60)}分${sec % 60}秒`;
}

export default function History() {
  const navigate = useNavigate();
  const { token: themeToken } = theme.useToken();
  const { message } = AntApp.useApp();

  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [keyword, setKeyword] = useState("");

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await getTasks({
        page,
        page_size: pageSize,
        ...(statusFilter ? { status: statusFilter } : {}),
        ...(keyword ? { keyword } : {}),
      });
      setTasks(resp.items);
      setTotal(resp.total);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || "加载任务列表失败");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, statusFilter, keyword, message]);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const handleSearch = (value: string) => {
    setKeyword(value);
    setPage(1);
  };

  const handleStatusChange = (value: string) => {
    setStatusFilter(value);
    setPage(1);
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0 }}>检测历史</Title>
        <Button
          type="primary"
          icon={<PlusCircleOutlined />}
          onClick={() => navigate("/reduce/new")}
        >
          新建任务
        </Button>
      </div>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={12} align="middle">
          <Col>
            <Select
              value={statusFilter}
              onChange={handleStatusChange}
              options={STATUS_OPTIONS}
              style={{ width: 120 }}
            />
          </Col>
          <Col flex="auto">
            <Input.Search
              placeholder="搜索标题或任务 ID"
              allowClear
              onSearch={handleSearch}
              style={{ maxWidth: 320 }}
            />
          </Col>
        </Row>
      </Card>

      <Spin spinning={loading}>
        {tasks.length === 0 && !loading ? (
          <Card>
            <Empty description="暂无任务" />
          </Card>
        ) : (
          <List
            dataSource={tasks}
            pagination={{
              current: page,
              pageSize,
              total,
              onChange: (p) => setPage(p),
              showTotal: (t) => `共 ${t} 条`,
              size: "small",
              style: { textAlign: "center", marginTop: 16 },
            }}
            renderItem={(item) => (
              <List.Item
                style={{
                  cursor: "pointer",
                  padding: "12px 16px",
                  borderRadius: 8,
                  marginBottom: 4,
                  transition: "background 0.2s",
                }}
                onClick={() => navigate(`/reduce/${item.id}`)}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLElement).style.background = themeToken.colorBgLayout;
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLElement).style.background = "transparent";
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 12, width: "100%" }}>
                  <Text
                    strong
                    ellipsis
                    style={{ flex: 1, fontSize: 14 }}
                  >
                    {item.title}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 11, fontFamily: "monospace", opacity: 0.5 }} copyable={{ text: item.id, tooltips: ["复制 ID", "已复制"] }}>
                    {item.id.slice(0, 8)}
                  </Text>
                  <Tag color={taskStatusColor(item.status)}>
                    {TASK_STATUS_LABELS[item.status] ?? item.status}
                  </Tag>
                  <Text type="secondary" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
                    {new Date(item.created_at + "Z").toLocaleString("zh-CN")}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
                    {formatDuration(item.created_at, item.completed_at)}
                  </Text>
                  <Text type="secondary" style={{ fontSize: 12, whiteSpace: "nowrap" }}>
                    {item.total_credits} 积分
                  </Text>
                </div>
              </List.Item>
            )}
          />
        )}
      </Spin>
    </div>
  );
}
