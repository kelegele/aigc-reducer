// web/frontend/src/pages/credits/History.tsx
import { useEffect, useState } from "react";
import { Table, Tag, Select, Typography, theme } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCreditsStore } from "../../stores/credits";
import type { TransactionResponse } from "../../api/credits";

const { Title } = Typography;

export default function History() {
  const { transactions, fetchTransactions, loading } = useCreditsStore();
  const { token } = theme.useToken();
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined);

  useEffect(() => {
    fetchTransactions({ type: typeFilter, page: 1, size: 10 });
  }, [typeFilter, fetchTransactions]);

  const columns: ColumnsType<TransactionResponse> = [
    {
      title: "流水号",
      dataIndex: "trade_no",
      key: "trade_no",
      render: (v: string) => <Typography.Text copyable style={{ fontSize: 12 }}>{v}</Typography.Text>,
    },
    {
      title: "时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (v: string) => new Date(v + "Z").toLocaleString("zh-CN"),
    },
    {
      title: "类型",
      dataIndex: "type",
      key: "type",
      render: (v: string) => (
        <Tag color={v === "recharge" ? "green" : "red"}>
          {v === "recharge" ? "充值" : "消费"}
        </Tag>
      ),
    },
    {
      title: "积分变动",
      dataIndex: "amount",
      key: "amount",
      render: (v: number) => (
        <span style={{ color: v > 0 ? token.colorSuccess : token.colorError }}>
          {v > 0 ? "+" : ""}
          {v}
        </span>
      ),
    },
    {
      title: "余额",
      dataIndex: "balance_after",
      key: "balance_after",
    },
    {
      title: "备注",
      dataIndex: "remark",
      key: "remark",
    },
  ];

  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <Title level={5} style={{ margin: 0 }}>
          积分流水
        </Title>
        <Select
          style={{ width: 120 }}
          placeholder="全部类型"
          allowClear
          onChange={(v) => setTypeFilter(v)}
          options={[
            { label: "充值", value: "recharge" },
            { label: "消费", value: "consume" },
          ]}
        />
      </div>
      <Table
        columns={columns}
        dataSource={transactions?.items ?? []}
        rowKey="id"
        loading={loading}
        pagination={{
          current: transactions?.page ?? 1,
          total: transactions?.total ?? 0,
          pageSize: transactions?.size ?? 10,
          onChange: (page) =>
            fetchTransactions({ type: typeFilter, page, size: 10 }),
        }}
      />
    </div>
  );
}
