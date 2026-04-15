#!/usr/bin/env bun
/**
 * 发送选题卡片到飞书 + 向监听服务注册选题
 *
 * 卡片为纯展示模式（V1兼容），用户通过回复数字编号选择选题，
 * 监听服务（WSClient长连接）自动接收并触发文案生成。
 *
 * 用法：bun run send-topic-card.ts [选题文件路径]
 */

const LARK_APP_ID = process.env.LARK_APP_ID || "";
const LARK_APP_SECRET = process.env.LARK_APP_SECRET || "";
const TARGET_OPEN_ID = process.env.TARGET_OPEN_ID || "";
const CALLBACK_SERVER = process.env.CALLBACK_SERVER || "http://localhost:9800";

const topicsFile = process.argv[2] || "/tmp/nsksd-topics-result.md";

interface Topic {
  id: string;
  title: string;
  grade: string;
  score: string;
  line: string;
  compliance: string;
}

/**
 * 从选题结果文件中解析选题列表
 */
function parseTopics(content: string): Topic[] {
  const topics: Topic[] = [];
  const lines = content.split("\n");
  let currentTopic: any = null;
  let topicIndex = 0;

  for (const line of lines) {
    const titleMatch = line.match(/\*\*选题(\d+)[：:]\s*(.+?)\*\*/);
    if (titleMatch) {
      topicIndex++;
      currentTopic = {
        id: `topic_${topicIndex}`,
        title: titleMatch[2].trim(),
        grade: "",
        score: "",
        line: "",
        compliance: "",
      };
      topics.push(currentTopic);
      continue;
    }
    if (!currentTopic) continue;

    const lineMatch = line.match(/内容线[：:]\s*(.+)/);
    if (lineMatch) currentTopic.line = lineMatch[1].trim();

    const gradeMatch = line.match(/等级[：:]\s*([SAB])/);
    if (gradeMatch) currentTopic.grade = gradeMatch[1];

    const scoreMatch = line.match(/总分(\d+)/);
    if (scoreMatch && !currentTopic.score) currentTopic.score = scoreMatch[1];

    const complianceMatch = line.match(/合规分级[：:]\s*(🟢|🟡|🔴)/);
    if (complianceMatch) currentTopic.compliance = complianceMatch[1];
  }

  return topics;
}

/**
 * 构建V1卡片（纯展示，最大兼容性）
 */
function buildCard(topics: Topic[]) {
  const gradeEmoji: Record<string, string> = { S: "🏆", A: "⭐", B: "📌" };

  // 按等级分组
  const sTopics = topics.filter(t => t.grade === "S");
  const aTopics = topics.filter(t => t.grade === "A");
  const bTopics = topics.filter(t => t.grade === "B");

  const formatGroup = (grade: string, items: Topic[], startIndex: number) => {
    if (items.length === 0) return "";
    const emoji = gradeEmoji[grade];
    const lines = items.map((t, i) => {
      const idx = startIndex + i;
      return `**${idx}.** ${t.title}（${t.score}分）${t.compliance}`;
    });
    return `${emoji} **${grade}级选题**\n${lines.join("\n")}`;
  };

  let mdContent = "";
  let idx = 1;

  if (sTopics.length > 0) {
    mdContent += formatGroup("S", sTopics, idx);
    idx += sTopics.length;
  }
  if (aTopics.length > 0) {
    mdContent += "\n\n" + formatGroup("A", aTopics, idx);
    idx += aTopics.length;
  }
  if (bTopics.length > 0) {
    mdContent += "\n\n" + formatGroup("B", bTopics, idx);
  }

  const dateStr = new Date().toLocaleDateString("zh-CN", { month: "long", day: "numeric" });

  // V1卡片结构
  const card = {
    config: { wide_screen_mode: true },
    header: {
      template: "blue",
      title: {
        tag: "plain_text",
        content: `日生研NSKSD · ${dateStr}选题（共${topics.length}篇）`,
      },
    },
    elements: [
      {
        tag: "div",
        text: {
          tag: "lark_md",
          content: mdContent,
        },
      },
      { tag: "hr" },
      {
        tag: "div",
        text: {
          tag: "lark_md",
          content: '💡 **回复数字编号即可选择选题**\n例如回复 "1 3 5" 表示选择第1、3、5篇\n回复后将自动开始生成文案',
        },
      },
    ],
  };

  return card;
}

/**
 * 获取飞书token
 */
async function getTenantToken(): Promise<string> {
  const resp = await fetch("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ app_id: LARK_APP_ID, app_secret: LARK_APP_SECRET }),
  });
  const data = (await resp.json()) as any;
  if (!data.tenant_access_token) {
    throw new Error(`获取token失败: ${JSON.stringify(data)}`);
  }
  return data.tenant_access_token;
}

/**
 * 发送卡片
 */
async function sendCard(token: string, openId: string, card: any) {
  const resp = await fetch("https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      receive_id: openId,
      msg_type: "interactive",
      content: JSON.stringify(card),
    }),
  });
  return (await resp.json()) as any;
}

/**
 * 向监听服务注册选题
 */
async function registerTopics(topics: Topic[]) {
  try {
    const resp = await fetch(`${CALLBACK_SERVER}/register-topics`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topics: topics.map((t, i) => ({
          id: t.id,
          title: t.title,
          grade: t.grade,
          line: t.line,
          score: t.score,
          compliance: t.compliance,
          index: i + 1,
        })),
      }),
    });
    const data = (await resp.json()) as any;
    console.log(`✅ 已向监听服务注册 ${data.registered} 个选题`);
  } catch (err) {
    console.warn(`⚠️ 监听服务未启动: ${err}`);
    console.warn("   请先启动监听服务: cd server && bun run index.ts");
  }
}

// ============ Main ============

async function main() {
  console.log(`📄 读取选题文件: ${topicsFile}`);
  const content = await Bun.file(topicsFile).text();

  const topics = parseTopics(content);
  if (topics.length === 0) {
    console.error("❌ 未解析到任何选题");
    process.exit(1);
  }

  console.log(`✅ 解析到 ${topics.length} 个选题：`);
  topics.forEach((t, i) => console.log(`   ${i + 1}: [${t.grade}] ${t.title} (${t.score}分) ${t.compliance}`));

  // 构建V1卡片
  const card = buildCard(topics);
  console.log(`\n🃏 卡片已构建（V1兼容模式）`);

  // 注册选题到监听服务
  await registerTopics(topics);

  // 发送卡片
  console.log(`\n📤 发送卡片到飞书...`);
  const token = await getTenantToken();
  const result = await sendCard(token, TARGET_OPEN_ID, card);

  if (result.code === 0) {
    console.log(`✅ 卡片发送成功！message_id: ${result.data?.message_id}`);
    console.log(`\n📱 用户在飞书中回复数字编号即可触发文案生成`);
  } else {
    console.error(`❌ 发送失败:`, JSON.stringify(result, null, 2));
  }
}

main().catch(err => {
  console.error("❌ 执行失败:", err);
  process.exit(1);
});
