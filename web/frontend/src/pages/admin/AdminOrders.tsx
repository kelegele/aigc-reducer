// web/frontend/src/pages/admin/AdminOrders.tsx
import { useEffect, useState } from "react";
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
import { getAdminOrders } from "../../api/orders";
import type { AdminOrderDetail } from "../../api/orders";

const { Title } = Typography;
const { Search } = Input;

const statusMap: Record<string, { color: string; label: string }> = {
  pending: { color: "gold", label: "待支付" },
  paid: { color: "green", label: "已支付" },
  closed: { color: "default", label: "已关闭" },
};

export default function AdminOrders() {
  const { message } = AntApp.useApp();
  const [orders, setOrders] = useState<AdminOrderDetail[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState<string | undefined>();
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [loading, setLoading] = useState(false);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const resp = await getAdminOrders({
        search,
        status: statusFilter,
        page,
        size: 20,
      });
      setOrders(resp.items);
      setTotal(resp.total);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || "获取订单列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, [page, statusFilter]);

  const handleSearch = (value: string) => {
    setSearch(value || undefined);
    setPage(1);
    // 手动触发搜索
    fetchOrdersWithSearch(value || undefined);
  };

  const fetchOrdersWithSearch = async (s: string | undefined) => {
    setLoading(true);
    try {
      const resp = await getAdminOrders({
        search: s,
        status: statusFilter,
        page: 1,
        size: 20,
      });
      setOrders(resp.items);
      setTotal(resp.total);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || "获取订单列表失败");
    } finally {
      setLoading(false);
    }
  };

  const columns: ColumnsType<AdminOrderDetail> = [
    {
      title: "订单号",
      dataIndex: "out_trade_no",
      key: "out_trade_no",
    },
    {
      title: "用户手机号",
      dataIndex: "user_phone",
      key: "user_phone",
    },
    {
      title: "用户昵称",
      dataIndex: "user_nickname",
      key: "user_nickname",
    },
    {
      title: "金额",
      dataIndex: "amount_cents",
      key: "amount_cents",
      render: (v: number) => `¥${(v / 100).toFixed(2)}`,
    },
    {
      title: "积分",
      dataIndex: "credits_granted",
      key: "credits_granted",
    },
    {
      title: "套餐",
      dataIndex: "package_name",
      key: "package_name",
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (v: string) => {
        const s = statusMap[v] || { color: "default", label: v };
        return <Tag color={s.color}>{s.label}</Tag>;
      },
    },
    {
      title: "流水ID",
      dataIndex: "credit_transaction_id",
      key: "credit_transaction_id",
      render: (v: number | null) => (v != null ? v : "-"),
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (v: string) => new Date(v).toLocaleString("zh-CN"),
    },
  ];

  return (
    <div>
      <Title level={4}>订单管理</Title>
      <Space style={{ marginBottom: 16 }}>
        <Search
          placeholder="搜索订单号或手机号"
          allowClear
          onSearch={handleSearch}
          style={{ width: 250 }}
        />
        <Select
          allowClear
          placeholder="状态筛选"
          style={{ width: 120 }}
          value={statusFilter}
          onChange={(v) => {
            setStatusFilter(v);
            setPage(1);
          }}
          options={[
            { label: "待支付", value: "pending" },
            { label: "已支付", value: "paid" },
            { label: "已关闭", value: "closed" },
          ]}
        />
      </Space>
      <Table
        columns={columns}
        dataSource={orders}
        rowKey="id"
        loading={loading}
        pagination={{
          current: page,
          total,
          pageSize: 20,
          onChange: setPage,
          showTotal: (t) => `共 ${t} 条`,
        }}
      />
    </div>
  );
}
