import { useEffect, useState } from "react";
import { Input, Select, Table, Tag, Typography, theme } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  listAdminTransactions,
  type AdminTransactionResponse,
} from "../../api/admin";

const { Title } = Typography;

export default function AdminTransactions() {
  const { token } = theme.useToken();
  const [data, setData] = useState<{
    items: AdminTransactionResponse[];
    total: number;
    page: number;
    size: number;
  } | null>(null);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined);

  const fetch = (page = 1) => {
    listAdminTransactions({
      search: search || undefined,
      type: typeFilter,
      page,
      size: 20,
    }).then(setData);
  };

  useEffect(() => {
    fetch();
  }, [search, typeFilter]);

  const columns: ColumnsType<AdminTransactionResponse> = [
    {
      title: "流水号",
      dataIndex: "trade_no",
      key: "trade_no",
      render: (v: string) => <Typography.Text copyable style={{ fontSize: 12 }}>{v}</Typography.Text>,
    },
    {
      title: "用户",
      key: "user",
      render: (_: unknown, r: AdminTransactionResponse) => `${r.user_nickname} (${r.user_phone})`,
    },
    {
      title: "类型",
      dataIndex: "type",
      key: "type",
      width: 80,
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
      width: 100,
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
      width: 80,
    },
    {
      title: "备注",
      dataIndex: "remark",
      key: "remark",
      ellipsis: true,
    },
    {
      title: "时间",
      dataIndex: "created_at",
      key: "created_at",
      width: 170,
      render: (v: string) => new Date(v + "Z").toLocaleString("zh-CN"),
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
        <Title level={4} style={{ margin: 0 }}>
          积分流水的管理
        </Title>
        <div style={{ display: "flex", gap: 8 }}>
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
          <Input.Search
            placeholder="搜索手机号"
            style={{ width: 200 }}
            onSearch={setSearch}
            allowClear
          />
        </div>
      </div>
      <Table
        columns={columns}
        dataSource={data?.items ?? []}
        rowKey="id"
        pagination={{
          current: data?.page ?? 1,
          total: data?.total ?? 0,
          pageSize: data?.size ?? 20,
          onChange: (page) => fetch(page),
        }}
      />
    </div>
  );
}
