#!/usr/bin/env bun
/**
 * 日生研 NSKSD · 选题库外部资讯抓取器（V9.1）
 *
 * 职责：按 M1–M6 模块的关键词池抓外部资讯，落盘到
 *       references/topic-library/{module}/{YYYY-MM}/{YYYY-MM-DD}-{slug}.md
 *
 * 用法：
 *   bun scripts/topic-crawler.ts --module M2
 *   bun scripts/topic-crawler.ts --all
 *   bun scripts/topic-crawler.ts --module M6 --limit 10
 *
 * 搜索引擎：目前用 stub（返回示例结果），接入真实搜索的 TODO 在
 *          callSearch() 处。可选后端：exa_web_search / web_search_prime /
 *          baoyu-url-to-markdown。
 */

import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";

// ============ 模块 & 关键词 ============

type Module = "M1" | "M2" | "M3" | "M4" | "M5" | "M6";

const KEYWORDS: Record<Module, string[]> = {
  M1: ["健康行业热点", "慢病管理 2026", "保健食品 政策", "大健康产业"],
  M2: [
    "纳豆激酶 临床试验",
    "NSKSD",
    "纳豆激酶 心脑血管",
    "溶栓酶 最新研究",
    "纳豆激酶 专家指南",
  ],
  M3: ["高血压管理", "动脉粥样硬化 干预", "血脂管理", "中风预防"],
  M4: ["纳豆激酶 真实案例", "心脑血管康复故事", "医生推荐 纳豆激酶"],
  M5: ["保健食品 监管", "广告法 2026", "执业药师 整治", "职业打假"],
  M6: [
    "养生馆 健康咨询",
    "美容院 健康管理",
    "健康门店 运营",
    "健康社群 裂变",
    "私域 健康咨询师",
  ],
};

const MODULE_NAME: Record<Module, string> = {
  M1: "industry-news",
  M2: "nattokinase-research",
  M3: "health-management",
  M4: "cases-stories",
  M5: "policy-regulation",
  M6: "partner-channels",
};

// ============ 搜索接入（stub） ============

interface SearchHit {
  title: string;
  url: string;
  snippet: string;
  published_at?: string;
  source?: string;
}

/**
 * TODO：接入真实搜索。推荐：
 *   - exa_web_search_exa（已在 MCP 里）
 *   - web_search_prime
 *   - 公众号（mp.weixin.qq.com）走 exa + web-reader 组合（见 GENOME）
 *
 * 当前为 stub：返回一条占位结果，保证目录结构跑通。
 */
async function callSearch(keyword: string, limit: number): Promise<SearchHit[]> {
  return [
    {
      title: `[STUB] ${keyword} — 占位结果`,
      url: "https://example.com/placeholder",
      snippet: `这是 ${keyword} 的占位摘要。接入真实搜索后此处会被真实抓取内容替换。`,
      published_at: new Date().toISOString().slice(0, 10),
      source: "stub",
    },
  ].slice(0, limit);
}

// ============ 归档 ============

function ym(d = new Date()): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}
function ymd(d = new Date()): string {
  return d.toISOString().slice(0, 10);
}

function slugify(s: string): string {
  return s
    .toLowerCase()
    .replace(/[\s\u3000]+/g, "-")
    .replace(/[^\w\u4e00-\u9fa5\-]/g, "")
    .slice(0, 50);
}

function render(hit: SearchHit, module: Module, keyword: string): string {
  return `# ${hit.title}

**来源**：${hit.source || "待补"}
**原始链接**：${hit.url}
**发布日期**：${hit.published_at || "待补"}
**抓取日期**：${ymd()}
**所属模块**：${module}
**搜索关键词**：${keyword}

## 一句话摘要
${hit.snippet.slice(0, 80)}

## 核心内容
${hit.snippet}

## 可切的选题方向（待人工补充）
1. F?·：_______
2. F?·：_______
3. F?·：_______

## 可信度与合规备注
- [ ] 信源权威性（官方/三甲/SCI）
- [ ] 无医疗承诺词
- [ ] 数据可复核

---
*自动抓取 · topic-crawler.ts v9.1*
`;
}

async function crawlModule(module: Module, limit: number, root: string): Promise<number> {
  const kws = KEYWORDS[module];
  const outDir = join(
    root,
    "references/topic-library",
    `${module}-${MODULE_NAME[module]}`,
    ym(),
  );
  if (!existsSync(outDir)) mkdirSync(outDir, { recursive: true });

  let count = 0;
  for (const kw of kws) {
    const hits = await callSearch(kw, limit);
    for (const h of hits) {
      const fileName = `${ymd()}-${slugify(h.title)}.md`;
      const fp = join(outDir, fileName);
      if (existsSync(fp)) continue;
      writeFileSync(fp, render(h, module, kw), "utf-8");
      count++;
      console.log(`  [${module}] +${fileName}`);
    }
  }
  return count;
}

// ============ 入口 ============

async function main() {
  const args = process.argv.slice(2);
  const root = process.env.SKILL_PATH || join(__dirname, "..");
  const limitIdx = args.indexOf("--limit");
  const limit = limitIdx >= 0 ? Number(args[limitIdx + 1] ?? 5) : 5;

  let modules: Module[];
  if (args.includes("--all")) {
    modules = ["M1", "M2", "M3", "M4", "M5", "M6"];
  } else {
    const mi = args.indexOf("--module");
    if (mi < 0) {
      console.error("用法：bun scripts/topic-crawler.ts --module M2 [--limit 5]");
      console.error("或  ：bun scripts/topic-crawler.ts --all");
      process.exit(1);
    }
    modules = [args[mi + 1] as Module];
  }

  console.log(`[topic-crawler] 抓取模块：${modules.join(", ")} · 每关键词 ${limit} 条`);
  let total = 0;
  for (const m of modules) total += await crawlModule(m, limit, root);
  console.log(`[topic-crawler] 完成，共 ${total} 条。`);
}

if (import.meta.main) main();
