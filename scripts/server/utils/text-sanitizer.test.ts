/**
 * 运行：cd scripts/server && bun test utils/text-sanitizer.test.ts
 */
import { describe, expect, test } from "bun:test";
import {
  sanitizeForFeishu,
  safeStringify,
  truncateByBytes,
  sanitizeOptionValue,
  buildOption,
} from "./text-sanitizer";

describe("sanitizeForFeishu", () => {
  test("去 BOM", () => {
    expect(sanitizeForFeishu("\uFEFF日生研纳豆激酶")).toBe("日生研纳豆激酶");
  });
  test("去零宽空格", () => {
    expect(sanitizeForFeishu("日\u200B生\u200C研")).toBe("日生研");
  });
  test("CRLF 归一化为 LF", () => {
    expect(sanitizeForFeishu("a\r\nb\rc")).toBe("a\nb\nc");
  });
  test("去控制字符保留换行", () => {
    expect(sanitizeForFeishu("a\x01b\nc\tD")).toBe("ab\nc\tD");
  });
  test("HTML 尖括号转义", () => {
    expect(sanitizeForFeishu("<script>")).toBe("&lt;script&gt;");
  });
  test("null/undefined 返回空串", () => {
    expect(sanitizeForFeishu(null)).toBe("");
    expect(sanitizeForFeishu(undefined)).toBe("");
  });
  test("emoji 不被破坏", () => {
    const s = "心脑血管❤️健康";
    expect(sanitizeForFeishu(s)).toBe(s);
  });
});

describe("truncateByBytes", () => {
  test("短文本原样返回", () => {
    expect(truncateByBytes("日生研", 100)).toBe("日生研");
  });
  test("超长按字节裁剪且不切坏多字节", () => {
    const s = "日".repeat(300); // 每字符 3 字节 → 900 B
    const out = truncateByBytes(s, 100);
    expect(new TextEncoder().encode(out).length).toBeLessThanOrEqual(100);
    // 不应出现 replacement char
    expect(out.includes("\uFFFD")).toBe(false);
  });
});

describe("safeStringify", () => {
  test("过滤控制字符后仍是合法 JSON", () => {
    const j = safeStringify({ msg: "hi\x01there", arr: ["a\u200Bb"] });
    const parsed = JSON.parse(j);
    expect(parsed.msg).toBe("hithere");
    expect(parsed.arr[0]).toBe("ab");
  });
});

describe("sanitizeOptionValue", () => {
  test("引号反斜杠转下划线", () => {
    expect(sanitizeOptionValue('id"with\\bad')).toBe("id_with_bad");
  });
});

describe("buildOption", () => {
  test("构造合法的飞书 option 结构", () => {
    const o = buildOption("选题 1：纳豆激酶", "topic-01");
    expect(o.text.tag).toBe("plain_text");
    expect(o.text.content).toBe("选题 1：纳豆激酶");
    expect(o.value).toBe("topic-01");
  });
  test("脏输入全部被清洗", () => {
    const o = buildOption("\uFEFF日\u200B生研", 'bad"val');
    expect(o.text.content).toBe("日生研");
    expect(o.value).toBe("bad_val");
  });
});
