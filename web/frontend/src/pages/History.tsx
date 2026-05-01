// web/frontend/src/pages/History.tsx
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  App as AntApp,
  Button,
  Card,
  Empty,
  Input,
  Select,
  Table,
  Tag,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  PlusCircleOutlined,
  StopOutlined,
} from "@ant-design/icons";
import { cancelTask, getTasks, type TaskListItem } from "../api/reduce";
import {
  TASK_STATUS,
  TASK_STATUS_LABELS,
} from "../constants/reduce";

const { Title, Text } = Typography;

const STATUS_OPTIONS = [
  { value: "in_progress", label: "进行中" },
  { value: "completed", label: "已完成" },
  { value: "failed", label: "失败" },
  { value: "cancelled", label: "已停止" },
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
  const { message, modal } = AntApp.useApp();

  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
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

  const columns: ColumnsType<TaskListItem> = [
    {
      title: "任务标题",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
    },
    {
      title: "任务 ID",
      dataIndex: "id",
      key: "id",
      width: 110,
      render: (v: string) => (
        <Text copyable={{ text: v, tooltips: ["复制 ID", "已复制"] }} style={{ fontSize: 12, fontFamily: "monospace" }}>
          {v.slice(0, 8)}
        </Text>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 90,
      render: (v: string) => (
        <Tag color={taskStatusColor(v)}>{TASK_STATUS_LABELS[v] ?? v}</Tag>
      ),
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 170,
      render: (v: string) => new Date(v + "Z").toLocaleString("zh-CN"),
    },
    {
      title: "耗时",
      key: "duration",
      width: 80,
      render: (_: unknown, r: TaskListItem) => formatDuration(r.created_at, r.completed_at),
    },
    {
      title: "消耗积分",
      dataIndex: "total_credits",
      key: "total_credits",
      width: 90,
      align: "center",
    },
    {
      title: "操作",
      key: "actions",
      width: 120,
      align: "center",
      render: (_: unknown, item: TaskListItem) => {
        const isInProgress = !["completed", "failed", "cancelled"].includes(item.status);
        if (!isInProgress) return null;
        return (
          <Button
            size="small"
            danger
            icon={<StopOutlined />}
            onClick={(e) => {
              e.stopPropagation();
              modal.confirm({
                title: "确认停止任务",
                content: "停止后任务将无法恢复，确认停止吗？",
                okText: "确认停止",
                okType: "danger",
                cancelText: "取消",
                onOk: async () => {
                  try {
                    await cancelTask(item.id);
                    message.success("任务已停止");
                    loadTasks();
                  } catch (err: unknown) {
                    const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
                    message.error(detail || "停止失败");
                  }
                },
              });
            }}
          >
            停止
          </Button>
        );
      },
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0 }}>检测记录</Title>
        <Button
          type="primary"
          icon={<PlusCircleOutlined />}
          onClick={() => navigate("/reduce/new")}
        >
          新建任务
        </Button>
      </div>

      <Card size="small" style={{ marginBottom: 16 }}>
        <div style={{ display: "flex", gap: 12 }}>
          <Select
            allowClear
            placeholder="状态筛选"
            value={statusFilter}
            onChange={(v) => {
              setStatusFilter(v);
              setPage(1);
            }}
            options={STATUS_OPTIONS}
            style={{ width: 130 }}
          />
          <Input.Search
            placeholder="搜索标题或任务 ID"
            allowClear
            onSearch={handleSearch}
            style={{ maxWidth: 320 }}
          />
        </div>
      </Card>

      <Table
        columns={columns}
        dataSource={tasks}
        rowKey="id"
        loading={loading}
        scroll={{ x: 800 }}
        locale={{ emptyText: <Empty description="暂无任务" /> }}
        onRow={(item) => ({
          onClick: () => navigate(`/reduce/${item.id}`),
          style: { cursor: "pointer" },
        })}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          pageSizeOptions: [10, 20, 50],
          locale: { items_per_page: "条/页" },
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => {
            setPage(p);
            setPageSize(ps);
          },
        }}
      />
    </div>
  );
}
