# Playbook：公众号图片处理（V10.2 硬规矩）

> **坑位 & 真相**：本地图路径原样推到微信草稿箱 = 100% 裂图。本 playbook 解释正确方式。

---

## 核心真相

微信公众号草稿箱的 `content` 字段里，**所有 `<img src="...">` 必须是 `mmbiz.qpic.cn` 域名**。

| 来源 | 草稿箱表现 |
|------|----------|
| `<img src="./images/cover.png">` | ❌ 裂图（本地路径微信服务器访问不到） |
| `<img src="https://example.com/x.jpg">` | ❌ 裂图（外链被微信拦截）|
| `<img src="https://mmbiz.qpic.cn/...">` | ✅ 正常显示 |

所以每张图必须先调 **`/cgi-bin/media/uploadimg`** 上传到微信服务器，拿到 `mmbiz.qpic.cn` URL，替换回 HTML 再推草稿。

---

## 完整调用链（V10.2）

```
┌──────────────────────────────────────────────────────────┐
│ 1. 获取 access_token                                       │
│    GET /cgi-bin/token?grant_type=client_credential        │
│        &appid=xxx&secret=xxx                              │
│    → {"access_token":"..."}                               │
└─────────────────────┬────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│ 2. 上传封面（永久素材，拿到 thumb_media_id）                   │
│    POST /cgi-bin/material/add_material?                   │
│         access_token=...&type=image                       │
│    multipart/form-data: media=@cover-wechat.png           │
│    → {"media_id":"xxx","url":"..."}                       │
│    👆 这个 media_id 用在 draft/add 的 thumb_media_id 字段   │
└─────────────────────┬────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│ 3. 上传内文每张图（临时 CDN，拿到 mmbiz.qpic.cn URL）          │
│    POST /cgi-bin/media/uploadimg?access_token=...         │
│    multipart/form-data: media=@figure-1.png               │
│    → {"url":"https://mmbiz.qpic.cn/mmbiz_png/xxx/0"}      │
│    👆 这个 url 替换 HTML 里的 <img src>                    │
└─────────────────────┬────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│ 4. 替换 HTML 里所有 <img src>                               │
│    注意支持双引号 / 单引号 / 无引号 三种写法                    │
│    data: / http(s) / 本地相对路径 都要覆盖                    │
│    ./images/x.png 要先去 ./ 前缀再拼 article_dir            │
└─────────────────────┬────────────────────────────────────┘
                      ↓
┌──────────────────────────────────────────────────────────┐
│ 5. 推草稿箱                                                │
│    POST /cgi-bin/draft/add?access_token=...               │
│    Content-Type: application/json                         │
│    {                                                      │
│      "articles":[{                                        │
│        "title":"...",                                     │
│        "author":"...",                                    │
│        "content":"<html with mmbiz.qpic.cn imgs>",        │
│        "thumb_media_id":"<步骤 2 的 media_id>"             │
│      }]                                                   │
│    }                                                      │
│    → {"media_id":"<draft_media_id>"}                      │
└──────────────────────────────────────────────────────────┘
```

---

## 关键参数速查

| 接口 | method | Content-Type | 关键参数 |
|------|--------|--------------|----------|
| `/cgi-bin/token` | GET | - | `grant_type=client_credential` |
| `/cgi-bin/material/add_material` | POST | `multipart/form-data` | `type=image`, `media` 文件字段 |
| `/cgi-bin/media/uploadimg` | POST | `multipart/form-data` | `media` 文件字段 |
| `/cgi-bin/draft/add` | POST | `application/json` | `articles[0].thumb_media_id` 必填 |

**MIME type 映射**（upload 时 files 元组第 3 位）：

```python
{".jpg": "image/jpeg", ".jpeg": "image/jpeg",
 ".png": "image/png", ".gif": "image/gif"}
```

**封面图尺寸**（参考 V10.1 硬门控）：`cover-wechat.png` 必须 900×383，否则 `image_size_check.py` 退回。

---

## V10.2 代码修复

`scripts/lib/wechat_publish_core.py::replace_all_images` 原来只匹配 `src="..."` 双引号。V10.2 扩成三种：

```python
html = re.sub(r'src="([^"]+)"', _repl_double, html)
html = re.sub(r"src='([^']+)'", _repl_single, html)
html = re.sub(r'src=([^\s"\'>]+)', _repl_bare, html)
```

同时所有失败场景打 stderr：

```
[wechat-img] FAIL 本地图片找不到：src=./images/figure-1.png article_dir=/tmp/nsksd-xxx
[wechat-img] FAIL 外网图下载/上传失败：https://...
```

---

## 调试清单（图片裂开时走一遍）

1. **看 stderr 日志**：`grep wechat-img /tmp/nsksd-trigger-watcher.log`
2. **检查 article_dir 结构**：
   ```
   /tmp/nsksd-<session_id>/
   ├── article.html                    ← <img src> 必须能解析到下面文件
   ├── images/
   │   ├── cover-wechat.png            ← 900×383 公众号封面
   │   ├── cover-xhs.png               ← 1242×1660（可选）
   │   ├── figure-1.png
   │   ├── figure-2.png
   │   └── figure-3.png                ← 至少 3 张
   ```
3. **手动校验一张**：
   ```bash
   TOKEN=$(curl -s "https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=$APPID&secret=$SECRET" | jq -r .access_token)
   curl -F "media=@images/figure-1.png" \
     "https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token=$TOKEN"
   # 期望返回 {"url":"https://mmbiz.qpic.cn/..."}
   ```
4. **HTML 正则检查**：确认 `<img src` 里没有本地路径残留
   ```bash
   grep -oE '<img[^>]*src=[^>]*>' article.html | grep -v mmbiz.qpic.cn
   # 期望：无输出
   ```

---

## 常见 errcode

| errcode | errmsg | 处理 |
|---------|--------|------|
| 40001 | access_token 过期 | 重新取 token（有效期 7200s）|
| 40164 | invalid ip | IP 不在白名单，走本地或把出口 IP 加白名单 |
| 45009 | api freq out of limit | 单接口上限（uploadimg 每日 100 次）|
| 45166 | content too long | content 字段上限 20000 汉字，图片太多会超 |

---

## 红线

- ❌ 本地路径直接塞进 content → 100% 裂图
- ❌ 外链 URL 塞进 content → 100% 裂图（微信服务器不代理外链）
- ❌ 忘了上传封面就推 draft → errcode 45009（thumb_media_id invalid）
- ✅ 先 uploadimg 拿 mmbiz URL → 替换 → 再 draft/add
