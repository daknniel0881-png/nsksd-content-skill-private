# Playbook：公众号推送

> 场景：将排版好的 HTML 文章推送到微信公众号草稿箱，待人工审核发布。

---

## 场景说明

本 Skill 的公众号推送由 `scripts/nsksd_publish.py` 完成。它读取配置中的微信凭证，上传封面图，创建草稿，返回草稿链接。

---

## 步骤

### 1. 确认凭证

```bash
python3 scripts/setup_cli.py
# 查看脱敏状态表，确认 wechat.app_id 和 wechat.app_secret 已填写
```

凭证来源：`~/.nsksd-content/config.json`，字段：
```json
{
  "wechat": {
    "app_id": "wx...",
    "app_secret": "...",
    "author": ""
  }
}
```

### 2. 准备文件

| 文件 | 说明 |
|------|------|
| `$HTML_FILE` | 排版后的 HTML，由 `nsksd_publish.py --format` 生成 |
| `$COVER_FILE` | 封面图，JPG/PNG，建议 900x500 |
| `$ARTICLE_TITLE` | 文章标题，不超过 64 字 |

### 3. 执行推送

```bash
python3 scripts/nsksd_publish.py \
  --html /tmp/article.html \
  --cover /tmp/cover.jpg \
  --title "文章标题" \
  --session-id "session-xxx"
```

### 4. 检查退出码

| 退出码 | 含义 | 处理 |
|--------|------|------|
| 0 | 推送成功 | 草稿箱等待发布 |
| 3 | 凭证缺失 | 已自动走飞书云文档保底 |
| 4 | 推送失败 | 已自动走飞书云文档保底 |
| 其他 | 未知异常 | 查看日志 |

---

## 参数说明

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `--html` | 是 | - | HTML 文件路径 |
| `--cover` | 否 | - | 封面图路径，无则不上传封面 |
| `--title` | 是 | - | 文章标题 |
| `--session-id` | 否 | 随机生成 | 用于日志追踪 |
| `--mock` | 否 | False | Mock 模式，不实际推送 |

---

## 常见错误

### 403 Forbidden

**原因**：app_id 或 app_secret 错误，或 IP 不在白名单。

**处理：**
1. 登录微信公众平台 → 开发 → 基本配置，确认 AppID 和 AppSecret
2. 如果用服务器推送，需要将服务器 IP 加入白名单（开发 → 基本配置 → IP 白名单）
3. 本地推送一般不受 IP 限制

### 40164 Invalid IP

**原因**：服务器 IP 不在微信白名单。

**处理**：将当前机器出口 IP 加入公众号后台白名单，或改用本地运行。

### author 字段为空

**默认行为**：author 为空字符串时，微信显示默认作者。这是正常的，不影响推送。

如果需要设置作者名，在 `~/.nsksd-content/config.json` 里：
```json
{
  "wechat": {
    "author": "日生研官方"
  }
}
```

### 图片 Markdown 转 HTML 后宽度固定

**问题**：有些排版工具会把 `![](img.jpg)` 转成 `<img width="750" ...>`，微信端显示异常。

**解决**：nsksd_publish.py 内置后处理，强制将所有 img 的 width 属性改为 `auto`：
```python
html = re.sub(r'<img([^>]*)width="[^"]*"', r'<img\1width="auto"', html)
```

如果手动处理 HTML，运行：
```bash
python3 -c "
import re, sys
html = open(sys.argv[1]).read()
html = re.sub(r'<img([^>]*)width=\"[^\"]*\"', r'<img\1width=\"auto\"', html)
open(sys.argv[1], 'w').write(html)
" article.html
```

### Mock 模式验证

不想真正推送时，加 `--mock` 参数：
```bash
python3 scripts/nsksd_publish.py --html test.html --title "测试" --mock
# 输出：[MOCK] 公众号推送跳过，凭证校验通过
```

---

## 验证方法

推送成功后：
1. 登录微信公众平台 → 内容 → 草稿箱，确认文章出现
2. 确认标题、封面、正文格式正确
3. 不要直接发布，让运营人员审核后再发

---

## 回查兜底

公众号推送失败（exit code 3 或 4）时，自动走飞书云文档保底。

保底流程见：[feishu-doc.md](./feishu-doc.md)
