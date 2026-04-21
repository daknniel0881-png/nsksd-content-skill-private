# 数据来源与验证规范 · v9.3

> **适用范围**：日生研 NSKSD 内容生产全流程（选题 / 大纲 / 撰稿 / 合规）
> **客户行业**：健康品（纳豆激酶） — **数据造假是要出人命的**
> **强制等级**：article-writer、title-outliner、topic-scout 三方必读

---

## 🔴 诚实原则（最高优先级）

> 你**可以**说：「这项数据我没找到权威来源，建议写成'行业内流传'或删掉」。
>
> 你**绝对不能**：
> - 编造数据（受试者人数、P 值、改善率、百分比等）
> - 编造文献（期刊名、论文标题、发表日期）
> - 编造机构名称（把"某三甲医院"伪装成"浙大二院"）
> - 编造 URL（拼凑看起来像那么回事的链接）
> - 编造研究团队姓名或职务
>
> **一旦被曲率/客户抽查到编造，这个 skill 直接下架。**
>
> 不确定就问，问不到就降级写法，降级写法不够就重新选题。**宁可不写，不可乱写。**

---

## 一、数据引用格式（硬标准）

### ✅ 标准格式

```
数据内容（来源：<权威机构名称> <文章/研究标题>，<URL>，<发表日期>）
```

### 示例对照

| ❌ 残次 | ✅ 合格 |
|--------|--------|
| 「降低 65% 风险」 | 「视觉空间功能衰退风险降低约 65%（来源：《卒中与脑血管疾病杂志》2026-01 在线发表，https://doi.org/xxx，浙大楼敏教授团队 120 人双盲 RCT）」 |
| 「EFSA 认证可长期服用」 | 「35 岁以上人群可长期服用（来源：EFSA Journal 2017;15(6):4818，https://efsa.onlinelibrary.wiley.com/doi/10.2903/j.efsa.2017.4818）」 |
| 「中国 1.2 亿人无症状性颈动脉狭窄」 | 「约 1.2 亿人（来源：《中国脑血管病一级预防指南 2019》，中华医学会神经病学分会，https://rs.yiigle.com/xxx）」 |

---

## 二、来源权威度分级（硬排序）

### 一级权威（医学/科学事实可直接引用）

- **国际机构**：WHO、CDC、FDA、EFSA、NIH、PubMed Central
- **中国官方**：NMPA（国家药监局）、国家卫健委、中国营养学会、中华医学会
- **顶级期刊 & 综述**：Nature、Science、NEJM、Lancet、JAMA、BMJ、Cochrane 系统综述
- **专业学术期刊**：Frontiers 系列、《卒中与脑血管疾病杂志》、《中华心血管病杂志》等中英文核心期刊

### 二级权威（社会事实、行业背景可引用）

- 人民日报、新华社、央视、光明网（官方转载学术成果时）
- 健康时报、丁香园、医学界、健康界（专业记者采写的医学新闻）

### 三级权威（**仅限不涉及健康功效的行业数据**）

- 品牌官网（日生研、海外原研方）— 只用于产品规格 / FU 值 / 公司信息
- 行业协会白皮书 — 只用于市场规模、渠道数据
- 企业新闻稿 — 只用于会议议程、发布活动

### ❌ 禁用来源

- 小红书 / 抖音 / 视频号帖子（任何个人博主内容）
- 非署名自媒体、公众号匿名文章
- 百度文库、道客巴巴、知乎回答
- 广告软文、KOL 种草贴
- 企业自夸性产品页（涉及功效宣传时）

---

## 三、URL 验证流程（article-writer 撰稿前必跑）

### Step 1 · 逐个 fetch

写稿完成后，对 frontmatter `sources_checked` 里每个 URL 跑一次 WebFetch：

```python
for item in sources_checked:
    status = webfetch(item["url"])
    if status != 200:
        # 必须换源或删除该数据点
        flag_for_rewrite(item)
```

### Step 2 · 失败处理

| 失败类型 | 处理 |
|---------|------|
| 404 Not Found | **必须**换另一个同级或更高级权威源；换不到就删掉该数据点 |
| 域名死链 / DNS 失败 | 同上 |
| robots 拒绝 / 反爬 | 尝试镜像（DOI、PubMed PMID）；仍失败则标注「原文需通过 DOI 访问」并保留 DOI |
| 跳转到首页 / 页面已更新 | 用 archive.org 的 Wayback Machine 版本，附 snapshot URL |
| 被墙（海外源） | 标注「原文 URL 海外可访问」，并提供中文权威媒体转载作为二级印证 |

### Step 3 · 记录到 frontmatter

每条通过的 URL 必须写入 `sources_checked`：

```yaml
sources_checked:
  - url: "https://..."
    verified_at: "2026-04-21T10:23:00+08:00"
    http_status: 200
    authority_level: 1
    claim: "该 URL 直接支持的具体陈述（一句话）"
```

**没填 sources_checked = 不合格，不得落盘。**

---

## 四、交叉验证（孤证不立）

### 硬规则

- 每个**核心数据**（涉及健康功效、临床效果、数字百分比）至少要 **2 个独立来源**
- 其中至少 1 个是**一级权威**
- 两个来源不能是同一篇论文的不同转载

### 什么叫"核心数据"

- 「降低 65% 风险」← 核心
- 「EFSA 认证 35 岁以上可长期服用」← 核心
- 「每克含 20000 FU」← 次要（品牌规格，三级权威可接受）
- 「2026 年 1 月发表」← 次要（时间事实）

### 孤证处理

- 能找到第二来源 → 补上
- 找不到 → 降级写法（"有研究显示……"改成"日生研团队内部数据显示……"并明确标注）
- 实在是核心数据还找不到孤证以外的来源 → **删掉这一条，重写段落**

---

## 五、frontmatter 完整示例（合格样板）

```yaml
---
session_id: 2026-04-21-ffc-v4
topic_index: 2
title: "全球首份临床报告：65% 来自浙大 120 人的双盲试验"
word_count: 1980
compliance: "🟢"
style_check:
  ai_words_hit: 0
  first_person_hit: 0
  quyu_signature_hit: 0
  dashes_count: 1
  concrete_numbers: 11
sources_checked:
  - url: "https://doi.org/10.1016/j.jstrokecerebrovasdis.2026.01.xxx"
    verified_at: "2026-04-21T10:23:00+08:00"
    http_status: 200
    authority_level: 1
    claim: "浙大 120 人双盲 RCT 视觉空间功能衰退风险降低 65%（P=0.024）"
  - url: "https://www.gmw.cn/xxx/2026-01-12/xxx.htm"
    verified_at: "2026-04-21T10:24:15+08:00"
    http_status: 200
    authority_level: 2
    claim: "光明网对浙大研究的权威媒体转载（交叉验证）"
  - url: "https://efsa.onlinelibrary.wiley.com/doi/10.2903/j.efsa.2017.4818"
    verified_at: "2026-04-21T10:25:30+08:00"
    http_status: 200
    authority_level: 1
    claim: "EFSA 2017 对纳豆激酶 35+ 人群长期服用安全性评估"
  - url: "https://rs.yiigle.com/CN113046201910/1234567.htm"
    verified_at: "2026-04-21T10:26:45+08:00"
    http_status: 200
    authority_level: 1
    claim: "《中国脑血管病一级预防指南 2019》1.2 亿人基数"
cross_validation:
  core_claims_with_2plus_sources: 3
  arbitrary_isolated_claims: 0
written_at: "2026-04-21T10:30:00+08:00"
---
```

---

## 六、出事边界

- 写了没带 URL 的健康功效陈述 → 🔴 退回重写
- URL 存在但验证 404 → 🔴 退回重写
- 孤证硬写 → 🔴 退回重写
- 编造任何一条（机构/人物/数据/链接） → ❌ skill 下架 + 曲率约谈

**健康行业的内容，宁可慢一天，不可错一字。**
