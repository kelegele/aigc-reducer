// web/frontend/src/constants/reduce.ts

/** 任务状态 */
export const TASK_STATUS = {
  PARSING: "parsing",
  DETECTING: "detecting",
  DETECTED: "detected",
  RECONSTRUCTING: "reconstructing",
  REWRITING: "rewriting",
  REWRITTEN: "rewritten",
  FINALIZING: "finalizing",
  COMPLETED: "completed",
  FAILED: "failed",
  CANCELLED: "cancelled",
} as const;

export type TaskStatus = (typeof TASK_STATUS)[keyof typeof TASK_STATUS];

export const TASK_STATUS_LABELS: Record<string, string> = {
  [TASK_STATUS.PARSING]: "解析中",
  [TASK_STATUS.DETECTING]: "检测中",
  [TASK_STATUS.DETECTED]: "检测完成",
  [TASK_STATUS.RECONSTRUCTING]: "重构中",
  [TASK_STATUS.REWRITING]: "改写中",
  [TASK_STATUS.REWRITTEN]: "改写完成",
  [TASK_STATUS.FINALIZING]: "生成中",
  [TASK_STATUS.COMPLETED]: "已完成",
  [TASK_STATUS.FAILED]: "失败",
  [TASK_STATUS.CANCELLED]: "已停止",
};

/** 风险等级 */
export const RISK_LEVEL = {
  LOW: "low",
  MEDIUM: "medium",
  MEDIUM_HIGH: "medium_high",
  HIGH: "high",
} as const;

export type RiskLevel = (typeof RISK_LEVEL)[keyof typeof RISK_LEVEL];

export const RISK_LEVEL_LABELS: Record<string, string> = {
  [RISK_LEVEL.LOW]: "低风险",
  [RISK_LEVEL.MEDIUM]: "中风险",
  [RISK_LEVEL.MEDIUM_HIGH]: "中高",
  [RISK_LEVEL.HIGH]: "高风险",
};

export const RISK_LEVEL_COLORS: Record<string, string> = {
  [RISK_LEVEL.LOW]: "success",
  [RISK_LEVEL.MEDIUM]: "processing",
  [RISK_LEVEL.MEDIUM_HIGH]: "warning",
  [RISK_LEVEL.HIGH]: "error",
};

/** 段落选择类型 */
export const PARAGRAPH_CHOICE = {
  AGGRESSIVE: "aggressive",
  CONSERVATIVE: "conservative",
  ORIGINAL: "original",
  MANUAL: "manual",
} as const;

export type ParagraphChoice = (typeof PARAGRAPH_CHOICE)[keyof typeof PARAGRAPH_CHOICE];

export const PARAGRAPH_CHOICE_LABELS: Record<string, string> = {
  [PARAGRAPH_CHOICE.AGGRESSIVE]: "方案 A（推荐）",
  [PARAGRAPH_CHOICE.CONSERVATIVE]: "方案 B（保守）",
  [PARAGRAPH_CHOICE.ORIGINAL]: "使用原文",
  [PARAGRAPH_CHOICE.MANUAL]: "手动输入",
};
