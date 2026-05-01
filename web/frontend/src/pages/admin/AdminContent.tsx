// web/frontend/src/pages/admin/AdminContent.tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  App as AntApp,
  Table,
  Tag,
  Input,
  Select,
  Space,
  Typography,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import { listAdminTasks } from "../../api/admin";
import type { AdminTaskResponse } from "../../api/admin";
import { TASK_STATUS_LABELS } from "../../constants/reduce";

const { Title, Text } = Typography;
const { Search } = Input;

const statusColorMap: Record<string, string> = {
  completed: "success",
  failed: "error",
  cancelled: "default",
  parsing: "processing",
  detecting: "processing",
  detected: "processing",
  rewriting: "processing",
  rewritten: "processing",
  finalizing: "processing",
};

const detectModeLabels: Record<string, string> = {
  rules: "规则引擎",
  llm: "LLM 反查",
};

export default function AdminContent() {
  const navigate = useNavigate();
  const { message } = AntApp.useApp();
  const [tasks, setTasks] = useState<AdminTaskResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);

  const fetchTasks = async (s?: string) => {
    setLoading(true);
    try {
      const resp = await listAdminTasks({
        search: s ?? search,
        status: statusFilter,
        page: s !== undefined ? 1 : page,
        size: 20,
      });
      setTasks(resp.items);
      setTotal(resp.total);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || "获取检测记录失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTasks();
  }, [page, statusFilter]);

  const handleSearch = (value: string) => {
    setSearch(value || undefined);
    setPage(1);
    fetchTasks(value || undefined);
  };

  const columns: ColumnsType<AdminTaskResponse> = [
    {
      title: "任务 ID",
      dataIndex: "id",
      key: "id",
      width: 100,
      render: (v: string) => (
        <Text
          copyable={{ text: v }}
          style={{ fontFamily: "monospace", fontSize: 12, cursor: "pointer", color: "inherit" }}
          onClick={() => navigate(`/admin/content/${v}`)}
        >
          {v.slice(0, 8)}
        </Text>
      ),
    },
    {
      title: "用户 ID",
      dataIndex: "user_id",
      key: "user_id",
      width: 80,
    },
    {
      title: "用户",
      dataIndex: "user_phone",
      key: "user_phone",
      render: (_: string, record: AdminTaskResponse) =>
        `${record.user_nickname || "-"} (${record.user_phone || "-"})`,
    },
    {
      title: "标题",
      dataIndex: "title",
      key: "title",
      ellipsis: true,
      render: (v: string, record: AdminTaskResponse) => (
        <a onClick={() => navigate(`/admin/content/${record.id}`)} style={{ cursor: "pointer" }}>
          {v}
        </a>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 100,
      render: (v: string) => (
        <Tag color={statusColorMap[v] || "default"}>
          {TASK_STATUS_LABELS[v] ?? v}
        </Tag>
      ),
    },
    {
      title: "检测模式",
      dataIndex: "detect_mode",
      key: "detect_mode",
      width: 90,
      render: (v: string) => detectModeLabels[v] ?? v,
    },
    {
      title: "改写风格",
      dataIndex: "style",
      key: "style",
      width: 100,
    },
    {
      title: "段落数",
      dataIndex: "paragraph_count",
      key: "paragraph_count",
      width: 70,
    },
    {
      title: "花费积分",
      dataIndex: "total_credits",
      key: "total_credits",
      width: 80,
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 160,
      render: (v: string) => new Date(v + "Z").toLocaleString("zh-CN"),
    },
  ];

  return (
    <div>
      <Title level={4}>内容管理</Title>
      <Space style={{ marginBottom: 16 }}>
        <Search
          placeholder="搜索标题、手机号或任务 ID"
          allowClear
          onSearch={handleSearch}
          style={{ width: 280 }}
        />
        <Select
          allowClear
          placeholder="状态筛选"
          style={{ width: 130 }}
          value={statusFilter}
          onChange={(v) => {
            setStatusFilter(v);
            setPage(1);
          }}
          options={[
            { label: "进行中", value: "in_progress" },
            { label: "已完成", value: "completed" },
            { label: "失败", value: "failed" },
            { label: "已停止", value: "cancelled" },
          ]}
        />
      </Space>
      <Table
        columns={columns}
        dataSource={tasks}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 20,
          onChange: (p) => setPage(p),
          showTotal: (t) => `共 ${t} 条`,
        }}
        scroll={{ x: 1100 }}
        onRow={(record) => ({
          onClick: () => navigate(`/admin/content/${record.id}`),
          style: { cursor: "pointer" },
        })}
      />
    </div>
  );
}
