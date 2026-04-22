// web/frontend/src/pages/credits/Orders.tsx
import { useEffect, useState } from "react";
import { Table, Tag, Typography, Select, Space, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { getOrders, getOrderDetail } from "../../api/orders";
import type {
  OrderListItem,
  OrderDetail,
} from "../../api/orders";

const { Title, Text } = Typography;

const statusMap: Record<string, { color: string; label: string }> = {
  pending: { color: "gold", label: "待支付" },
  paid: { color: "green", label: "已支付" },
  closed: { color: "default", label: "已关闭" },
};

export default function Orders() {
  const [orders, setOrders] = useState<OrderListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [expandedRows, setExpandedRows] = useState<Record<number, OrderDetail>>({});
  const [loading, setLoading] = useState(false);

  const fetchOrders = async () => {
    setLoading(true);
    try {
      const resp = await getOrders({ status: statusFilter, page, size: 10 });
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

  const handleExpand = async (expanded: boolean, record: OrderListItem) => {
    if (expanded && !expandedRows[record.id]) {
      try {
        const detail = await getOrderDetail(record.id);
        setExpandedRows((prev) => ({ ...prev, [record.id]: detail }));
      } catch (err: unknown) {
        const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
        message.error(detail || "获取订单详情失败");
      }
    }
  };

  const columns: ColumnsType<OrderListItem> = [
    {
      title: "订单号",
      dataIndex: "out_trade_no",
      key: "out_trade_no",
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
      title: "状态",
      dataIndex: "status",
      key: "status",
      render: (v: string) => {
        const s = statusMap[v] || { color: "default", label: v };
        return <Tag color={s.color}>{s.label}</Tag>;
      },
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (v: string) => new Date(v).toLocaleString("zh-CN"),
    },
    {
      title: "支付时间",
      dataIndex: "paid_at",
      key: "paid_at",
      render: (v: string | null) =>
        v ? new Date(v).toLocaleString("zh-CN") : "-",
    },
  ];

  return (
    <div>
      <Title level={5}>我的订单</Title>
      <Space style={{ marginBottom: 16 }}>
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
          pageSize: 10,
          onChange: setPage,
          showTotal: (t) => `共 ${t} 条`,
        }}
        expandable={{
          onExpand: handleExpand,
          expandedRowRender: (record) => {
            const detail = expandedRows[record.id];
            if (!detail) return <Text type="secondary">加载中...</Text>;
            return (
              <Space direction="vertical" size={4}>
                <Text>
                  套餐名称：{detail.package_name}
                </Text>
                {detail.credit_transaction_id !== null && (
                  <Text>
                    积分流水 ID：
                    <Text code>{detail.credit_transaction_id}</Text>
                  </Text>
                )}
              </Space>
            );
          },
        }}
      />
    </div>
  );
}
