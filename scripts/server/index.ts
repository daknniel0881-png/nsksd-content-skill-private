/**
 * 日生研NSKSD · 选题监听服务 v2（长连接模式）
 *
 * 工作原理：
 * 1. 通过飞书SDK的WSClient建立长连接（不需要公网服务器）
 * 2. 发送多选卡片到飞书（form容器 + checkbox + 提交按钮）
 * 3. 用户在卡片内勾选选题 → 点击提交 → 按钮变灰
 * 4. 服务收到card.action.trigger回调 → 解析form_value → 触发写稿+排版
 * 5. 写稿完成后推送进度卡片和完成通知卡片
 *
 * 运行方式：bun run index.ts
 */

import * as Lark from "@larksuiteoapi/node-sdk";

// ============ 配置 ============

const APP_ID = process.env.LARK_APP_ID || "";
const APP_SECRET = process.env.LARK_APP_SECRET || "";
const TARGET_OPEN_ID = process.env.TARGET_OPEN_ID || "";
const SKILL_PATH = process.env.SKILL_PATH || "/tmp/nsksd-content-skill";
const CHAT_ID = process.env.CHAT_ID || "oc_593f103b3d1f80ca34b728de58a31ac1";
const FORMAT_SCRIPT = `${SKILL_PATH}/scripts/format/format.py`;
const FORMAT_OUTPUT_DIR = process.env.FORMAT_OUTPUT_DIR || "/tmp/wechat-format";

/** 根据内容线自动选择温暖简洁的排版主题 */
const THEME_MAP: Record<string, string> = {
  "科学信任": "mint-fresh",
  "健康科普": "mint-fresh",
  "品牌故事": "coffee-house",
  "招商转化": "sunset-amber",
};
const DEFAULT_THEME = "mint-fresh";

if (!APP_ID || !APP_SECRET) {
  console.error("请设置环境变量 LARK_APP_ID 和 LARK_APP_SECRET");
  process.exit(1);
}

// ============ 选题存储 ============

interface Topic {
  id: string;
  index: number;
  title: string;
  summary: string;  // 一句话摘要，卡片中显示在标题下方
  grade: string;
  line: string;
  score: string;
  compliance: string;
}

let currentTopics: Topic[] = [];
let isGenerating = false;

export function registerTopics(topics: Topic[]) {
  currentTopics = topics;
  console.log(`[Register] 已注册 ${topics.length} 个选题`);
}

// ============ 预置选题（开发调试用） ============

const FFC_TOPICS: Topic[] = [
  { id: "ffc_1", index: 1, title: "5元成本卖300，纳豆激酶市场到底有多乱？", summary: "揭露行业乱象，用价格对比建立品牌信任", grade: "S", line: "品牌故事", score: "95", compliance: "🟢" },
  { id: "ffc_2", index: 2, title: "1062人、12个月、4家医院：最硬核的成绩单", summary: "用临床数据说话，最有说服力的科学背书", grade: "S", line: "科学信任", score: "92", compliance: "🟡" },
  { id: "ffc_3", index: 3, title: "你吃的纳豆激酶是真的吗？5个鉴别方法", summary: "实用鉴别指南，帮用户建立选品标准", grade: "S", line: "健康科普", score: "90", compliance: "🟢" },
  { id: "ffc_4", index: 4, title: "4月24日杭州，纳豆激酶行业可能要变天了", summary: "行业大会预热，制造紧迫感和期待", grade: "A", line: "品牌故事", score: "87", compliance: "🟢" },
  { id: "ffc_5", index: 5, title: "这场论坛的专家阵容有多硬？", summary: "专家背书阵容前瞻，强化学术权威感", grade: "A", line: "科学信任", score: "85", compliance: "🟡" },
  { id: "ffc_6", index: 6, title: "门店老板该关注这场大会的3件事", summary: "养生馆老板必须关注这个大会，有3个重要信号", grade: "A", line: "招商转化", score: "83", compliance: "🟢" },
  { id: "ffc_7", index: 7, title: "养生馆老板：你还在靠手艺赚钱吗？", summary: "痛点切入，从手艺人转型到品牌经营者", grade: "A", line: "招商转化", score: "81", compliance: "🟢" },
  { id: "ffc_8", index: 8, title: "从经销商到临床研究推动者，日生研15年", summary: "品牌发展史，用时间线讲企业蜕变故事", grade: "B", line: "品牌故事", score: "78", compliance: "🟢" },
  { id: "ffc_9", index: 9, title: "明天见！亮点剧透+观看指南", summary: "大会前最后预热，降低参与门槛", grade: "B", line: "品牌故事", score: "75", compliance: "🟢" },
  { id: "ffc_10", index: 10, title: "一个纳豆激酶经销商的真实账本", summary: "真实经营数据，用账本说服潜在加盟者", grade: "B", line: "招商转化", score: "73", compliance: "🟢" },
];
registerTopics(FFC_TOPICS);

// ============ 飞书客户端 ============

const client = new Lark.Client({
  appId: APP_ID,
  appSecret: APP_SECRET,
  appType: Lark.AppType.SelfBuild,
});

async function sendText(chatId: string, text: string) {
  await client.im.v1.message.create({
    params: { receive_id_type: "chat_id" },
    data: { receive_id: chatId, msg_type: "text", content: JSON.stringify({ text }) },
  });
}

async function sendCardToUser(openId: string, card: object) {
  const resp = await client.im.v1.message.create({
    params: { receive_id_type: "open_id" },
    data: { receive_id: openId, msg_type: "interactive", content: JSON.stringify(card) },
  });
  return resp;
}

async function sendCardToChat(chatId: string, card: object) {
  const resp = await client.im.v1.message.create({
    params: { receive_id_type: "chat_id" },
    data: { receive_id: chatId, msg_type: "interactive", content: JSON.stringify(card) },
  });
  return resp;
}

// ============ 卡片构建 ============

/** 当日飞书云文档 URL（由定时脚本注入） */
let todayDocUrl = "";

/**
 * 构建选题清单卡片（第一张卡片 — 纯展示）
 *
 * 按 S/A/B 分级列出所有选题概览 + 一个「查看详情」按钮跳转飞书云文档
 */
function buildSummaryCard(topics: Topic[], docUrl: string): object {
  const today = new Date().toLocaleDateString("zh-CN", { month: "long", day: "numeric" });
  const gradeEmoji: Record<string, string> = { S: "🏆", A: "⭐", B: "📌" };

  const elements: any[] = [];

  // 按等级分组
  for (const grade of ["S", "A", "B"]) {
    const group = topics.filter(t => t.grade === grade);
    if (group.length === 0) continue;

    const label = grade === "S" ? "🏆 S级（强烈推荐）" : grade === "A" ? "⭐ A级（推荐）" : "📌 B级（可选）";
    elements.push({ tag: "markdown", content: `**${label}**` });

    for (const t of group) {
      const line = `${t.index}. **${t.title}**\n${t.line}（${t.score}分）${t.compliance}　${t.summary || ""}`;
      elements.push({ tag: "markdown", content: line });
    }

    elements.push({ tag: "hr" });
  }

  // 底部：查看飞书云文档按钮
  if (docUrl) {
    elements.push({
      tag: "action",
      actions: [
        {
          tag: "button",
          text: { tag: "plain_text", content: "📄 查看完整选题方案" },
          type: "primary",
          multi_url: { url: docUrl, android_url: docUrl, ios_url: docUrl, pc_url: docUrl },
        },
      ],
    });
  }

  // 清单卡是纯展示，不需要 form 回调，用 schema 1.0（支持 action tag）
  return {
    header: {
      title: { tag: "plain_text", content: `📋 ${today} 选题清单` },
      template: "green",
    },
    elements,
  };
}

/**
 * 构建多选选题卡片（第二张卡片 — 核心交互）
 *
 * 结构：form容器 > 多个checker勾选组件 + 提交按钮
 * 用户勾选 → 点提交 → card.action.trigger回调 → form_value: { topic_1: true, topic_3: true, ... }
 *
 * 注意：checker 在 form 内时不配 behaviors（避免200672），只靠 form 提交按钮触发回调
 */
function buildSelectCard(topics: Topic[], disabled = false): object {
  const today = new Date().toLocaleDateString("zh-CN", { month: "long", day: "numeric" });
  const gradeEmoji: Record<string, string> = { S: "🏆", A: "⭐", B: "📌" };

  // 每个选题：一个 markdown 标签行 + 一个 checker 勾选
  // markdown 显示加粗等级+分数，checker 显示标题+摘要
  const topicElements: any[] = [];

  // 按等级分组显示
  const gradeGroups = ["S", "A", "B"];
  for (const grade of gradeGroups) {
    const gradeTopics = topics.filter(t => t.grade === grade);
    if (gradeTopics.length === 0) continue;

    // 等级分隔标题
    const gradeLabel = grade === "S" ? "🏆 S级（强烈推荐）" : grade === "A" ? "⭐ A级（推荐）" : "📌 B级（可选）";
    topicElements.push({
      tag: "markdown",
      content: `**${gradeLabel}**`,
    });

    // 该等级下的选题 checker
    for (const t of gradeTopics) {
      topicElements.push({
        tag: "checker",
        name: `topic_${t.index}`,
        checked: false,
        overall_checkable: true,
        text: {
          tag: "plain_text",
          content: `${t.line}（${t.score}分）${t.compliance}  ${t.title}\n${t.summary || ""}`,
        },
        ...(disabled ? { disabled: true } : {}),
      });
    }

    // 等级间加分割线（最后一组不加）
    if (grade !== gradeGroups[gradeGroups.length - 1]) {
      topicElements.push({ tag: "hr" });
    }
  }

  // form 内的元素：说明 + checkers + 提交按钮
  const formElements: any[] = [
    {
      tag: "markdown",
      content: "**勾选要创作的选题：**",
    },
    ...topicElements,
    {
      tag: "button",
      text: {
        tag: "plain_text",
        content: disabled ? "✅ 已提交，正在创作中..." : "📝 提交选题，开始创作",
      },
      type: disabled ? "default" : "primary",
      form_action_type: "submit",
      name: "submit_btn",
      ...(disabled ? { disabled: true } : {}),
    },
  ];

  const card = {
    schema: "2.0",
    config: { update_multi: true, width_mode: "fill" },
    header: {
      title: { tag: "plain_text", content: `📋 日生研NSKSD · ${today}选题（共${topics.length}篇）` },
      subtitle: { tag: "plain_text", content: disabled ? "已提交，文案创作中..." : "勾选后点击提交，自动生成文案并排版" },
      template: disabled ? "grey" : "blue",
    },
    body: {
      direction: "vertical",
      padding: "12px 12px 12px 12px",
      elements: [
        {
          tag: "form",
          name: "topic_form",
          elements: formElements,
        },
      ],
    },
  };

  return card;
}

/**
 * 构建"正在创作"进度通知卡片
 */
function buildProgressCard(selectedTopics: Topic[]): object {
  const list = selectedTopics.map(t => `${t.index}. ${t.title}`).join("\n");
  return {
    schema: "2.0",
    config: { update_multi: true, width_mode: "fill" },
    header: {
      title: { tag: "plain_text", content: "⏳ 正在生成文稿..." },
      subtitle: { tag: "plain_text", content: `共 ${selectedTopics.length} 篇，预计每篇2-5分钟` },
      template: "orange",
    },
    body: {
      direction: "vertical",
      padding: "12px 12px 12px 12px",
      elements: [
        {
          tag: "markdown",
          content: `已提交以下选题，正在调用 Claude 撰写初稿：\n\n${list}\n\n完成后会发送通知，请稍候…`,
        },
      ],
    },
  };
}

/**
 * 构建"创作完成"通知卡片
 */
function buildCompletionCard(results: { topic: Topic; success: boolean; formatted?: boolean; published?: boolean }[]): object {
  const successCount = results.filter(r => r.success).length;
  const failCount = results.filter(r => !r.success).length;
  const publishedCount = results.filter(r => r.published).length;

  const list = results.map(r => {
    if (!r.success) return `❌ ${r.topic.index}. ${r.topic.title}（生成失败）`;
    if (r.published) return `✅ ${r.topic.index}. ${r.topic.title}（已推送草稿箱）`;
    if (r.formatted) return `⚠️ ${r.topic.index}. ${r.topic.title}（已排版，推送失败）`;
    return `⚠️ ${r.topic.index}. ${r.topic.title}（排版失败）`;
  }).join("\n");

  const allPublished = publishedCount === successCount && successCount > 0;
  const subtitle = allPublished
    ? `全部 ${publishedCount} 篇已推送到草稿箱`
    : `成功 ${successCount} 篇，已推送 ${publishedCount} 篇${failCount > 0 ? `，失败 ${failCount} 篇` : ""}`;

  return {
    schema: "2.0",
    config: { update_multi: true, width_mode: "fill" },
    header: {
      title: { tag: "plain_text", content: allPublished ? "✅ 全部完成，已推送草稿箱" : "⚠️ 文稿生成完成（部分需手动处理）" },
      subtitle: { tag: "plain_text", content: subtitle },
      template: allPublished ? "green" : "orange",
    },
    body: {
      direction: "vertical",
      padding: "12px 12px 12px 12px",
      elements: [
        {
          tag: "markdown",
          content: `${list}\n\n${allPublished ? "所有文稿已推送到公众号草稿箱，请前往检查发布👇" : "请前往公众号后台草稿箱检查👇"}`,
        },
        {
          tag: "button",
          text: { tag: "plain_text", content: "📝 前往公众号草稿箱" },
          type: "primary",
          size: "medium",
          behaviors: [{ type: "open_url", default_url: "https://mp.weixin.qq.com" }],
        },
      ],
    },
  };
}

// ============ 文案生成 & 排版 ============

async function generateArticle(topicTitle: string): Promise<string> {
  const prompt = `你是一个微信公众号文案写手。请阅读 ${SKILL_PATH}/SKILL.md 了解写作规范，然后阅读 ${SKILL_PATH}/references/ 下的参考文件获取素材。

现在为以下选题写一篇完整的微信公众号文章：

选题：${topicTitle}

【输出要求 - 极其重要】
1. 直接输出 Markdown 格式的文章正文，1500-2500字
2. 禁止输出任何非文章内容：不要写"好的""收到"、不要写分析过程、不要写合规自查表、不要写总结说明
3. 第一行必须是文章标题（# 标题），最后一行是文章正文的结尾
4. 文章结构：标题 → 引子 → 正文（3-5个段落，用 ## 分节）→ 结尾
5. 遵循健康科普写作合规规范，不做功效承诺
6. 段落之间必须空一行，保持简洁干净的排版节奏
7. 这是一篇可以直接发布的公众号文章，禁止包含以下内容：
   - 评分、分级标记（S级/A级/🟢/🟡等）
   - "本文由AI生成"等暴露AI身份的声明
   - 合规检查结果、审查报告
   - "免责声明""温馨提示"等模板化尾注
   - 素材来源清单、参考文献列表
   文末如需提醒读者注意健康，用一句自然的话融入正文收尾即可（如"具体情况还是得问医生"），不要单独起一段做声明

再次强调：只输出文章本身的 Markdown 文本，不要任何额外的对话、解释或附注。`;

  const claudeBin = process.env.CLAUDE_BIN || "/opt/homebrew/bin/claude";
  console.log(`[Generate] 调用 Claude CLI: ${claudeBin}`);

  const proc = Bun.spawn([claudeBin, "-p", prompt], {
    stdout: "pipe",
    stderr: "pipe",
    env: {
      ...process.env,
      CLAUDE_NO_TELEMETRY: "1",
      PATH: `${process.env.PATH || ""}:/opt/homebrew/bin:/usr/local/bin:/usr/bin`,
    },
  });

  const output = await new Response(proc.stdout).text();
  const exitCode = await proc.exited;

  if (exitCode !== 0) {
    const stderr = await new Response(proc.stderr).text();
    throw new Error(`Claude CLI执行失败: ${stderr.slice(0, 200)}`);
  }
  return output;
}

async function formatArticle(article: string, topic: Topic): Promise<{ htmlPath: string; success: boolean }> {
  const theme = THEME_MAP[topic.line] || DEFAULT_THEME;
  const safeTitle = topic.title.replace(/[\/\\:*?"<>|]/g, "_");
  const mdPath = `/tmp/nsksd-article-${topic.index}-${Date.now()}.md`;
  const outputDir = `${FORMAT_OUTPUT_DIR}/${safeTitle}`;

  try {
    await Bun.write(mdPath, article);
    await Bun.spawn(["mkdir", "-p", outputDir]).exited;

    console.log(`[Format] 排版: ${topic.title} (主题: ${theme})`);

    const proc = Bun.spawn([
      "python3", FORMAT_SCRIPT,
      "--input", mdPath, "--theme", theme, "--output", outputDir, "--no-open",
    ], { stdout: "pipe", stderr: "pipe" });

    const stdout = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    if ((await proc.exited) !== 0) {
      console.error(`[Format] 排版失败: ${stderr}`);
      return { htmlPath: "", success: false };
    }
    console.log(`[Format] format.py 输出: ${stdout.slice(-200)}`);

    // format.py 会在 outputDir 下创建以文件stem命名的子目录
    // 递归搜索 article.html
    const findProc = Bun.spawn(["find", outputDir, "-name", "article.html", "-type", "f"], { stdout: "pipe" });
    const findOut = await new Response(findProc.stdout).text();
    await findProc.exited;

    const htmlFiles = findOut.trim().split("\n").filter(Boolean);
    if (htmlFiles.length > 0) {
      const htmlPath = htmlFiles[0];
      console.log(`[Format] 找到排版文件: ${htmlPath}`);
      return { htmlPath, success: true };
    }

    console.error(`[Format] 未找到 article.html，目录内容: ${findOut}`);
    return { htmlPath: "", success: false };
  } catch (err) {
    console.error(`[Format] 排版异常:`, err);
    return { htmlPath: "", success: false };
  }
}

const PUBLISH_SCRIPT = `${SKILL_PATH}/scripts/format/publish.py`;
const DEFAULT_COVER = `${SKILL_PATH}/assets/default-cover.jpg`;

/** 调用 publish.py 将排版后的文章推送到公众号草稿箱 */
async function publishArticle(topic: Topic, articleDir: string): Promise<{ success: boolean; mediaId?: string }> {
  try {
    // 确保目录下有封面图（publish.py 必须有封面图才能推送）
    const imagesDir = `${articleDir}/images`;
    const coverDst = `${imagesDir}/cover.jpg`;
    await Bun.spawn(["mkdir", "-p", imagesDir]).exited;
    if (!(await Bun.file(coverDst).exists())) {
      await Bun.spawn(["cp", DEFAULT_COVER, coverDst]).exited;
      console.log(`[Publish] 使用默认封面图`);
    }

    console.log(`[Publish] 推送草稿箱: ${topic.title} (目录: ${articleDir})`);

    const proc = Bun.spawn([
      "python3", PUBLISH_SCRIPT,
      "--dir", articleDir,
      "--title", topic.title,
      "--cover", coverDst,
    ], {
      stdout: "pipe",
      stderr: "pipe",
      env: {
        ...process.env,
        // publish.py 会从环境变量或 config.json 读取微信凭据
        WECHAT_APP_ID: process.env.WECHAT_APP_ID || "",
        WECHAT_APP_SECRET: process.env.WECHAT_APP_SECRET || "",
      },
    });

    const stdout = await new Response(proc.stdout).text();
    const stderr = await new Response(proc.stderr).text();
    const exitCode = await proc.exited;

    if (exitCode !== 0) {
      console.error(`[Publish] 推送失败: ${stderr || stdout}`);
      return { success: false };
    }

    // 从输出中提取 media_id
    const mediaIdMatch = stdout.match(/草稿 media_id:\s*(\S+)/);
    const mediaId = mediaIdMatch ? mediaIdMatch[1] : undefined;

    console.log(`[Publish] 推送成功: ${topic.title}${mediaId ? ` (media_id: ${mediaId})` : ""}`);
    return { success: true, mediaId };
  } catch (err) {
    console.error(`[Publish] 推送异常:`, err);
    return { success: false };
  }
}

// ============ 选题处理主流程 ============

async function handleTopicSelection(openId: string, selectedValues: string[]) {
  if (isGenerating) {
    await sendCardToUser(openId, {
      schema: "2.0",
      header: { title: { tag: "plain_text", content: "⚠️ 任务进行中" }, template: "orange" },
      body: { elements: [{ tag: "markdown", content: "上一批选题还在创作中，请等待完成后再提交。" }] },
    });
    return;
  }

  // 从 checkbox value 解析选题编号：topic_1 → 1
  const numbers = selectedValues
    .filter(v => v.startsWith("topic_"))
    .map(v => parseInt(v.replace("topic_", ""), 10))
    .filter(n => !isNaN(n));

  const selectedTopics = numbers
    .map(n => currentTopics.find(t => t.index === n))
    .filter(Boolean) as Topic[];

  if (selectedTopics.length === 0) {
    console.log("[Handle] 未匹配到有效选题");
    return;
  }

  isGenerating = true;
  console.log(`[Handle] 开始处理 ${selectedTopics.length} 个选题: ${selectedTopics.map(t => t.title).join(", ")}`);

  // 发送进度通知卡片
  await sendCardToUser(openId, buildProgressCard(selectedTopics));

  // 逐个生成 → 排版 → 推送草稿箱
  const results: { topic: Topic; success: boolean; formatted: boolean; published: boolean; htmlPath: string }[] = [];

  for (const topic of selectedTopics) {
    try {
      // 第1步：Claude 写稿
      console.log(`[Generate] 开始写稿: ${topic.title}`);
      const article = await generateArticle(topic.title);

      // 发送文案预览（分段）
      const chunks = splitText(article, 4000);
      for (let i = 0; i < chunks.length; i++) {
        const prefix = i === 0 ? `【第${topic.index}篇】${topic.title}\n${"=".repeat(30)}\n\n` : "";
        await sendText(CHAT_ID, prefix + chunks[i]);
      }

      // 第2步：排版
      console.log(`[Generate] 写稿完成，开始排版: ${topic.title}`);
      const fmtResult = await formatArticle(article, topic);

      if (fmtResult.success) {
        await sendText(CHAT_ID, `✅ 【第${topic.index}篇】排版完成 (${THEME_MAP[topic.line] || DEFAULT_THEME})`);
      }

      // 第3步：推送到公众号草稿箱
      let published = false;
      if (fmtResult.success && fmtResult.htmlPath) {
        // htmlPath 类似 /tmp/wechat-format/标题/article.html，取其父目录
        const articleDir = fmtResult.htmlPath.replace(/\/[^/]+$/, "");
        console.log(`[Generate] 排版完成，开始推送草稿箱: ${topic.title}`);
        const pubResult = await publishArticle(topic, articleDir);
        published = pubResult.success;

        if (published) {
          await sendText(CHAT_ID, `📤 【第${topic.index}篇】已推送到公众号草稿箱`);
        } else {
          await sendText(CHAT_ID, `⚠️ 【第${topic.index}篇】排版成功但推送草稿箱失败，请手动处理`);
        }
      }

      results.push({ topic, success: true, formatted: fmtResult.success, published, htmlPath: fmtResult.htmlPath });
    } catch (err) {
      console.error(`[Generate] 失败: ${topic.title}`, err);
      results.push({ topic, success: false, formatted: false, published: false, htmlPath: "" });
    }
  }

  // 发送完成通知卡片
  await sendCardToUser(openId, buildCompletionCard(results));
  isGenerating = false;
  console.log(`[Handle] 全部完成，成功 ${results.filter(r => r.success).length} 篇`);
}

function splitText(text: string, maxLen: number): string[] {
  if (text.length <= maxLen) return [text];
  const chunks: string[] = [];
  let start = 0;
  while (start < text.length) {
    let end = Math.min(start + maxLen, text.length);
    if (end < text.length) {
      const nl = text.lastIndexOf("\n", end);
      if (nl > start + maxLen * 0.5) end = nl + 1;
    }
    chunks.push(text.slice(start, end));
    start = end;
  }
  return chunks;
}

/** 解析用户文本消息中的选题编号 */
function parseTopicNumbers(text: string): number[] {
  text = text.trim();
  const parts = text.split(/[,，、\s]+/).filter(Boolean);
  let nums: number[] = [];
  for (const p of parts) {
    const n = parseInt(p, 10);
    if (!isNaN(n) && n >= 1 && n <= currentTopics.length) nums.push(n);
  }
  if (nums.length === 0 && /^\d+$/.test(text) && text.length <= currentTopics.length) {
    for (const ch of text) {
      const n = parseInt(ch, 10);
      if (n >= 1 && n <= currentTopics.length) nums.push(n);
    }
  }
  return [...new Set(nums)];
}

// ============ WSClient 长连接 ============

console.log(`
╔══════════════════════════════════════════════════╗
║  日生研NSKSD · 选题监听服务 v2                     ║
║                                                    ║
║  卡片多选 + 提交按钮 + 自动写稿排版                  ║
║  WSClient 长连接，不需要公网IP                       ║
╚══════════════════════════════════════════════════╝
`);

const wsClient = new Lark.WSClient({
  appId: APP_ID,
  appSecret: APP_SECRET,
  loggerLevel: Lark.LoggerLevel.info,
});

wsClient.start({
  eventDispatcher: new Lark.EventDispatcher({}).register({

    // ============ 卡片回调：处理form表单提交 ============
    "card.action.trigger": async (data: any) => {
      try {
        const event = data?.event || data;
        const action = event?.action || {};
        const openId = event?.operator?.open_id;
        const formValue = action?.form_value || {};
        const actionValue = action?.value || {};

        console.log(`[CardAction] ===== 收到卡片回调 =====`);
        console.log(`[CardAction] operator: ${openId}`);
        console.log(`[CardAction] action.tag: ${action?.tag}`);
        console.log(`[CardAction] action.value:`, JSON.stringify(actionValue));
        console.log(`[CardAction] form_value:`, JSON.stringify(formValue));
        console.log(`[CardAction] 完整event:`, JSON.stringify(event, null, 2));

        // form表单提交：form_value 格式为 { "topic_1": true, "topic_3": true, "submit_btn": {...} }
        // checker 组件的值是布尔型，true = 已勾选
        const selectedValues: string[] = [];
        for (const [key, value] of Object.entries(formValue)) {
          if (key.startsWith("topic_") && value === true) {
            selectedValues.push(key);
          }
        }

        if (selectedValues.length > 0) {
          console.log(`[CardAction] 选中的选题: ${selectedValues.join(", ")}`);

          // 异步处理写稿（不阻塞3秒超时）
          handleTopicSelection(openId, selectedValues).catch(err => {
            console.error("[CardAction] 写稿流程失败:", err);
          });

          // 返回toast + 更新卡片（按钮变灰）
          return {
            toast: {
              type: "success",
              content: `已提交 ${selectedValues.length} 个选题，开始创作...`,
            },
            card: {
              type: "raw",
              data: buildSelectCard(currentTopics, true),
            },
          };
        }

        // form_value 存在但没有勾选任何选题
        if (Object.keys(formValue).length > 0) {
          console.log(`[CardAction] 提交了但未勾选选题，form_value:`, JSON.stringify(formValue));
          return {
            toast: { type: "warning", content: "请先勾选要创作的选题，再点击提交" },
          };
        }

        console.log(`[CardAction] 未识别的回调类型，忽略`);
        return {};
      } catch (err) {
        console.error("[CardAction] 处理卡片回调出错:", err);
        return { toast: { type: "error", content: "处理失败，请重试" } };
      }
    },

    // ============ 消息事件：文本回复编号（备选方案） ============
    "im.message.receive_v1": async (data: any) => {
      try {
        const message = data.message;
        const chatId = message.chat_id;
        const senderId = data.sender?.sender_id?.open_id;
        if (message.message_type !== "text") return;

        const content = JSON.parse(message.content);
        const text = content.text?.trim();
        if (!text) return;

        console.log(`[Message] 收到消息: "${text}" from ${senderId}`);

        const numbers = parseTopicNumbers(text);
        if (numbers.length > 0 && currentTopics.length > 0) {
          console.log(`[Message] 解析到选题编号: ${numbers.join(", ")}`);
          const values = numbers.map(n => `topic_${n}`);
          handleTopicSelection(senderId, values).catch(err => {
            console.error("[Handle] 处理失败:", err);
          });
        } else if (text === "选题列表" || text === "查看选题") {
          if (currentTopics.length === 0) {
            await sendText(chatId, "当前没有待选的选题。");
          } else {
            const list = currentTopics.map(t => `${t.index}. [${t.grade}] ${t.title}（${t.score}分）`).join("\n");
            await sendText(chatId, `当前选题（${currentTopics.length}篇）：\n\n${list}`);
          }
        } else if (text === "帮助" || text === "help") {
          await sendText(chatId, "日生研NSKSD · 选题助手\n═══════════════\n\n直接在卡片中勾选选题并提交即可。\n也可以回复编号：1 3 5");
        }
      } catch (err) {
        console.error("[Message] 处理消息时出错:", err);
      }
    },
  }),
});

console.log("[WSClient] 正在连接飞书长连接服务...");

// ============ 本地HTTP管理端口 ============

const httpServer = Bun.serve({
  port: Number(process.env.PORT) || 9800,
  async fetch(req) {
    const url = new URL(req.url);

    // 健康检查
    if (url.pathname === "/health") {
      return Response.json({
        status: "ok",
        version: "v2",
        mode: "websocket+card_callback",
        topics: currentTopics.length,
        generating: isGenerating,
      });
    }

    // 注册选题
    if (url.pathname === "/register-topics" && req.method === "POST") {
      const body = await req.json() as any;
      const topics = (body.topics || []).map((t: any, i: number) => ({ ...t, index: t.index || i + 1 }));
      registerTopics(topics);
      return Response.json({ code: 0, registered: currentTopics.length });
    }

    // 设置飞书云文档URL（定时脚本注入）
    if (url.pathname === "/set-doc-url" && req.method === "POST") {
      const body = await req.json() as any;
      todayDocUrl = body.doc_url || "";
      console.log(`[HTTP] 云文档URL已设置: ${todayDocUrl}`);
      return Response.json({ code: 0 });
    }

    // 发送清单卡片（第一张：选题概览 + 飞书云文档链接）
    if (url.pathname === "/send-summary-card" && req.method === "POST") {
      const body = await req.json() as any;
      const targetId = body.open_id || TARGET_OPEN_ID;
      const docUrl = body.doc_url || todayDocUrl;
      try {
        const card = buildSummaryCard(currentTopics, docUrl);
        const resp = await sendCardToUser(targetId, card);
        console.log(`[HTTP] 清单卡片已发送到 ${targetId}`);
        return Response.json({ code: 0, message_id: (resp as any)?.data?.message_id });
      } catch (err: any) {
        const respData = err?.response?.data;
        console.error("[HTTP] 发送清单卡片失败:", err.message, "response:", JSON.stringify(respData));
        return Response.json({ code: 1, error: err.message, detail: respData }, { status: 500 });
      }
    }

    // 发送多选卡片（第二张：勾选选题触发写稿流程）
    if (url.pathname === "/send-card" && req.method === "POST") {
      const body = await req.json() as any;
      const targetId = body.open_id || TARGET_OPEN_ID;
      try {
        const card = buildSelectCard(currentTopics);
        const resp = await sendCardToUser(targetId, card);
        console.log(`[HTTP] 卡片已发送到 ${targetId}`);
        return Response.json({ code: 0, message_id: (resp as any)?.data?.message_id });
      } catch (err: any) {
        console.error("[HTTP] 发送卡片失败:", err);
        return Response.json({ code: 1, error: err.message }, { status: 500 });
      }
    }

    // 查看状态
    if (url.pathname === "/status") {
      return Response.json({ topics: currentTopics, generating: isGenerating });
    }

    return new Response("NSKSD Topic Listener v2 (WSClient + Card Callback)");
  },
});

console.log(`[HTTP] 本地管理端口: http://localhost:${httpServer.port}`);
console.log(`[HTTP] 发送卡片: curl -X POST http://localhost:${httpServer.port}/send-card -H 'Content-Type: application/json' -d '{}'`);
