#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "pillow>=10.0.0",
# ]
# ///
"""日生研NSKSD · 文章配图生成工具

基于 Google Gemini 3 Pro Image (Nano Banana Pro) API 为公众号文章生成配图。

用法:
    # 生成配图（默认2K分辨率，适合公众号）
    python3 generate_image.py --prompt "图片描述" --filename "output.png"

    # 指定分辨率
    python3 generate_image.py --prompt "图片描述" --filename "output.png" --resolution 4K

    # 编辑已有图片
    python3 generate_image.py --prompt "编辑说明" --filename "output.png" --input-image "input.png"

    # 使用 uv 运行（自动管理依赖）
    uv run generate_image.py --prompt "图片描述" --filename "output.png"

环境变量:
    GEMINI_API_KEY  — Google Gemini API 密钥（必须）

配图场景建议:
    - 科学信任类文章：数据可视化风格，清晰简洁的信息图
    - 品牌故事类文章：品牌调性配图，温暖专业
    - 健康科普类文章：科普插画风格，易懂亲切
    - 招商转化类文章：商业场景，专业有力
"""

import argparse
import os
import sys
from pathlib import Path


# ── 文章配图风格提示词模板 ──────────────────────────────────────────────

STYLE_TEMPLATES = {
    "science": (
        "Style: clean data visualization infographic. "
        "Colors: mint green and white palette. "
        "Layout: Bento Box grid layout with 5-7 sections. "
        "Background: pure off-white or light parchment. "
        "Text: Chinese characters, clear sans-serif font. "
        "Flat design with minimal shadows. "
        "Professional, trustworthy, scientific feel."
    ),
    "brand": (
        "Style: warm professional brand illustration. "
        "Colors: coffee brown and cream palette, warm tones. "
        "Layout: balanced composition with breathing space. "
        "Background: soft cream or warm beige. "
        "Hand-drawn elements with clean lines. "
        "Text: Chinese characters. "
        "Approachable, trustworthy, established brand feel."
    ),
    "health": (
        "Style: friendly health science illustration. "
        "Colors: fresh green and light blue palette. "
        "Layout: clear visual hierarchy, easy to understand. "
        "Background: clean white with subtle texture. "
        "Cartoon-like but professional illustrations. "
        "Text: Chinese characters. "
        "Accessible, educational, caring feel."
    ),
    "business": (
        "Style: professional business infographic. "
        "Colors: sunset amber and dark navy palette. "
        "Layout: structured grid with bold sections. "
        "Background: light warm tone. "
        "Modern flat design with strong visual anchors. "
        "Text: Chinese characters. "
        "Confident, opportunity-focused, actionable feel."
    ),
    "cover": (
        "Style: WeChat article cover image, 900x383 aspect ratio. "
        "Colors: harmonious professional palette. "
        "Layout: centered key visual with text overlay area on left or right. "
        "Background: gradient or subtle texture. "
        "Text: Chinese characters, large readable title. "
        "Eye-catching but not cluttered. "
        "Professional magazine cover feel."
    ),
}

# 内容线 → 配图风格映射
CONTENT_LINE_MAP = {
    "科学信任": "science",
    "健康科普": "health",
    "品牌故事": "brand",
    "招商转化": "business",
}


def get_api_key(provided_key: str | None) -> str | None:
    """Get API key from argument first, then environment."""
    if provided_key:
        return provided_key
    return os.environ.get("GEMINI_API_KEY")


def build_prompt(user_prompt: str, style: str | None = None) -> str:
    """组合用户描述和风格模板，生成最终 prompt。"""
    base = user_prompt.strip()

    if style and style in STYLE_TEMPLATES:
        return f"{base}. {STYLE_TEMPLATES[style]}"

    # 自动检测风格关键词
    for keyword, style_key in CONTENT_LINE_MAP.items():
        if keyword in base:
            return f"{base}. {STYLE_TEMPLATES[style_key]}"

    # 默认使用科普风格
    return base


def main():
    parser = argparse.ArgumentParser(
        description="日生研NSKSD · 文章配图生成工具 (Gemini 3 Pro Image)"
    )
    parser.add_argument(
        "--prompt", "-p",
        required=True,
        help="图片描述（中英文均可）"
    )
    parser.add_argument(
        "--filename", "-f",
        required=True,
        help="输出文件名（如 cover.png, illustration-1.png）"
    )
    parser.add_argument(
        "--input-image", "-i",
        help="输入图片路径（用于编辑已有图片）"
    )
    parser.add_argument(
        "--resolution", "-r",
        choices=["1K", "2K", "4K"],
        default="2K",
        help="输出分辨率：1K, 2K（默认，适合公众号）, 4K"
    )
    parser.add_argument(
        "--style", "-s",
        choices=list(STYLE_TEMPLATES.keys()),
        default=None,
        help="配图风格：science/brand/health/business/cover"
    )
    parser.add_argument(
        "--content-line",
        choices=list(CONTENT_LINE_MAP.keys()),
        default=None,
        help="内容线（自动映射配图风格）：科学信任/健康科普/品牌故事/招商转化"
    )
    parser.add_argument(
        "--api-key", "-k",
        help="Gemini API key（覆盖环境变量 GEMINI_API_KEY）"
    )

    args = parser.parse_args()

    # 获取 API key
    api_key = get_api_key(args.api_key)
    if not api_key:
        print("错误：未提供 API 密钥。", file=sys.stderr)
        print("请设置环境变量 GEMINI_API_KEY 或使用 --api-key 参数。", file=sys.stderr)
        sys.exit(1)

    # 导入依赖（检查完 API key 再导入，避免无 key 时还要等慢导入）
    from google import genai
    from google.genai import types
    from PIL import Image as PILImage

    # 初始化客户端
    client = genai.Client(api_key=api_key)

    # 输出路径
    output_path = Path(args.filename)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 确定风格
    style = args.style
    if not style and args.content_line:
        style = CONTENT_LINE_MAP.get(args.content_line)

    # 构建 prompt
    final_prompt = build_prompt(args.prompt, style)
    print(f"配图风格: {style or '自动'}")
    print(f"最终 prompt: {final_prompt[:100]}...")

    # 加载输入图片（如果是编辑模式）
    input_image = None
    output_resolution = args.resolution
    if args.input_image:
        try:
            input_image = PILImage.open(args.input_image)
            print(f"已加载输入图片: {args.input_image}")

            # 根据输入图片尺寸自动调整输出分辨率
            if args.resolution == "2K":  # 默认值时自动检测
                width, height = input_image.size
                max_dim = max(width, height)
                if max_dim >= 3000:
                    output_resolution = "4K"
                elif max_dim >= 1500:
                    output_resolution = "2K"
                else:
                    output_resolution = "1K"
                print(f"自动检测分辨率: {output_resolution}（输入 {width}x{height}）")
        except Exception as e:
            print(f"错误：加载输入图片失败: {e}", file=sys.stderr)
            sys.exit(1)

    # 构建请求内容
    if input_image:
        contents = [input_image, final_prompt]
        print(f"编辑图片中，分辨率 {output_resolution}...")
    else:
        contents = final_prompt
        print(f"生成图片中，分辨率 {output_resolution}...")

    try:
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
                image_config=types.ImageConfig(
                    image_size=output_resolution
                )
            )
        )

        # 处理响应并保存为 PNG
        image_saved = False
        for part in response.parts:
            if part.text is not None:
                print(f"模型回复: {part.text}")
            elif part.inline_data is not None:
                from io import BytesIO

                image_data = part.inline_data.data
                if isinstance(image_data, str):
                    import base64
                    image_data = base64.b64decode(image_data)

                image = PILImage.open(BytesIO(image_data))

                # 确保 RGB 模式
                if image.mode == 'RGBA':
                    rgb_image = PILImage.new('RGB', image.size, (255, 255, 255))
                    rgb_image.paste(image, mask=image.split()[3])
                    rgb_image.save(str(output_path), 'PNG')
                elif image.mode == 'RGB':
                    image.save(str(output_path), 'PNG')
                else:
                    image.convert('RGB').save(str(output_path), 'PNG')
                image_saved = True

        if image_saved:
            full_path = output_path.resolve()
            print(f"\n图片已保存: {full_path}")
            print(f"尺寸: {image.size[0]}x{image.size[1]}")
        else:
            print("错误：API 未返回图片。", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"错误：生成图片失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
