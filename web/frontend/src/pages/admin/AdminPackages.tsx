import { useEffect, useState } from "react";
import { App as AntApp, Button, Form, Input, InputNumber, Modal, Switch, Table, Typography } from "antd";
import type { ColumnsType } from "antd/es/table";
import {
  listAllPackages,
  createPackage,
  updatePackage,
  deletePackage,
  type AdminPackageResponse,
} from "../../api/admin";

const { Title } = Typography;

export default function AdminPackages() {
  const { message, modal } = AntApp.useApp();
  const [packages, setPackages] = useState<AdminPackageResponse[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editPkg, setEditPkg] = useState<AdminPackageResponse | null>(null);
  const [form] = Form.useForm();

  const fetch = () => listAllPackages().then(setPackages);

  useEffect(() => { fetch(); }, []);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      values.price_cents = Math.round(values.price_cents * 100);
      if (editPkg) {
        await updatePackage(editPkg.id, values);
        message.success("修改成功");
      } else {
        await createPackage(values);
        message.success("创建成功");
      }
      setModalOpen(false);
      form.resetFields();
      setEditPkg(null);
      fetch();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      if (detail) message.error(detail);
    }
  };

  const handleDelete = async (id: number) => {
    modal.confirm({
      title: "确认删除？",
      onOk: async () => {
        try {
          await deletePackage(id);
          message.success("删除成功");
          fetch();
        } catch (err: unknown) {
          const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
          if (detail) message.error(detail);
        }
      },
    });
  };

  const openEdit = (pkg: AdminPackageResponse) => {
    setEditPkg(pkg);
    form.setFieldsValue({ ...pkg, price_cents: pkg.price_cents / 100 });
    setModalOpen(true);
  };

  const openCreate = () => {
    setEditPkg(null);
    form.resetFields();
    setModalOpen(true);
  };

  const columns: ColumnsType<AdminPackageResponse> = [
    { title: "ID", dataIndex: "id", key: "id", width: 60 },
    { title: "名称", dataIndex: "name", key: "name" },
    { title: "价格(元)", dataIndex: "price_cents", key: "price_cents", render: (v: number) => `¥${(v / 100).toFixed(2)}` },
    { title: "积分", dataIndex: "credits", key: "credits" },
    { title: "赠送", dataIndex: "bonus_credits", key: "bonus_credits" },
    { title: "排序", dataIndex: "sort_order", key: "sort_order", width: 80 },
    {
      title: "上架", dataIndex: "is_active", key: "is_active", width: 80,
      render: (v: boolean, record: AdminPackageResponse) => (
        <Switch checked={v} onChange={async (checked) => {
          await updatePackage(record.id, { is_active: checked });
          fetch();
        }} />
      ),
    },
    {
      title: "操作", key: "action", width: 140,
      render: (_: unknown, record: AdminPackageResponse) => (
        <>
          <Button type="link" size="small" onClick={() => openEdit(record)}>编辑</Button>
          <Button type="link" size="small" danger onClick={() => handleDelete(record.id)}>删除</Button>
        </>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>套餐管理</Title>
        <Button type="primary" onClick={openCreate}>新增套餐</Button>
      </div>
      <Table columns={columns} dataSource={packages} rowKey="id" />

      <Modal title={editPkg ? "编辑套餐" : "新增套餐"} open={modalOpen} onOk={handleSave} onCancel={() => { setModalOpen(false); setEditPkg(null); }}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="price_cents" label="价格(元)" rules={[{ required: true }]}>
            <InputNumber min={0.01} step={1} precision={2} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="credits" label="积分" rules={[{ required: true }]}>
            <InputNumber min={1} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="bonus_credits" label="赠送积分" initialValue={0}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="sort_order" label="排序" initialValue={0}>
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item name="is_active" label="上架" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
