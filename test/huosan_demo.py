from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List, Dict, Any
load_dotenv()
from volcenginesdkarkruntime import Ark
import os
from time import time
HS_API_BASE="https://ark.cn-beijing.volces.com/api/v3"
HS_API_KEY="f2db87be-c47a-4184-b206-a5ea1cdcc63f"

model="doubao-seed-1-6-flash-250828"

# 提示词变量
subject = "小学数学"
grade = "五年级上册"
textbook = "小学数学苏教版五年级上册"
section = "五 小数乘法和除法"
current_knowledge = "小数乘小数"
question_type = "单选题"
difficulty = "难"
count = 3
learned_knowledge = "小数乘整数,小数加法,小数减法,小数的意义,小数的性质,三角形的面积,正方形的面积,矩形的面积,平行四边形的面积,梯形的面积,圆的面积,方向的认识,位置的认识,图形的平移,坐标的认识"


prompt=f"""
# Role
你是一位拥有10年经验的资深小学数学教研员，精通各国标准课程大纲（如人教版、北师大版）。你擅长将抽象的知识点转化为具有挑战性、情境感且逻辑严密的综合性题目蓝图。

# Input Parameters
请根据以下变量生成题目蓝图：
<parameters>
- 学科 <Subject>：{subject}
- 年级 <Grade>：{grade}
- 教材版本 <Textbook>：{textbook}（若未指定，默认参考人教版）
- 章节 <Section>：{section}
- 当前知识点 <Current_Knowledge>：{current_knowledge}
- 题目类型 <Question_Type>：{question_type}
- 难度 <Difficulty>：{difficulty}（可选值：易、较易、中档、较难、难）
- 题目总数 <Count>：{count}
- 已学知识点列表 <Learned_Knowledge>：{learned_knowledge}
- 输出语言 <Language>：Chinese
</parameters>

# Constraints & Logic
1. **知识点组合策略**：
   - 核心：必须以 <Current_Knowledge> 为核心。
   - 关联：从 <Learned_Knowledge> 中挑选 1-2 个具有逻辑关联（如逆运算、递进、转化）的知识点。
   - **空值处理**：若 <Learned_Knowledge> 为空，则 `knowledge_compose` 必须仅包含 `["<Current_Knowledge>"]`。

2. **难度量化标准（严格执行）**：
   - **易**：1步逻辑（直接代入公式/定义）；数值整洁；干扰项针对粗心点。
   - **较易**：2步逻辑（读题转化 -> 基础计算）；情境直观；干扰项针对单一概念混淆。
   - **中档**：2-3步逻辑（含1个关键决策点，如分段处理或公式变形）；干扰项覆盖2种错误路径。
   - **较难**：**严格 3 步推理**（涉及知识迁移，如：单位换算 -> 隐含条件挖掘 -> 综合应用）；干扰项体现思路型错误。
   - **难**：**4 步及以上推理**（必须含“模型化”过程，如：逆向推理、构建等量关系、动态变化分析）；干扰项体现完整但错误的建模路径。
   - **计算量原则**：难度应体现在“思维深度”。确保数值对学生友好（凑整/简算），避免无意义的繁琐计算。

3. **版本适配逻辑**：
   - 若为“北师大版”，情境设计应尝试引入“情境串”或“主题图”风格。
   - 若为“人教版”，侧重逻辑的严密性与典型数学模型的应用。

4. **输出约束**：
   - 必须输出合法的 JSON 数组。
   - **严禁任何开场白、结尾解释或 Markdown 代码块标签**。
   - 确保 `scenario_setting` 简洁（指提供描述方向）。
   - 当 {count} > 1 时，确保各题目蓝图的情境从 [购物、工程、实验、运动、图形、文化、环保、规划] 中随机选择且不重复。

# Internal Process (Self-Correction)
1. **合规检查**：核对 `knowledge_compose` 是否越界（超前使用未学知识）。
2. **数值预审**：预设数值逻辑是否支持简便运算。

# Output Format (JSON)
{{
  "result": [
    {{
      "knowledge": "当前知识点名称",
      "knowledge_compose": ["<Current_Knowledge>", "关联知识点A"],
      "assessment_dimension": "简述考查的数学能力及预设的干扰项逻辑",
      "scenario_setting": "简单描述题目生成方向"
    }}
  ]
}}

# Example (Logic Reference)
{{
  "result": [
    {{
      "knowledge": "圆的面积",
      "knowledge_compose": ["圆的面积", "长度单位换算"],
      "assessment_dimension": "考查逆向思维与多级转化能力。干扰项预设为：直接将周长代入面积公式或忘记平方。",
      "scenario_setting": "校园喷泉护栏改造情境"
    }}
  ]
}}
"""


class BlueprintItem(BaseModel):
    knowledge: str = Field(description="当前知识点名称")
    knowledge_compose: List[str] = Field(description="知识点组合，包含至少<Current_Knowledge>及逻辑相关知识点")
    assessment_dimension: str = Field(description="简述考查的数学能力及预设的干扰项逻辑")
    scenario_setting: str = Field(description="简单描述题目生成方向")

class BlueprintResult(BaseModel):
    result: List[BlueprintItem]



client = Ark(
    base_url=HS_API_BASE,
    api_key=HS_API_KEY,
)

time_start = time()
# 使用结构化输出，确保返回 JSON 格式
response = client.beta.chat.completions.parse(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    response_format=BlueprintResult,
    extra_headers={'x-is-encrypted': 'true'},
    extra_body={
        "temperature": 0.5,
        "top_p": 0.9,
        "max_tokens": 12000,
        "repetition_penalty": 1.2,
        "thinking": {"type": "disabled"},
    },
)
# 解析并打印 JSON 结果
result_json = response.choices[0].message.parsed
print(result_json.model_dump_json(indent=2))
time_end = time()
print(f"Time taken: {time_end - time_start} seconds")
