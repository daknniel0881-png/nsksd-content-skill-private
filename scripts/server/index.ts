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

  // 发送确认
  const list = selectedTopics.map(t => `${t.index}. ${t.title}`).join("\n");
  await sendText(chatId,
    `已收到！共选择 ${selectedTopics.length} 个选题：\n${list}\n\n正在为您生成文案，预计每篇2-5分钟...`
  );

  // 逐个生成
  for (const topic of selectedTopics) {
    try {
      console.log(`[Generate] 开始: ${topic.title}`);
      await sendText(chatId, `正在生成第 ${topic.index} 篇：${topic.title}...`);

      const article = await generateArticle(topic.title);

      // 发送文案（分段发送避免超长）
      const chunks = splitText(article, 4000);
      for (let i = 0; i < chunks.length; i++) {
        const prefix = i === 0 ? `【第${topic.index}篇】${topic.title}\n${"=".repeat(30)}\n\n` : "";
        await sendText(chatId, prefix + chunks[i]);
      }

      console.log(`[Generate] 完成: ${topic.title}`);
    } catch (err) {
      console.error(`[Generate] 失败: ${topic.title}`, err);
      await sendText(chatId, `第${topic.index}篇生成失败：${err}\n请手动执行：/nsksd 文案 ${topic.title}`);
    }
  }

  await sendText(chatId, `全部文案生成完毕！共 ${selectedTopics.length} 篇。`);
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
