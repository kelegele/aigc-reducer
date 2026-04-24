// web/frontend/src/pages/Landing.tsx
import { useNavigate } from "react-router-dom";
import { Button, Typography } from "antd";
import {
  SafetyCertificateOutlined,
  EditOutlined,
  FileProtectOutlined,
  FileTextOutlined,
  SearchOutlined,
  ThunderboltOutlined,
  DownloadOutlined,
  CheckCircleOutlined,
  CreditCardOutlined,
  LoginOutlined,
  RightOutlined,
  BulbOutlined,
  ArrowRightOutlined,
} from "@ant-design/icons";
import { useThemeStore } from "../stores/theme";
import { useAuthStore } from "../stores/auth";

const { Title, Text, Paragraph } = Typography;

const darkColors = {
  bg: "#050507",
  surface: "#101010",
  border: "#3d3a39",
  accent: "#00d992",
  accentMint: "#2fd6a1",
  textPrimary: "#f2f2f2",
  textSecondary: "#b8b3b0",
  textTertiary: "#8b949e",
  btnBg: "#00d992",
  btnColor: "#050507",
  btnGhostBg: "transparent",
  btnGhostBorder: "#3d3a39",
  btnGhostColor: "#f2f2f2",
};

const lightColors = {
  bg: "#ffffff",
  surface: "#f7f8fa",
  border: "#e0e0e0",
  accent: "#00b377",
  accentMint: "#00b377",
  textPrimary: "#1a1a1a",
  textSecondary: "#555555",
  textTertiary: "#888888",
  btnBg: "#00b377",
  btnColor: "#ffffff",
  btnGhostBg: "transparent",
  btnGhostBorder: "#d0d0d0",
  btnGhostColor: "#1a1a1a",
};

const steps = [
  { icon: <CreditCardOutlined />, title: "充值积分", desc: "支付宝安全支付" },
  { icon: <FileTextOutlined />, title: "上传文档", desc: "Word / PDF / MD" },
  { icon: <SearchOutlined />, title: "扫描风险", desc: "双引擎 AI 检测" },
  { icon: <ThunderboltOutlined />, title: "选择风格", desc: "5 种改写风格" },
  { icon: <EditOutlined />, title: "AI 改写", desc: "逐段 A/B 确认" },
  { icon: <DownloadOutlined />, title: "下载结果", desc: "全文 + 差异 + 报告" },
];

const platforms = ["知网 AIGC 检测", "格子达", "维普", "万方", "PaperPass"];

const features = [
  {
    icon: <SafetyCertificateOutlined />,
    color: "#00d992",
    title: "AI 检测",
    desc: "规则引擎（5 维特征分析）+ LLM 反查模拟，精准识别 AI 写作痕迹",
    points: ["困惑度 / 突发性 / 连接词频率", "认知特征 / 语义指纹", "综合评分 0-100"],
  },
  {
    icon: <EditOutlined />,
    color: "#2fd6a1",
    title: "智能改写",
    desc: "5 种改写风格，aggressive / conservative 两档，逐段 A/B 对比确认",
    points: ["学术人文化（推荐）", "口语化 / 文言文化", "中英混杂 / 粗犷草稿风"],
  },
  {
    icon: <FileProtectOutlined />,
    color: "#818cf8",
    title: "完整输出",
    desc: "一键生成三份文件，全面掌握改写效果和论文状态",
    points: ["改写后全文（Markdown）", "前后差异对比", "整改建议报告"],
  },
];

export default function Landing() {
  const navigate = useNavigate();
  const { isDark, toggle } = useThemeStore();
  const { user } = useAuthStore();
  const C = isDark ? darkColors : lightColors;

  return (
    <div style={{ background: C.bg, minHeight: "100vh", color: C.textPrimary }}>
      {/* 导航栏 */}
      <nav
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 48px",
          borderBottom: `1px solid ${C.border}`,
          maxWidth: 1200,
          margin: "0 auto",
        }}
      >
        <Text
          strong
          style={{
            fontSize: 20,
            color: C.textPrimary,
            fontFamily: "system-ui, -apple-system, sans-serif",
            letterSpacing: "-0.5px",
            cursor: "pointer",
          }}
          onClick={() => navigate("/")}
        >
          AIGC<span style={{ color: C.accent }}>Reducer</span>
        </Text>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Button
            type="text"
            icon={<BulbOutlined />}
            onClick={toggle}
            style={{ color: C.textSecondary }}
          />
          <Button
            type="primary"
            icon={user ? <ArrowRightOutlined /> : <LoginOutlined />}
            onClick={() => navigate(user ? "/dashboard" : "/login")}
            style={{
              background: C.btnBg,
              borderColor: C.btnBg,
              color: C.btnColor,
              height: 40,
              paddingInline: 24,
              borderRadius: 6,
            }}
          >
            {user ? "进入系统" : "登录 / 注册"}
          </Button>
        </div>
      </nav>

      <div style={{ maxWidth: 1000, margin: "0 auto", padding: "0 24px" }}>
        {/* Hero */}
        <div style={{ textAlign: "center", padding: "80px 0 48px" }}>
          <Text
            style={{
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: "2.5px",
              textTransform: "uppercase",
              color: C.accent,
              display: "block",
              marginBottom: 20,
            }}
          >
            学术论文 AIGC 降重工具
          </Text>
          <Title
            level={1}
            style={{
              color: C.textPrimary,
              fontSize: 48,
              lineHeight: 1.05,
              letterSpacing: "-0.65px",
              fontFamily: "system-ui, -apple-system, sans-serif",
              fontWeight: 400,
              marginBottom: 20,
            }}
          >
            精准检测，智能改写
            <br />
            <span style={{ color: C.accent }}>降低 AIGC 查重率</span>
          </Title>
          <Paragraph
            style={{
              fontSize: 18,
              color: C.textSecondary,
              maxWidth: 560,
              margin: "0 auto 36px",
              lineHeight: 1.65,
            }}
          >
            双引擎检测 AI 写作痕迹，5 种风格智能改写，助力论文通过知网、格子达等平台审核
          </Paragraph>
          <div style={{ display: "flex", gap: 12, justifyContent: "center" }}>
            <Button
              type="primary"
              size="large"
              icon={user ? <ArrowRightOutlined /> : <LoginOutlined />}
              onClick={() => navigate(user ? "/dashboard" : "/login")}
              style={{
                height: 50,
                paddingInline: 40,
                fontSize: 16,
                background: C.accent,
                borderColor: C.accent,
                color: C.bg,
                fontWeight: 600,
                borderRadius: 6,
              }}
            >
              {user ? "进入系统" : "立即使用"}
            </Button>
            <Button
              size="large"
              onClick={() =>
                document.getElementById("features")?.scrollIntoView({ behavior: "smooth" })
              }
              style={{
                height: 50,
                paddingInline: 32,
                fontSize: 16,
                background: "transparent",
                borderColor: C.border,
                color: C.textPrimary,
                borderRadius: 6,
              }}
            >
              了解更多
            </Button>
          </div>
        </div>

        {/* 信任指标 */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 16,
            marginBottom: 64,
          }}
        >
          {[
            { value: "双引擎", label: "检测引擎" },
            { value: "5 种", label: "改写风格" },
            { value: "100%", label: "格式支持" },
          ].map((item) => (
            <div
              key={item.label}
              style={{
                textAlign: "center",
                padding: "20px 0",
                background: C.surface,
                border: `1px solid ${C.border}`,
                borderRadius: 8,
              }}
            >
              <div style={{ fontSize: 28, fontWeight: 600, color: C.accent, marginBottom: 4, fontFamily: "system-ui" }}>
                {item.value}
              </div>
              <Text style={{ color: C.textTertiary, fontSize: 14 }}>{item.label}</Text>
            </div>
          ))}
        </div>

        {/* 核心功能 */}
        <div id="features" style={{ marginBottom: 64 }}>
          <Text
            style={{
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: "2.5px",
              textTransform: "uppercase",
              color: C.accent,
              display: "block",
              marginBottom: 8,
            }}
          >
            Core Features
          </Text>
          <Title
            level={2}
            style={{
              color: C.textPrimary,
              fontSize: 36,
              lineHeight: 1.11,
              letterSpacing: "-0.9px",
              fontFamily: "system-ui",
              fontWeight: 400,
              marginBottom: 32,
            }}
          >
            核心功能
          </Title>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
            {features.map((f) => (
              <div
                key={f.title}
                style={{
                  background: C.surface,
                  border: `1px solid ${C.border}`,
                  borderRadius: 8,
                  padding: 28,
                  borderTop: `2px solid ${f.color}`,
                }}
              >
                <div style={{ fontSize: 32, color: f.color, marginBottom: 16 }}>{f.icon}</div>
                <Title
                  level={4}
                  style={{
                    color: C.textPrimary,
                    fontFamily: "system-ui",
                    fontWeight: 700,
                    fontSize: 20,
                    marginBottom: 8,
                  }}
                >
                  {f.title}
                </Title>
                <Paragraph style={{ color: C.textSecondary, marginBottom: 16, lineHeight: 1.65 }}>
                  {f.desc}
                </Paragraph>
                <ul style={{ paddingLeft: 16, margin: 0, listStyle: "disc" }}>
                  {f.points.map((p) => (
                    <li key={p} style={{ color: C.textTertiary, fontSize: 14, marginBottom: 4 }}>
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        {/* 使用流程 */}
        <div style={{ marginBottom: 64 }}>
          <Text
            style={{
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: "2.5px",
              textTransform: "uppercase",
              color: C.accent,
              display: "block",
              marginBottom: 8,
            }}
          >
            How It Works
          </Text>
          <Title
            level={2}
            style={{
              color: C.textPrimary,
              fontSize: 36,
              lineHeight: 1.11,
              letterSpacing: "-0.9px",
              fontFamily: "system-ui",
              fontWeight: 400,
              marginBottom: 32,
            }}
          >
            使用流程
          </Title>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 16 }}>
            {steps.map((s, i) => (
              <div key={i} style={{ textAlign: "center" }}>
                <div
                  style={{
                    width: 52,
                    height: 52,
                    borderRadius: "50%",
                    border: `1px solid ${C.border}`,
                    background: C.surface,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    margin: "0 auto 10px",
                    fontSize: 22,
                    color: C.accent,
                  }}
                >
                  {s.icon}
                </div>
                <Text
                  strong
                  style={{ display: "block", color: C.textPrimary, fontSize: 14, marginBottom: 4 }}
                >
                  {s.title}
                </Text>
                <Text style={{ color: C.textTertiary, fontSize: 12 }}>{s.desc}</Text>
              </div>
            ))}
          </div>
        </div>

        {/* 定价引导 */}
        <div
          style={{
            marginBottom: 64,
            background: C.surface,
            border: `2px solid ${C.accent}`,
            borderRadius: 8,
            padding: "32px 40px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <Title
              level={4}
              style={{
                color: C.textPrimary,
                fontFamily: "system-ui",
                fontWeight: 700,
                fontSize: 24,
                marginBottom: 8,
              }}
            >
              按需付费，用多少扣多少
            </Title>
            <Paragraph style={{ color: C.textSecondary, marginBottom: 0, lineHeight: 1.65 }}>
              积分按 Token 消耗，支持支付宝在线支付。从体验包到专业包，满足不同论文需求。
            </Paragraph>
          </div>
          <Button
            type="primary"
            size="large"
            icon={<RightOutlined />}
            onClick={() => navigate(user ? "/credits" : "/login")}
            style={{
              background: C.accent,
              borderColor: C.accent,
              color: C.bg,
              fontWeight: 600,
              height: 48,
              paddingInline: 28,
              borderRadius: 6,
            }}
          >
            查看套餐
          </Button>
        </div>

        {/* 适配平台 */}
        <div style={{ marginBottom: 64 }}>
          <Text
            style={{
              fontSize: 12,
              fontWeight: 600,
              letterSpacing: "2.5px",
              textTransform: "uppercase",
              color: C.accent,
              display: "block",
              marginBottom: 8,
            }}
          >
            Compatible Platforms
          </Text>
          <Title
            level={2}
            style={{
              color: C.textPrimary,
              fontSize: 36,
              lineHeight: 1.11,
              letterSpacing: "-0.9px",
              fontFamily: "system-ui",
              fontWeight: 400,
              marginBottom: 24,
            }}
          >
            适配检测平台
          </Title>
          <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
            {platforms.map((name) => (
              <div
                key={name}
                style={{
                  padding: "10px 20px",
                  background: C.surface,
                  border: `1px solid ${C.border}`,
                  borderRadius: 6,
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                }}
              >
                <CheckCircleOutlined style={{ color: C.accent }} />
                <Text style={{ color: C.textPrimary }}>{name}</Text>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 页脚 */}
      <footer
        style={{
          borderTop: `1px solid ${C.border}`,
          background: C.surface,
          padding: "40px 48px 24px",
        }}
      >
        <div style={{ maxWidth: 1000, margin: "0 auto", display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 32 }}>
          <div>
            <Text strong style={{ color: C.textPrimary, fontSize: 16, display: "block", marginBottom: 12 }}>
              AIGC<span style={{ color: C.accent }}>Reducer</span>
            </Text>
            <Text style={{ color: C.textTertiary, fontSize: 13, lineHeight: 1.8, display: "block" }}>
              专业的学术论文 AIGC 查重率降低工具
            </Text>
            <Text style={{ color: C.textTertiary, fontSize: 13, lineHeight: 1.8, display: "block" }}>
              双引擎检测 + 智能改写
            </Text>
          </div>
          <div>
            <Text strong style={{ color: C.textPrimary, fontSize: 14, display: "block", marginBottom: 12 }}>
              产品服务
            </Text>
            <Text style={{ color: C.textTertiary, fontSize: 13, display: "block", lineHeight: 2 }}>
              AIGC 降重
            </Text>
          </div>
          <div>
            <Text strong style={{ color: C.textPrimary, fontSize: 14, display: "block", marginBottom: 12 }}>
              联系我们
            </Text>
            <Text style={{ color: C.textTertiary, fontSize: 13, display: "block", lineHeight: 2 }}>
              客服邮箱：support@aigc-reducer.com
            </Text>
            <Text style={{ color: C.textTertiary, fontSize: 13, display: "block", lineHeight: 2 }}>
              工作时间：周一至周五 9:00-18:00
            </Text>
          </div>
        </div>
        <div style={{ maxWidth: 1000, margin: "24px auto 0", paddingTop: 16, borderTop: `1px solid ${C.border}`, textAlign: "center" }}>
          <Text style={{ color: C.textTertiary, fontSize: 12 }}>
            © 2026 AIGC Reducer. All rights reserved. | 本产品仅供学术研究使用
          </Text>
        </div>
      </footer>
    </div>
  );
}
