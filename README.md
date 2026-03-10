# 电商智能体演示系统

一个基于 FastAPI 和火山引擎 Ark 的电商智能体演示系统，支持用户管理、商品管理、订单管理和智能体对话功能。

## 功能特性

- ✅ 用户管理：支持商家和买家两种角色，可切换用户
- ✅ 商品管理：商家可新增、编辑、删除商品
- ✅ 订单管理：买家可使用余额购买商品，自动检查余额和库存
- ✅ 智能体对话：通过火山引擎 Ark 实现自然语言交互
  - 支持对话记忆（保留最近10轮对话历史）
  - 支持实际执行购买操作（不仅仅是回复文本）
  - 智能解析用户意图，自动匹配商品
- ✅ 语音输入：支持浏览器语音转文字功能
- ✅ 提示词统一管理：所有提示词集中管理，便于维护
- ✅ MCP 工具支持：可选使用 MCP 框架进行工具调用

## 技术栈

### 后端
- FastAPI - Web 框架
- SQLite3 - 数据库
- 火山引擎 Ark - 大模型服务
- Pydantic - 数据验证
- FastMCP - MCP 框架（可选，用于工具调用）
- 提示词统一管理 - 集中管理所有提示词模板

### 前端
- 原生 HTML/CSS/JavaScript
- Web Speech API - 语音识别

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写火山引擎配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```
HS_API_BASE=https://ark.cn-beijing.volces.com/api/v3
HS_API_KEY=your_api_key_here
HS_MODEL=doubao-seed-1-6-flash-250828
```

> 注意：如果没有配置火山引擎 API，系统会使用降级方案（关键词匹配）进行对话。

### 3. 启动服务

```bash
cd backend
python main.py
```

或者使用 uvicorn：

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问系统

打开浏览器访问：http://localhost:8000

## 项目结构

```
agent-demo/
├── backend/              # 后端代码
│   ├── main.py          # FastAPI 主程序
│   ├── models.py        # 数据模型
│   ├── database.py      # 数据库连接和初始化
│   ├── crud.py          # 共用 CRUD 基类
│   ├── services.py      # 业务逻辑层
│   ├── prompts.py       # 提示词统一管理
│   ├── mcp_server.py   # MCP 服务器（可选）
│   └── routers/         # API 路由
│       ├── users.py     # 用户路由
│       ├── products.py  # 商品路由
│       ├── orders.py    # 订单路由
│       └── agent.py     # 智能体路由
├── frontend/            # 前端代码
│   ├── index.html       # 主页面
│   ├── css/
│   │   └── style.css    # 样式文件
│   └── js/
│       ├── app.js       # 主应用逻辑
│       └── speech-input.js  # 语音输入功能
├── data/                # 数据库文件（自动创建）
├── .env                 # 环境配置（需自行创建）
├── requirements.txt     # Python 依赖
├── README.md            # 项目说明
```

## API 文档

启动服务后，访问 http://localhost:8000/docs 查看自动生成的 API 文档。

## 使用说明

1. **选择用户**：在顶部下拉框中选择要使用的用户（商家或买家）
2. **用户管理**：查看所有用户信息
3. **商品管理**：
   - 商家可以新增、编辑、删除商品
   - 买家可以浏览商品并购买
4. **订单管理**：查看订单列表
5. **智能体对话**：
   - 输入文字消息或点击麦克风使用语音输入
   - 智能体会根据上下文理解意图并执行相应操作
   - 支持对话记忆，能记住最近10轮对话历史
   - 支持实际执行购买操作（如"帮我购买一件耳机"会自动创建订单）
   
   **常用提问示例**：
   - 商品查询："帮我查询一下现在有哪些商品"、"查询iPhone手机的信息"
   - 购买商品："我需要购买智能机械键盘"、"帮我购买一件耳机"
   - 订单查询："查询一下我购买了哪些商品"、"我的订单有哪些？"
   - 用户信息："我的余额是多少？"、"查询我的账户信息"

## 注意事项

1. **浏览器兼容性**：语音识别功能主要在 Chrome/Edge 浏览器支持
2. **数据库**：首次运行会自动创建数据库并初始化示例数据
3. **权限**：使用语音功能时需要授权麦克风权限

## 开发说明

### 代码特点

- **精简设计**：使用共用 CRUD 基类，避免代码冗余
- **业务分离**：业务逻辑集中在 services.py
- **统一接口**：所有 API 遵循 RESTful 规范
- **提示词管理**：所有提示词统一管理在 prompts.py，便于维护
- **对话记忆**：智能体支持保留最近10轮对话历史
- **实际执行**：智能体可以真正执行购买等操作，不仅仅是回复文本

### 扩展开发

- 添加新的数据表：在 `crud.py` 中实例化新的 CRUD 对象
- 添加新的业务逻辑：在 `services.py` 中添加新的服务类
- 添加新的路由：在 `routers/` 目录下创建新的路由文件
- 修改提示词：在 `prompts.py` 中修改对应的提示词方法
- 添加 MCP 工具：在 `mcp_server.py` 中使用 `@mcp.tool` 装饰器添加新工具

### 相关文档

- [提示词管理说明](PROMPTS_README.md) - 了解如何管理和修改提示词
- [MCP 使用说明](MCP_USAGE.md) - 了解如何使用 MCP 工具调用

## License

MIT

