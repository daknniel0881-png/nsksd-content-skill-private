/**
 * 日生研NSKSD · 选题监听服务（长连接模式）
 *
 * 工作原理：
 * 1. 通过飞书SDK的WSClient建立长连接（不需要公网服务器）
 * 2. 发送选题卡片到飞书（带编号的选题列表）
 * 3. 用户在飞书中回复选题编号（如"1 3 5"）
 * 4. 服务自动触发Claude CLI生成文案
 * 5. 生成的文案通过飞书推送给用户
 *
 * 运行方式：bun run index.ts
 *
 * 优势：
 * - 不需要公网IP或域名
 * - 不需要内网穿透（ngrok等）
 * - 不需要配置防火墙或白名单
 * - 本地运行即可，5分钟接入
 */

import * as Lark from "@larksuiteoapi/node-sdk";

// ============ 配置 ============

const APP_ID = process.env.LARK_APP_ID || "";
const APP_SECRET = process.env.LARK_APP_SECRET || "";
const TARGET_OPEN_ID = process.env.TARGET_OPEN_ID || "";
const SKILL_PATH = process.env.SKILL_PATH || "/tmp/nsksd-content-skill";

if (!APP_ID || !APP_SECRET) {
  console.error("请设置环境变量 LARK_APP_ID 和 LARK_APP_SECRET");
  console.error("参考 .env.example 文件配置");
  process.exit(1);
}

// ============ 选题存储 ============

interface Topic {
  id: string;
  index: number;
  title: string;
  grade: string;
  line: string;
  score: string;
  compliance: string;
}

let currentTopics: Topic[] = [];
let isGenerating = false;

/**
 * 注册选题列表
 */
export function registerTopics(topics: Topic[]) {
  currentTopics = topics;
  console.log(`[Register] 已注册 ${topics.length} 个选题`);
}

// ============ 预置FFC 2026选题 ============

const FFC_TOPICS: Topic[] = [
  { id: "ffc_1", index: 1, title: "5元成本卖300，纳豆激酶市场到底有多乱？", grade: "S", line: "品牌故事", score: "95", compliance: "🟢" },
  { id: "ffc_2", index: 2, title: "1062人、12个月、4家医院：最硬核的成绩单", grade: "S", line: "科学信任", score: "92", compliance: "🟡" },
  { id: "ffc_3", index: 3, title: "你吃的纳豆激酶是真的吗？5个鉴别方法", grade: "S", line: "健康科普", score: "90", compliance: "🟢" },
  { id: "ffc_4", index: 4, title: "4月24日杭州，纳豆激酶行业可能要变天了", grade: "A", line: "品牌故事", score: "87", compliance: "🟢" },
  { id: "ffc_5", index: 5, title: "这场论坛的专家阵容有多硬？", grade: "A", line: "科学信任", score: "85", compliance: "🟡" },
  { id: "ffc_6", index: 6, title: "门店老板该关注这场大会的3件事", grade: "A", line: "招商转化", score: "83", compliance: "🟢" },
  { id: "ffc_7", index: 7, title: "养生馆老板：你还在靠手艺赚钱吗？", grade: "A", line: "招商转化", score: "81", compliance: "🟢" },
  { id: "ffc_8", index: 8, title: "从经销商到临床研究推动者，日生研15年", grade: "B", line: "品牌故事", score: "78", compliance: "🟢" },
  { id: "ffc_9", index: 9, title: "明天见！亮点剧透+观看指南", grade: "B", line: "品牌故事", score: "75", compliance: "🟢" },
  { id: "ffc_10", index: 10, title: "一个纳豆激酶经销商的真实账本", grade: "B", line: "招商转化", score: "73", compliance: "🟢" },
];

// 启动时自动注册
registerTopics(FFC_TOPICS);

// ============ 飞书客户端 ============

const client = new Lark.Client({
  appId: APP_ID,
  appSecret: APP_SECRET,
  appType: Lark.AppType.SelfBuild,
});

/**
 * 发送文本消息
 */
async function sendText(chatId: string, text: string) {
  await client.im.v1.message.create({
    params: { receive_id_type: "chat_id" },
    data: {
      receive_id: chatId,
      msg_type: "text",
      content: JSON.stringify({ text }),
    },
  });
}

/**
 * 发送文本消息（通过open_id）
 */
async function sendTextToUser(openId: string, text: string) {
  await client.im.v1.message.create({
    params: { receive_id_type: "open_id" },
    data: {
      receive_id: openId,
      msg_type: "text",
      content: JSON.stringify({ text }),
    },
  });
}

/**
 * 发送卡片消息（通过open_id）
 */
async function sendCardToUser(openId: string, card: object) {
  await client.im.v1.message.create({
    params: { receive_id_type: "open_id" },
    data: {
      receive_id: openId,
      msg_type: "interactive",
      content: JSON.stringify(card),
    },
  });
}

/**
 * 更新卡片消息（用message_id更新原卡片内容）
 */
async function updateCard(messageId: string, card: object) {
  await client.im.v1.message.patch({
    path: { message_id: messageId },
    data: {
      content: JSON.stringify(card),
    },
  });
}

/**
 * 发送"正在写稿"进度通知卡片
 */
async function sendProgressCard(openId: string, selectedTopics: Topic[]) {
  const list = selectedTopics.map(t => `${t.index}. ${t.title}`).join("\n");
  const card = {
    schema: "2.0",
    config: { update_multi: true, width_mode: "fill" },
    header: {
      title: { tag: "plain_text", content: "\u23f3 \u6b63\u5728\u751f\u6210\u6587\u7a3f..." },
      subtitle: { tag: "plain_text", content: `\u5171 ${selectedTopics.length} \u7bc7\uff0c\u9884\u8ba1\u6bcf\u7bc72-5\u5206\u949f` },
      template: "orange",
    },
    body: {
      direction: "vertical",
      padding: "12px 12px 12px 12px",
      elements: [
        {
          tag: "markdown",
          content: `\u5df2\u63d0\u4ea4\u4ee5\u4e0b\u9009\u9898\uff0c\u6b63\u5728\u8c03\u7528 Claude \u64b0\u5199\u521d\u7a3f\uff1a\n\n${list}\n\n\u5b8c\u6210\u540e\u4f1a\u53d1\u9001\u901a\u77e5\uff0c\u8bf7\u7a0d\u5019\u2026`,
        },
      ],
    },
  };
  await sendCardToUser(openId, card);
}

/**
 * 发送"写稿完成"通知卡片
 */
async function sendCompletionCard(openId: string, selectedTopics: Topic[], results: { topic: Topic; success: boolean }[]) {
  const successCount = results.filter(r => r.success).length;
  const failCount = results.filter(r => !r.success).length;
  const list = results.map(r =>
    r.success
      ? `\u2705 ${r.topic.index}. ${r.topic.title}`
      : `\u274c ${r.topic.index}. ${r.topic.title}\uff08\u751f\u6210\u5931\u8d25\uff09`
  ).join("\n");

  const card = {
    schema: "2.0",
    config: { update_multi: true, width_mode: "fill" },
    header: {
      title: { tag: "plain_text", content: `\u2705 \u6587\u7a3f\u751f\u6210\u5b8c\u6210` },
      subtitle: { tag: "plain_text", content: `\u6210\u529f ${successCount} \u7bc7${failCount > 0 ? `\uff0c\u5931\u8d25 ${failCount} \u7bc7` : ""}` },
      template: "green",
    },
    body: {
      direction: "vertical",
      padding: "12px 12px 12px 12px",
      elements: [
        {
          tag: "markdown",
          content: `${list}\n\n\u8bf7\u524d\u5f80\u516c\u4f17\u53f7\u540e\u53f0\u8349\u7a3f\u7bb1\u67e5\u770b\u521d\u7a3f\ud83d\udc47`,
        },
        {
          tag: "button",
          text: { tag: "plain_text", content: "\ud83d\udcdd \u524d\u5f80\u516c\u4f17\u53f7\u8349\u7a3f\u7bb1" },
          type: "primary",
          width: "default",
          size: "medium",
          behaviors: [
            {
              type: "open_url",
              default_url: "https://mp.weixin.qq.com",
            },
          ],
        },
      ],
    },
  };
  await sendCardToUser(openId, card);
}

/**
 * 调用Claude CLI生成文案
 */
async function generateArticle(topicTitle: string): Promise<string> {
  const prompt = `请阅读 ${SKILL_PATH}/SKILL.md 了解工作流，然后阅读 ${SKILL_PATH}/references/ 下的所有参考文件。

现在请为以下选题生成完整文案：

选题：${topicTitle}

要求：
1. 按照SKILL.md中"阶段四：全文撰写"的流程执行
2. 写作前加载合规清单，写作中实时遵守
3. 输出1500-2500字完整文案
4. 末尾附合规自查结果`;

  const proc = Bun.spawn(["claude", "-p", prompt], {
    stdout: "pipe",
    stderr: "pipe",
    env: { ...process.env, CLAUDE_NO_TELEMETRY: "1" },
  });

  const output = await new Response(proc.stdout).text();
  const exitCode = await proc.exited;

  if (exitCode !== 0) {
    const stderr = await new Response(proc.stderr).text();
    console.error(`[Claude] CLI错误: ${stderr}`);
    throw new Error(`Claude CLI执行失败: ${stderr.slice(0, 200)}`);
  }

  return output;
}

/**
 * 解析用户回复的选题编号
 * 支持格式："1 3 5"、"1,3,5"、"1、3、5"、"135"（单位数时）
 */
function parseTopicNumbers(text: string): number[] {
  // 去掉前后空格
  text = text.trim();

  // 尝试各种分隔符
  let nums: number[] = [];

  // 用逗号、顿号、空格分割
  const parts = text.split(/[,，、\s]+/).filter(Boolean);

  for (const part of parts) {
    const n = parseInt(part, 10);
    if (!isNaN(n) && n >= 1 && n <= currentTopics.length) {
      nums.push(n);
    }
  }

  // 如果没有分隔符，尝试逐字符解析（如"135"→[1,3,5]）
  if (nums.length === 0 && /^\d+$/.test(text) && text.length <= currentTopics.length) {
    for (const ch of text) {
      const n = parseInt(ch, 10);
      if (n >= 1 && n <= currentTopics.length) {
        nums.push(n);
      }
    }
  }

  // 去重
  return [...new Set(nums)];
}

/**
 * 处理选题选择并生成文案
 */
async function handleTopicSelection(chatId: string, openId: string, numbers: number[]) {
  if (isGenerating) {
    await sendText(chatId, "正在生成中，请等待当前任务完成后再提交新选题。");
    return;
  }

  const selectedTopics = numbers
    .map(n => currentTopics.find(t => t.index === n))
    .filter(Boolean) as Topic[];

  if (selectedTopics.length === 0) {
    await sendText(chatId, "未匹配到有效选题编号，请检查后重新输入。");
    return;
  }

  isGenerating = true;

  // 发送进度通知卡片
  await sendProgressCard(openId, selectedTopics);

  // 逐个生成，记录结果
  const results: { topic: Topic; success: boolean }[] = [];

  for (const topic of selectedTopics) {
    try {
      console.log(`[Generate] 开始: ${topic.title}`);

      const article = await generateArticle(topic.title);

      // 发送文案（分段发送避免超长）
      const chunks = splitText(article, 4000);
      for (let i = 0; i < chunks.length; i++) {
        const prefix = i === 0 ? `【第${topic.index}篇】${topic.title}\n${"=".repeat(30)}\n\n` : "";
        await sendText(chatId, prefix + chunks[i]);
      }

      console.log(`[Generate] 完成: ${topic.title}`);
      results.push({ topic, success: true });
    } catch (err) {
      console.error(`[Generate] 失败: ${topic.title}`, err);
      results.push({ topic, success: false });
    }
  }

  // 发送完成通知卡片
  await sendCompletionCard(openId, selectedTopics, results);
  isGenerating = false;
}

/**
 * 将长文本分段
 */
function splitText(text: string, maxLen: number): string[] {
  if (text.length <= maxLen) return [text];
  const chunks: string[] = [];
  let start = 0;
  while (start < text.length) {
    let end = Math.min(start + maxLen, text.length);
    // 尝试在换行处断开
    if (end < text.length) {
      const lastNewline = text.lastIndexOf("\n", end);
      if (lastNewline > start + maxLen * 0.5) {
        end = lastNewline + 1;
      }
    }
    chunks.push(text.slice(start, end));
    start = end;
  }
  return chunks;
}

// ============ WSClient 长连接 ============

console.log(`
╔══════════════════════════════════════════════════════╗
║  日生研NSKSD · 选题监听服务（长连接模式）               ║
║                                                      ║
║  不需要公网IP，不需要内网穿透                           ║
║  通过飞书SDK WebSocket长连接接收消息                    ║
╚══════════════════════════════════════════════════════╝
`);

const wsClient = new Lark.WSClient({
  appId: APP_ID,
  appSecret: APP_SECRET,
  loggerLevel: Lark.LoggerLevel.info,
});

wsClient.start({
  eventDispatcher: new Lark.EventDispatcher({}).register({
    // ============ 卡片回调：处理form提交 ============
    "card.action.trigger": async (data: any) => {
      try {
        const action = data?.event?.action;
        const openId = data?.event?.operator?.open_id;
        const actionValue = action?.value || {};

        console.log(`[CardAction] 收到卡片回调:`, JSON.stringify(data?.event, null, 2));

        // 检查是否是提交按钮的callback
        if (actionValue?.action === "submit_topics") {
          // callback模式下，checker状态在 data.event.action.form_value 或需要从卡片状态获取
          // 由于不用form容器，checker状态可能在 data.event.action 的其他字段
          // 先记录完整数据结构用于调试
          console.log(`[CardAction] 完整action:`, JSON.stringify(action, null, 2));

          // 尝试多种方式获取checker状态
          const formValue = action?.form_value || {};
          const checkerValues = action?.checked_value || {};

          const selectedNumbers: number[] = [];

          // 方式1: form_value
          for (const [key, value] of Object.entries(formValue)) {
            if (key.startsWith("topic_") && value === true) {
              const num = parseInt(key.replace("topic_", ""), 10);
              if (!isNaN(num)) selectedNumbers.push(num);
            }
          }

          // 方式2: checked_value
          if (selectedNumbers.length === 0) {
            for (const [key, value] of Object.entries(checkerValues)) {
              if (key.startsWith("topic_") && value === true) {
                const num = parseInt(key.replace("topic_", ""), 10);
                if (!isNaN(num)) selectedNumbers.push(num);
              }
            }
          }

          console.log(`[CardAction] 选中的选题: ${selectedNumbers.join(", ") || "(未检测到勾选)"}`);

          // 如果没检测到勾选，默认提示用回复编号的方式
          if (selectedNumbers.length === 0) {
            return {
              toast: { type: "info", content: "请在聊天框回复选题编号（如 1 3 5）来提交选题" }
            };
          }

          const chatId = "oc_593f103b3d1f80ca34b728de58a31ac1";

          // 异步处理写稿
          handleTopicSelection(chatId, openId, selectedNumbers).catch(err => {
            console.error("[CardAction] 处理失败:", err);
          });

          return {
            toast: {
              type: "success",
              content: `已提交 ${selectedNumbers.length} 个选题，正在生成文案...`
            }
          };
        }

        return {};
      } catch (err) {
        console.error("[CardAction] 处理卡片回调出错:", err);
        return { toast: { type: "error", content: "处理失败，请重试" } };
      }
    },
    // ============ 消息事件：处理文本回复 ============
    "im.message.receive_v1": async (data: any) => {
      try {
        const message = data.message;
        const chatId = message.chat_id;
        const senderId = data.sender?.sender_id?.open_id;
        const msgType = message.message_type;

        // 只处理文本消息
        if (msgType !== "text") return;

        const content = JSON.parse(message.content);
        const text = content.text?.trim();

        if (!text) return;

        console.log(`[Message] 收到消息: "${text}" from ${senderId}`);

        // 检查是否为选题编号
        const numbers = parseTopicNumbers(text);

        if (numbers.length > 0 && currentTopics.length > 0) {
          console.log(`[Message] 解析到选题编号: ${numbers.join(", ")}`);
          // 异步处理，避免3秒超时
          handleTopicSelection(chatId, senderId, numbers).catch(err => {
            console.error("[Handle] 处理失败:", err);
          });
        } else if (text === "选题列表" || text === "查看选题") {
          // 显示当前选题列表
          if (currentTopics.length === 0) {
            await sendText(chatId, "当前没有待选的选题。请先运行选题生成脚本。");
          } else {
            const list = currentTopics.map(t =>
              `${t.index}. [${t.grade}] ${t.title}（${t.score}分）`
            ).join("\n");
            await sendText(chatId, `当前选题列表（共${currentTopics.length}篇）：\n\n${list}\n\n回复编号即可选择，如"1 3 5"表示选择第1、3、5篇`);
          }
        } else if (text === "帮助" || text === "help") {
          await sendText(chatId, [
            "日生研NSKSD · 选题助手",
            "═══════════════════",
            "",
            "回复编号选择选题：",
            '  "1 3 5" → 选择第1、3、5篇',
            '  "1,3,5" → 同上',
            "",
            "其他命令：",
            '  "选题列表" → 查看当前选题',
            '  "帮助" → 显示本帮助',
          ].join("\n"));
        }
        // 其他消息忽略
      } catch (err) {
        console.error("[Message] 处理消息时出错:", err);
      }
    },
  }),
});

console.log("[WSClient] 正在连接飞书长连接服务...");

// ============ 同时启动一个本地HTTP端口用于注册选题和健康检查 ============

const httpServer = Bun.serve({
  port: Number(process.env.PORT) || 9800,
  async fetch(req) {
    const url = new URL(req.url);

    if (url.pathname === "/health") {
      return Response.json({
        status: "ok",
        mode: "websocket",
        topics: currentTopics.length,
        generating: isGenerating,
      });
    }

    if (url.pathname === "/register-topics" && req.method === "POST") {
      const body = await req.json() as any;
      const topics = (body.topics || []).map((t: any, i: number) => ({
        ...t,
        index: i + 1,
      }));
      registerTopics(topics);
      return Response.json({ code: 0, registered: currentTopics.length });
    }

    if (url.pathname === "/status") {
      return Response.json({
        topics: currentTopics,
        generating: isGenerating,
      });
    }

    return new Response("NSKSD Topic Listener (WebSocket mode)");
  },
});

console.log(`[HTTP] 本地管理端口: http://localhost:${httpServer.port}`);
