// web/frontend/src/pages/Credits.tsx
import { useState } from "react";
import { Typography, Tabs } from "antd";
import Balance from "./credits/Balance";
import Packages from "./credits/Packages";
import History from "./credits/History";

const { Title } = Typography;

export default function Credits() {
  const [activeTab, setActiveTab] = useState("balance");

  return (
    <div>
      <Title level={4}>积分管理</Title>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: "balance",
            label: "余额概览",
            children: <Balance onGoPackages={() => setActiveTab("packages")} />,
          },
          {
            key: "packages",
            label: "充值套餐",
            children: <Packages />,
          },
          {
            key: "history",
            label: "积分流水",
            children: <History />,
          },
        ]}
      />
    </div>
  );
}
