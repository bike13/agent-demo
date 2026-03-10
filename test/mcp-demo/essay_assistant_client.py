from fastmcp import Client
from fastmcp.client.transports import SSETransport
import asyncio
import os
from typing import Dict, Any


async def list_all_tools() -> None:
    """
    列出所有可用工具及其描述和参数
    """
    print("=== 列出所有可用工具 ===")
    async with Client(SSETransport("http://127.0.0.1:9002/sse")) as client:
        tools = await client.list_tools()
        for i, tool in enumerate(tools, 1):
            print(f"{i}. Tool: {tool.name}")
            print(f"   Description: {tool.description}")
            if tool.inputSchema:
                print(f"   Parameters: {tool.inputSchema}")
            print()


async def test_ocr_and_generate_outline() -> str:
    """
    测试OCR识别并生成作文提纲工具
    返回最终的结果字符串
    """
    print("=== 测试OCR识别并生成作文提纲 ===")
    async with Client(SSETransport("http://127.0.0.1:9002/sse")) as client:
        try:
            # 使用项目中的测试图片
            image_path = "../data/images/case1_ch.jpg"
            if not os.path.exists(image_path):
                print(f"测试图片不存在: {image_path}")
                return "测试图片不存在"

            result = await client.call_tool("ocr_and_generate_outline", {
                "image_path": image_path,
                "grade": "初中",
                "difficulty": "中等"
            })

            # 解析返回结果
            if hasattr(result, "data"):
                return result.data
            elif isinstance(result, dict) and "data" in result:
                return result["data"]
            elif isinstance(result, str):
                return result
            else:
                return str(result)

     
        except Exception as e:
            return f"测试失败: {e}"



async def test_generate_outline_from_keywords() -> str:
    """
    测试根据关键词生成作文提纲工具
    返回最终的结果字符串
    """
    print("=== 测试根据关键词生成作文提纲 ===")
    async with Client(SSETransport("http://127.0.0.1:9002/sse")) as client:
        try:
            result = await client.call_tool("generate_outline_from_keywords", {
                "keywords": ["environment", "pollution", "solution"],
                "grade": "高中",
                "difficulty": "困难"
            })

            # 解析返回结果，方式与test_ocr_and_generate_outline一致
            if hasattr(result, "data"):
                return result.data
            elif isinstance(result, dict) and "data" in result:
                return result["data"]
            elif isinstance(result, str):
                return result
            else:
                return str(result)

        except Exception as e:
            return f"测试失败: {e}"
       


async def test_generate_model_essay() -> str:
    """
    测试生成标准范文工具
    返回最终的结果字符串
    """
    print("=== 测试生成标准范文 ===")
    async with Client(SSETransport("http://127.0.0.1:9002/sse")) as client:
        try:
            # 使用一个示例提纲
            sample_outline = "[议论文] [初中]: \"Do you think it is better to study alone or with classmates? Give two reasons and examples to support your opinion.\""
            
            result = await client.call_tool("generate_model_essay", {
                "outline": sample_outline,
                "grade": "初中",
                "difficulty": "中等"
            })

            # 解析返回结果，方式与test_generate_outline_from_keywords一致
            if hasattr(result, "data"):
                return result.data
            elif isinstance(result, dict) and "data" in result:
                return result["data"]
            elif isinstance(result, str):
                return result
            else:
                return str(result)

        except Exception as e:
            return f"测试失败: {e}"


async def test_mark_article() -> str:
    """
    测试作文批改和点评工具
    返回最终的结果字符串
    """
    print("=== 测试作文批改和点评 ===")
    async with Client(SSETransport("http://127.0.0.1:9002/sse")) as client:
        try:
            # 使用示例作文和提纲
            sample_outline = "[议论文] [初中]: \"Do you think it is better to study alone or with classmates?\""
            sample_article = """
            I think studying with classmates is better than studying alone. First, when we study together, we can help each other. If someone doesn't understand something, others can explain it. Second, studying in a group makes learning more fun and less boring. We can discuss ideas and share different opinions. This helps us learn more and remember better. In conclusion, studying with classmates is the best way to learn.
            """
            
            result = await client.call_tool("mark_article", {
                "outline": sample_outline,
                "article": sample_article,
                "grade": "初中",
                "difficulty": "中等"
            })

            # 解析返回结果，方式与test_generate_outline_from_keywords一致
            if hasattr(result, "data"):
                return result.data
            elif isinstance(result, dict) and "data" in result:
                return result["data"]
            elif isinstance(result, str):
                return result
            else:
                return str(result)

        except Exception as e:
            return f"测试失败: {e}"




async def main() -> None:
    """
    主函数：运行所有测试
    """
    print("开始测试英语作文智能辅助系统MCP服务器...")
    
    try:
        # 1. 列出所有工具
        # await list_all_tools()
        
        # 2. 测试各个工具
        print("="*80)
        result = await test_ocr_and_generate_outline()
        print(result)
        print("="*80)
        result = await test_generate_outline_from_keywords()
        print(result)
        print("="*80)
        result = await test_generate_model_essay()
        print(result)
        print("="*80)
        result = await test_mark_article()
        print(result)
        
        print("所有测试完成！")
        
    except Exception as e:
        print(f"测试过程中出现错误: {e}")


if __name__ == "__main__":
    asyncio.run(main())
