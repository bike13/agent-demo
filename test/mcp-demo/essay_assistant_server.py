from fastmcp import FastMCP
import os
import logging
from typing import List, Optional, Dict, Any
import easyocr
from openai import OpenAI
from dotenv import load_dotenv
import requests

# 加载环境变量
load_dotenv()

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8"
)

# 创建MCP服务器
mcp = FastMCP(
    name="essay_assistant_server",
    dependencies=["requests", "easyocr", "openai", "python-dotenv", "pillow"],
    host="127.0.0.1",
    port=9002
)

# 初始化OpenAI客户端
def get_openai_client():
    """获取OpenAI客户端实例"""
    api_url = os.environ.get('BASE_URL')
    api_key = os.environ.get('API_KEY')
    
    if not api_url or not api_key:
        raise ValueError("请配置环境变量 BASE_URL 和 API_KEY")
    
    return OpenAI(
        api_key=api_key,
        base_url=api_url,
    )

@mcp.tool(description="OCR识别图片文字并生成英语作文提纲")
def ocr_and_generate_outline(image_path: str, grade: str, difficulty: Optional[str] = None) -> str:
    """
    识别图片中的文字并直接生成作文提纲，仅返回生成的提纲

    Args:
        image_path (str): 图片文件路径
        grade (str): 年级信息（如"小学三年级"、"初中"等）
        difficulty (str, optional): 难度等级

    Returns:
        str: 生成的作文提纲
    """
    try:
        # 检查图片文件是否存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片文件未找到: {image_path}")

        # 设置默认语言
        languages = ['ch_sim', 'en']

        # 第一步：OCR识别
        logging.info(f"开始识别图片: {image_path}")
        reader = easyocr.Reader(languages, gpu=False)

        # 识别图片中的文字
        results = reader.readtext(image_path)

        # 提取纯文本内容
        texts = []
        for bbox, text, conf in results:
            texts.append(text)

        # 合并所有文本
        ocr_text = " ".join(texts)
        logging.info(f"识别完成，共识别到 {len(texts)} 条文本")

        # 第二步：生成作文提纲
        if not ocr_text or not grade:
            raise ValueError("请提供OCR文字内容和年级信息")

        client = get_openai_client()

        prompt = f"""你是一名专业的英语考试命题专家。请根据以下要求，设计一个适合学生写作的作文题目提纲：

1. 情景内容：
{ocr_text}

2. 设计要求：
- 年级：{grade}
- 难度：{difficulty if difficulty else "适中"}
- 题目需紧扣输入材料的主题和内容
- 明确作文类型（如议论文、记叙文、应用文等），如为应用文请注明格式（如电子邮件/信函/演讲）
- 如为叙述文，请注明时态要求
- 题目应包含所有关键信息点
- 字数要求：50-300字

3. 输出格式：
- 只需输出一个最合适的作文题目
- 格式：[类型] [年级]："用引号括起确切的问题文本"

示例输出：
[议论文] [初中]："Do you think it is better to study alone or with classmates? Give two reasons and examples to support your opinion."

请严格按照上述格式输出，不要添加多余解释。
"""

        chat_completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        
        return chat_completion.choices[0].message.content

    except Exception as e:
        logging.error(f"OCR识别并生成提纲失败: {e}")
        return f"error: {str(e)}"

@mcp.tool(description="根据关键词生成英语作文提纲")
def generate_outline_from_keywords(keywords: List[str], grade: str, difficulty: Optional[str] = None) -> str:
    """
    根据关键词、年级和难度，生成作文提纲
    
    Args:
        keywords (List[str]): 关键词列表，至少包含一个关键词
        grade (str): 年级信息
        difficulty (str, optional): 难度等级
        
    Returns:
        str: 生成的作文提纲
    """
    if not keywords or not isinstance(keywords, list):
        raise ValueError("请提供至少一个关键词，且以列表形式传入")
    if not grade:
        raise ValueError("请提供年级信息")
    
    client = get_openai_client()
    
    prompt = f""" 作为一名专业的英语考试设计师，请遵循以下准则设计合适的作文题目：

        1. 核心要求：
        - 指定作文类型：议论文/记叙文/应用文/等
        - 对于应用文写作，请指定格式（电子邮件/信函/演讲）
        - 对于叙述文，请注明时态要求
        - 对于图表，请描述假设数据
        - 目标年级：{grade}
        - 题目难度：{difficulty}
        - 题目关键词：{keywords}
        - 字数：50-300字

        2. 题目设计原则：
        A. 结构：
        - 清晰且有目的性的指示（例如，“讨论两种观点”或“描述一段经历”）
        - 题目中要包含所有的的关键词{keywords}
        - 如有需要，提供背景信息（3到5句话）
        - 明确的要求（观点+理由、例子等）

        B. 难度控制：
        - 小学：简单词汇、个人话题
        - 初中：基本学术术语、社会主题
        - 对于应用文写作，请指定格式（电子邮件/信函/演讲）
        - 高中及以上：抽象概念、批判性思维

        C. 主题选择：
        - 与年龄相符的现实生活主题
        - 避免敏感话题（政治/宗教）
        - 开放式但重点突出（避免过于宽泛的问题）

        3. 输出格式：
        - 只需要给出一个最适合的题目即可。
        [类型] [级别]：“用引号括起确切的问题文本”

        示例输出：
        [议论文] [高中]："Should schools teach financial literacy as a required subject? Discuss both views and give your opinion.
        Keywords: budget, required "

        注意：只输出题目，不要添加任何解释、注释或说明。
        """

    try:
        chat_completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"生成作文提纲时出错: {str(e)}"

@mcp.tool(description="根据作文提纲生成标准范文")
def generate_model_essay(outline: str, grade: str, difficulty: Optional[str] = None) -> str:
    """
    根据给定的作文提纲和年级，生成标准范文
    
    Args:
        outline (str): 作文提纲，要求为完整的题目或提纲内容
        grade (str): 年级信息，如"小学二年级"、"初中"等
        difficulty (str, optional): 难度等级
        
    Returns:
        str: 生成的范文内容
    """
    if not outline or not isinstance(outline, str):
        raise ValueError("请提供有效的作文提纲（字符串类型）")
    if not grade:
        raise ValueError("请提供年级信息")
    
    client = get_openai_client()
    
    prompt = f"""您是一位专业的英语写作老师。为符合以下要求的学生撰写一篇范文：

1. 论文规范：
- 年级：{grade}（例如：初中、高中）
- 难度：{difficulty if difficulty else "moderate"}
- 论文类型：指定论文类型，例如：议论文、记叙文、描写文
- 提纲/标题：{outline}

2. 内容要求：
- 严格遵循提供的提纲/主题
- 使用适合学生年龄的词汇和句子结构
- 语法、连贯性和逻辑性正确
- 包含所有必需元素（例如：论点、示例、论据、结论）

3. 风格与语气：
- 正式但引人入胜，符合目标年级要求
- 清晰简洁，堪称典范
- 根据论文类型调整语气（例如：议论文采用说服性语言，记叙文采用生动活泼的语言）

4. 格式：
- 包含标题
- 使用包含清晰主题句的段落

5. 输出：
- 完整的范文（字数适合年级）
- 仅输出文章，不需要带额外说明

中学叙事作文示例输出：
---
一次难忘的冒险

去年夏天，我在山间旅行中经历了一次难忘的冒险。清新的空气、参天的树木以及意想不到的挑战，使这次旅程成为我永生难忘的回忆。

当我们到达营地时……

这次旅行教会了我……
---
"""
    
    try:
        chat_completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        essay = chat_completion.choices[0].message.content.strip()
        return essay
    except Exception as e:
        return f"生成范文时出错: {str(e)}"

@mcp.tool(description="对学生作文进行智能批改和详细点评")
def mark_article(outline: str, article: str, grade: str, difficulty: Optional[str] = None) -> str:
    """
    对学生作文进行批改和详细点评
    
    Args:
        outline (str): 原始作文题目或提纲
        article (str): 学生写的作文内容
        grade (str): 年级信息，如"小学二年级"、"初中"等
        difficulty (str, optional): 难度等级
        
    Returns:
        str: 批改和点评内容
    """
    if not article or not isinstance(article, str):
        raise ValueError("请提供有效的作文内容（字符串类型）")
    if not grade:
        raise ValueError("请提供年级信息")
    
    client = get_openai_client()
    
    prompt = f"""
你是一名经验丰富的英语老师，请根据下列要求对学生作文进行详细批改和点评。

【学生作文】：
{article}

【年级】：{grade}
【难度】：{difficulty if difficulty else "中等"}

【批改要求】：
1. 综合评价：内容、结构、语言、风格。

2. 纠错方式：用红色下滑线标记错误🔴 <u>they won't finish their work.</u>并在后面使用括号给出解析，
            用蓝色下滑线标记错误🔵 <u>they won't finish their work.</u>并在后面使用括号给出改进建议，
            用绿色下划线突出有点🟢 <u>they won't finish their work.</u>并在后面使用括号进行说明句子好处。

3. 反馈格式：
[总分] /100
输出原文，在原文上进修改。

4. 用中文进行点评，点评内容要适合{grade}学生的水平，点评要指出改进建议和鼓励。

"""
    
    try:
        chat_completion = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"批改失败：{str(e)}"


if __name__ == "__main__":
    print("启动英语作文智能辅助系统MCP服务器...")
    print("可用工具:")
    print("1. ocr_and_generate_outline - OCR识别并生成作文提纲")
    print("2. generate_outline_from_keywords - 根据关键词生成作文提纲")
    print("3. generate_model_essay - 生成标准范文")
    print("4. mark_article - 作文批改和点评")
    
    mcp.run(
        transport="sse",
    ) 