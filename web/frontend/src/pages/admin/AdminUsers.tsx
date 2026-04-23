import { useEffect, useState } from "react";
import { App as AntApp, Button, Input, InputNumber, Modal, Table, Tag, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import { listUsers, adjustCredits, setUserStatus, type AdminUserResponse } from "../../api/admin";

const { Title } = Typography;

export default function AdminUsers() {
  const { message, modal } = AntApp.useApp();
  const [users, setUsers] = useState<{ items: AdminUserResponse[]; total: number; page: number; size: number } | null>(null);
  const [search, setSearch] = useState("");
  const [adjustModal, setAdjustModal] = useState<{ userId: number; visible: boolean }>({ userId: 0, visible: false });
  const [adjustAmount, setAdjustAmount] = useState(0);
  const [adjustRemark, setAdjustRemark] = useState("");

  const fetch = (page = 1) => {
    listUsers({ search: search || undefined, page, size: 20 }).then(setUsers);
  };

  useEffect(() => { fetch(); }, [search]);

  const handleAdjust = async () => {
    try {
      await adjustCredits(adjustModal.userId, adjustAmount, adjustRemark || "管理员调整");
      message.success("积分调整成功");
      setAdjustModal({ userId: 0, visible: false });
      setAdjustAmount(0);
      setAdjustRemark("");
      fetch();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      if (detail) message.error(detail);
    }
  };

  const handleToggleStatus = async (userId: number, isActive: boolean) => {
    modal.confirm({
      title: `确认${isActive ? "禁用" : "启用"}该用户？`,
      onOk: async () => {
        try {
          await setUserStatus(userId, !isActive);
          message.success("操作成功");
          fetch();
        } catch (err: unknown) {
          const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
          if (detail) message.error(detail);
        }
      },
    });
  };

  const columns: ColumnsType<AdminUserResponse> = [
    { title: "ID", dataIndex: "id", key: "id", width: 60 },
    { title: "手机号", dataIndex: "phone", key: "phone" },
    { title: "昵称", dataIndex: "nickname", key: "nickname" },
    { title: "积分余额", dataIndex: "credit_balance", key: "credit_balance" },
    { title: "累计充值", dataIndex: "total_recharged", key: "total_recharged" },
    { title: "累计消费", dataIndex: "total_consumed", key: "total_consumed" },
    {
      title: "状态", dataIndex: "is_active", key: "is_active", width: 80,
      render: (v: boolean) => <Tag color={v ? "green" : "red"}>{v ? "正常" : "禁用"}</Tag>,
    },
    {
      title: "操作", key: "action", width: 160,
      render: (_: unknown, record: AdminUserResponse) => (
        <>
          <Button type="link" size="small" onClick={() => setAdjustModal({ userId: record.id, visible: true })}>调积分</Button>
          <Button type="link" size="small" danger onClick={() => handleToggleStatus(record.id, record.is_active)}>
            {record.is_active ? "禁用" : "启用"}
          </Button>
        </>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>用户管理</Title>
        <Input.Search placeholder="搜索手机号/昵称" style={{ width: 250 }} onSearch={setSearch} allowClear />
      </div>
      <Table
        columns={columns}
        dataSource={users?.items ?? []}
        rowKey="id"
        pagination={{
          current: users?.page ?? 1,
          total: users?.total ?? 0,
          pageSize: users?.size ?? 20,
          onChange: (page) => fetch(page),
        }}
      />

      <Modal title="调整积分" open={adjustModal.visible} onOk={handleAdjust} onCancel={() => setAdjustModal({ userId: 0, visible: false })}>
        <div style={{ marginBottom: 12 }}>
          <span>金额（正数加，负数减）：</span>
          <InputNumber value={adjustAmount} onChange={(v) => setAdjustAmount(v ?? 0)} style={{ width: "100%", marginTop: 8 }} />
        </div>
        <div>
          <span>备注：</span>
          <Input value={adjustRemark} onChange={(e) => setAdjustRemark(e.target.value)} placeholder="管理员调整" style={{ marginTop: 8 }} />
        </div>
      </Modal>
    </div>
  );
}
