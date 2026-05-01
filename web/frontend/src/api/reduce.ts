// web/frontend/src/api/reduce.ts
import client from "./client";

// --- Types ---

export interface ParagraphResponse {
  index: number;
  original_text: string;
  is_heading: boolean;
  has_formula: boolean;
  has_code: boolean;
  risk_level: string | null;
  composite_score: number | null;
  detection_detail: Record<string, unknown> | null;
  rewrite_aggressive: string | null;
  rewrite_conservative: string | null;
  user_choice: string | null;
  final_text: string | null;
  status: string;
}

export interface TaskResponse {
  id: string;
  title: string;
  status: string;
  detect_mode: string;
  style: string;
  full_reconstruct: boolean;
  total_credits: number;
  original_text: string;
  reduced_text: string | null;
  created_at: string;
  completed_at: string | null;
  paragraphs: ParagraphResponse[];
}

export interface TaskListItem {
  id: string;
  title: string;
  status: string;
  style: string;
  total_credits: number;
  paragraph_count: number;
  created_at: string;
  completed_at: string | null;
}

export interface TaskListResponse {
  items: TaskListItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface CreditsEstimateResponse {
  estimated_credits: number;
  current_balance: number;
  sufficient: boolean;
}

export interface ConfirmParagraphResponse {
  index: number;
  user_choice: string;
  final_text: string | null;
  status: string;
}

export interface UserStatsResponse {
  detection_count: number;
  rewritten_paragraphs: number;
  pass_rate: number;
}

// --- API Functions ---

/** 创建任务（multipart form） */
export async function createTask(data: {
  source_type: "file" | "text";
  detect_mode: "rules" | "llm";
  style: string;
  text?: string;
  file?: File;
}): Promise<TaskResponse> {
  const form = new FormData();
  form.append("source_type", data.source_type);
  form.append("detect_mode", data.detect_mode);
  form.append("style", data.style);
  if (data.source_type === "text" && data.text !== undefined) {
    form.append("text", data.text);
  }
  if (data.source_type === "file" && data.file !== undefined) {
    form.append("file", data.file);
  }
  const resp = await client.post<TaskResponse>("/reduce/tasks", form, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 30000,
  });
  return resp.data;
}

/** 任务列表 */
export async function getTasks(params: {
  page?: number;
  page_size?: number;
  status?: string;
  keyword?: string;
}): Promise<TaskListResponse> {
  const resp = await client.get<TaskListResponse>("/reduce/tasks", {
    params: {
      page: params.page ?? 1,
      page_size: params.page_size ?? 10,
      ...(params.status ? { status: params.status } : {}),
      ...(params.keyword ? { keyword: params.keyword } : {}),
    },
  });
  return resp.data;
}

/** 任务详情 */
export async function getTask(taskId: string): Promise<TaskResponse> {
  const resp = await client.get<TaskResponse>(`/reduce/tasks/${taskId}`);
  return resp.data;
}

/** 预估积分 */
export async function estimateCredits(
  taskId: string,
  operation: string,
): Promise<CreditsEstimateResponse> {
  const resp = await client.post<CreditsEstimateResponse>(
    `/reduce/tasks/${taskId}/estimate`,
    null,
    { params: { operation } },
  );
  return resp.data;
}

/** 确认段落 */
export async function confirmParagraph(
  taskId: string,
  index: number,
  choice: string,
  manualText?: string,
): Promise<ConfirmParagraphResponse> {
  const body: Record<string, string> = { choice };
  if (manualText !== undefined) {
    body.manual_text = manualText;
  }
  const resp = await client.put<ConfirmParagraphResponse>(
    `/reduce/tasks/${taskId}/paragraphs/${index}`,
    body,
  );
  return resp.data;
}

/** 完成任务 */
export async function finalizeTask(taskId: number): Promise<TaskResponse> {
  const resp = await client.post<TaskResponse>(`/reduce/tasks/${taskId}/finalize`);
  return resp.data;
}

/** 取消任务 */
export async function cancelTask(taskId: string): Promise<TaskResponse> {
  const resp = await client.post<TaskResponse>(`/reduce/tasks/${taskId}/cancel`);
  return resp.data;
}

/** 导出任务结果 */
export function getExportUrl(taskId: string, format: "markdown" | "docx" = "markdown"): string {
  return `/api/reduce/tasks/${taskId}/export?format=${format}`;
}

/** 用户统计数据 */
export async function getUserStats(): Promise<UserStatsResponse> {
  const resp = await client.get<UserStatsResponse>("/reduce/stats");
  return resp.data;
}

// --- SSE Helper ---

/**
 * 连接 SSE 端点并逐行解析 data 事件。
 * 返回 AbortController，调用方 controller.abort() 可取消连接。
 *
 * 后端格式：每行 `data: {...}\n\n`，无 `event:` 行。
 */
export function connectSSE(
  url: string,
  onEvent: (data: Record<string, unknown>) => void,
  onError: (error: string) => void,
): AbortController {
  const controller = new AbortController();
  const token = localStorage.getItem("access_token");

  // 构建完整 URL（client.ts 的 baseURL 是 /api，fetch 需要全路径）
  const fullUrl = url.startsWith("/") ? url : `/api${url}`;

  fetch(fullUrl, {
    method: "POST",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      Accept: "text/event-stream",
    },
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const body = await response.text();
        let detail = `HTTP ${response.status}`;
        try {
          const parsed = JSON.parse(body) as { detail?: string };
          if (parsed.detail) detail = parsed.detail;
        } catch {
          /* ignore parse error */
        }
        onError(detail);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        onError("No response body");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // 解析 SSE：按双换行分割事件块
        const parts = buffer.split("\n\n");
        // 最后一段可能不完整，留在 buffer 中
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          for (const line of part.split("\n")) {
            if (line.startsWith("data: ")) {
              const jsonStr = line.slice(6).trim();
              if (!jsonStr) continue;
              try {
                const data = JSON.parse(jsonStr) as Record<string, unknown>;
                onEvent(data);
              } catch {
                /* ignore malformed JSON */
              }
            }
          }
        }
      }

      // 处理 buffer 中剩余数据
      if (buffer.trim()) {
        for (const line of buffer.split("\n")) {
          if (line.startsWith("data: ")) {
            const jsonStr = line.slice(6).trim();
            if (!jsonStr) continue;
            try {
              const data = JSON.parse(jsonStr) as Record<string, unknown>;
              onEvent(data);
            } catch {
              /* ignore malformed JSON */
            }
          }
        }
      }
    })
    .catch((err: unknown) => {
      if (controller.signal.aborted) return;
      const message =
        err instanceof Error ? err.message : "SSE connection failed";
      onError(message);
    });

  return controller;
}
