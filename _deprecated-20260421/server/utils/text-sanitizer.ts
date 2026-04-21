/**
 * 飞书卡片文本消毒器（V9.1 · 乱码规避）
 *
 * 根因对应：
 * 1. BOM `\uFEFF`、零宽字符 `\u200B-\u200D\u2060` 会被飞书渲染成方块
 * 2. 控制字符 `\u0000-\u001F`（除了 \n\t）会让 JSON.parse 抛错
 * 3. CRLF `\r\n` 在飞书卡片 text 里渲染成字面量 \r
 * 4. 超长 text 被按字节截断会切坏多字节 UTF-8
 * 5. option.value 里的特殊字符（引号/反斜杠/冒号）会破坏 form schema
 *
 * 用法：所有进入飞书卡片 payload 的 string 字段必须先过 sanitizeForFeishu
 */

/** 去 BOM / 零宽 / 控制字符 / CRLF，裁剪到字节安全长度 */
export function sanitizeForFeishu(input: unknown, maxBytes = 500): string {
  if (input === null || input === undefined) return "";
  let s = String(input);

  // 1. 去 BOM
  s = s.replace(/^\uFEFF/, "");

  // 2. 去零宽字符 + 方向控制符
  s = s.replace(/[\u200B-\u200F\u202A-\u202E\u2060-\u206F]/g, "");

  // 3. 去控制字符（保留 \n \t），把 \r\n / \r 统一成 \n
  s = s.replace(/\r\n?/g, "\n");
  s = s.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "");

  // 4. 飞书 Markdown 敏感字符最小转义：反引号不处理（允许 code 块），但独立
  //    的 < > 要转义防止被当成 html 吞
  s = s.replace(/</g, "&lt;").replace(/>/g, "&gt;");

  // 5. 按字节裁剪，不切坏多字节
  s = truncateByBytes(s, maxBytes);

  return s;
}

/** 以 UTF-8 字节为单位裁剪，保证不切坏多字节字符 */
export function truncateByBytes(s: string, maxBytes: number): string {
  if (!s) return "";
  const enc = new TextEncoder();
  const bytes = enc.encode(s);
  if (bytes.length <= maxBytes) return s;
  // 从目标字节位置向前回退，直到落在 UTF-8 起始字节（0xxxxxxx 或 11xxxxxx）
  let end = maxBytes;
  while (end > 0 && (bytes[end] & 0xc0) === 0x80) end--;
  return new TextDecoder("utf-8").decode(bytes.subarray(0, end));
}

/** JSON.stringify + 过滤 payload 深层的控制字符，避免飞书 API 400 */
export function safeStringify(obj: unknown): string {
  const clean = deepClean(obj);
  return JSON.stringify(clean);
}

function deepClean(v: unknown): unknown {
  if (v === null || v === undefined) return v;
  if (typeof v === "string") {
    // 只去 BOM / 零宽 / 控制字符，不限长（限长交给 sanitizeForFeishu）
    return v
      .replace(/^\uFEFF/, "")
      .replace(/[\u200B-\u200F\u202A-\u202E\u2060-\u206F]/g, "")
      .replace(/\r\n?/g, "\n")
      .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "");
  }
  if (Array.isArray(v)) return v.map(deepClean);
  if (typeof v === "object") {
    const out: Record<string, unknown> = {};
    for (const [k, val] of Object.entries(v as Record<string, unknown>)) {
      out[k] = deepClean(val);
    }
    return out;
  }
  return v;
}

/** option value 专用：去掉会破坏 form schema 的字符 */
export function sanitizeOptionValue(v: string): string {
  return sanitizeForFeishu(v, 120).replace(/["\\\x00-\x1F]/g, "_");
}

/** 标准 fetch headers，强制 utf-8 */
export const FEISHU_JSON_HEADERS = {
  "Content-Type": "application/json; charset=utf-8",
  Accept: "application/json; charset=utf-8",
};

/** 统一的多选卡 option 构造器 */
export interface FeishuOption {
  text: string;
  value: string;
}

export function buildOption(text: string, value: string): {
  text: { tag: "plain_text"; content: string };
  value: string;
} {
  return {
    text: { tag: "plain_text", content: sanitizeForFeishu(text, 300) },
    value: sanitizeOptionValue(value),
  };
}
