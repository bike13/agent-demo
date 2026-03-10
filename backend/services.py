"""业务逻辑层"""
from typing import Optional, Dict, Any
from .crud import user_crud, product_crud, order_crud
from .models import OrderCreate, IntentRecognition
from .prompts import prompt_manager


class OrderService:
    """订单服务类"""
    
    @staticmethod
    def create_order(order_data: OrderCreate) -> Dict[str, Any]:
        """创建订单（包含余额检查和库存检查）"""
        buyer = user_crud.get_by_id(order_data.buyer_id)
        if not buyer:
            return {"success": False, "error": "买家不存在"}
        if buyer["role"] != "buyer":
            return {"success": False, "error": "只有买家可以下单"}
        
        product = product_crud.get_by_id(order_data.product_id)
        if not product:
            return {"success": False, "error": "商品不存在"}
        
        total_amount = product["price"] * order_data.quantity
        
        # 检查库存
        if product["stock"] < order_data.quantity:
            return {"success": False, "error": f"库存不足，当前库存：{product['stock']}"}
        
        # 检查余额
        if buyer["balance"] < total_amount:
            return {
                "success": False,
                "error": f"余额不足，当前余额：{buyer['balance']:.2f}，订单金额：{total_amount:.2f}"
            }
        
        # 事务处理：创建订单、扣除余额、减少库存
        from .database import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                # 创建订单
                order_id = order_crud.create({
                    "buyer_id": order_data.buyer_id,
                    "product_id": order_data.product_id,
                    "quantity": order_data.quantity,
                    "total_amount": total_amount
                })
                
                # 扣除余额
                cursor.execute(
                    "UPDATE tc_users SET balance = balance - ? WHERE id = ?",
                    (total_amount, order_data.buyer_id)
                )
                
                # 减少库存
                cursor.execute(
                    "UPDATE tc_products SET stock = stock - ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (order_data.quantity, order_data.product_id)
                )
                
                return {"success": True, "order_id": order_id, "total_amount": total_amount}
            except Exception as e:
                return {"success": False, "error": f"创建订单失败：{str(e)}"}


class AgentService:
    """智能体服务类"""
    
    def __init__(self):
        self._client = None
        self._model = None
        # 为每个用户维护对话历史 {user_id: [{"role": "user/assistant", "content": "..."}, ...]}
        self._conversations: Dict[int, list] = {}
        # 为每个用户维护待确认的购买信息 {user_id: {"product_id": int, "quantity": int, "product_name": str, "total_amount": float}}
        self._pending_purchases: Dict[int, Dict[str, Any]] = {}
    
    def _get_client(self):
        """懒加载火山引擎客户端"""
        if self._client is None:
            try:
                from dotenv import load_dotenv
                import os
                from volcenginesdkarkruntime import Ark
                
                load_dotenv()
                api_base = os.getenv("HS_API_BASE", "https://ark.cn-beijing.volces.com/api/v3")
                api_key = os.getenv("HS_API_KEY", "")
                model = os.getenv("HS_MODEL", "doubao-seed-1-6-flash-250828")
                
                if not api_key:
                    return None
                
                self._client = Ark(base_url=api_base, api_key=api_key)
                self._model = model
            except ImportError:
                return None
        return self._client
    
    def chat(self, message: str, user_id: int) -> Dict[str, Any]:
        """智能体对话处理（保留最近10轮对话记忆，支持实际调用工具）"""
        # 获取系统上下文信息
        users = user_crud.get_all()
        products = product_crud.get_all()
        orders = order_crud.filter(buyer_id=user_id) if user_id else []
        current_user = user_crud.get_by_id(user_id) if user_id else None
        
        # 使用统一的提示词管理器
        system_prompt = prompt_manager.get_system_prompt(
            users=users,
            products=products,
            user_id=user_id,
            current_user=current_user,
            orders=orders
        )
        
        client = self._get_client()
        if not client:
            # 降级方案：简单的关键词匹配
            return self._fallback_chat(message, user_id)
        
        try:
            # 获取该用户的对话历史（最近10轮，即20条消息）
            history = self._get_conversation_history(user_id)
            
            # 构建消息列表：系统提示词 + 历史对话 + 当前用户消息
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(history)  # 添加历史对话
            messages.append({"role": "user", "content": message})  # 添加当前消息
            
            # 调用大模型
            response = client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            )
            reply = response.choices[0].message.content
            
            # 使用大模型进行意图识别
            intent = self._recognize_intent_with_llm(message, user_id, history, client, products)
            action_result = None
            
            # 根据意图执行相应操作
            if user_id in self._pending_purchases:
                # 有待确认的购买，检查是否为确认/取消意图
                if intent and intent.intent == "confirm":
                    # 用户确认购买
                    confirm_result = self._execute_confirmed_purchase(user_id)
                    if confirm_result:
                        action_result = confirm_result
                        if action_result.get("executed"):
                            reply = action_result.get("reply", reply)
                        else:
                            reply = action_result.get("error", "购买失败")
                elif intent and intent.intent == "cancel":
                    # 用户取消购买
                    if user_id in self._pending_purchases:
                        del self._pending_purchases[user_id]
                    reply = "已取消购买。"
                # 如果大模型没有识别为确认/取消，使用降级方案（关键词匹配）
                elif not intent:
                    confirm_result = self._check_purchase_confirmation(message, user_id)
                    if confirm_result:
                        action_result = confirm_result
                        if action_result.get("executed"):
                            reply = action_result.get("reply", reply)
                        elif action_result.get("cancelled"):
                            reply = "已取消购买。"
                        else:
                            reply = action_result.get("error", "购买失败")
                # 如果不是确认/取消，继续正常对话
            elif intent and intent.intent == "purchase":
                # 识别到购买意图，生成确认消息
                # 如果大模型没有识别出product_id，尝试从历史对话中提取
                product_id = intent.product_id
                quantity = intent.quantity or 1
                
                if not product_id:
                    # 尝试从历史对话中提取商品ID
                    product_id = self._extract_product_id_from_history(message, history, products)
                
                purchase_result = self._prepare_purchase_confirmation(
                    product_id, quantity, user_id
                )
                if purchase_result:
                    action_result = purchase_result
                    if purchase_result.get("needs_confirmation"):
                        reply = purchase_result.get("reply", reply)
                    elif purchase_result.get("error"):
                        reply = purchase_result.get("error", "购买失败")
            elif not intent:
                # 大模型识别失败，使用降级方案（关键词匹配）
                purchase_result = self._try_execute_purchase(message, user_id, history)
                if purchase_result:
                    action_result = purchase_result
                    if purchase_result.get("needs_confirmation"):
                        reply = purchase_result.get("reply", reply)
                    elif purchase_result.get("executed"):
                        reply = purchase_result.get("reply", reply)
                    elif purchase_result.get("error"):
                        reply = purchase_result.get("error", "购买失败")
            
            # 保存对话历史（用户消息 + 助手回复）
            self._save_conversation(user_id, message, reply)
            
            return {"reply": reply, "action_result": action_result}
        except Exception as e:
            return {"reply": f"智能体服务出错：{str(e)}", "action_result": None}
    
    def _recognize_intent_with_llm(
        self, message: str, user_id: int, history: list, client, products: list
    ) -> Optional[IntentRecognition]:
        """使用大模型识别用户意图"""
        try:
            # 构建意图识别提示词
            products_info = "\n".join([f"ID:{p['id']} {p['name']}" for p in products])
            
            # 构建历史对话上下文（最近3轮）
            history_context = ""
            if history:
                recent_history = history[-6:] if len(history) > 6 else history
                for msg in recent_history:
                    role = "用户" if msg.get("role") == "user" else "助手"
                    history_context += f"{role}: {msg.get('content', '')}\n"
            
            has_pending = user_id in self._pending_purchases
            pending_info = ""
            if has_pending:
                pending = self._pending_purchases[user_id]
                pending_info = f"\n当前有待确认的购买：商品{pending['product_name']} (ID:{pending['product_id']})，数量{pending['quantity']}件，金额¥{pending['total_amount']:.2f}"
            
            intent_prompt = f"""请分析用户消息的意图，并返回JSON格式的结果。

用户消息：{message}

当前商品列表：
{products_info}
{pending_info}

历史对话：
{history_context if history_context else "无"}

请返回JSON格式：
{{
    "intent": "purchase|confirm|cancel|query|other",
    "product_id": 商品ID（如果是购买意图，从商品列表中匹配，如果提到商品名称但不确定ID，设为null）,
    "quantity": 购买数量（如果是购买意图，默认为1）,
    "confidence": 0.0-1.0之间的置信度
}}

意图说明：
- purchase: 用户想要购买商品（如"我要买XXX"、"购买XXX"）
- confirm: 用户确认购买（回复"确认"、"是的"、"好的"、"同意"等表示确认的词语）
- cancel: 用户取消购买（回复"取消"、"不要"、"算了"等表示拒绝的词语）
- query: 用户查询信息（如"查询商品"、"我的订单"）
- other: 其他意图

重要：
1. 如果用户提到商品名称但商品列表中找不到，product_id设为null
2. 如果历史对话中提到过商品ID，可以从历史中提取
3. 只返回JSON，不要其他文字。"""
            
            # 调用大模型进行意图识别
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": "你是一个意图识别助手，只返回JSON格式的结果，不要添加任何解释。"},
                    {"role": "user", "content": intent_prompt}
                ],
                temperature=0.3,
                max_tokens=500,
            )
            
            import json
            import re
            content = response.choices[0].message.content.strip()
            
            # 提取JSON部分（支持多行JSON）
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', content, re.DOTALL)
            if json_match:
                try:
                    intent_data = json.loads(json_match.group(0))
                    # 验证并创建IntentRecognition对象
                    if "intent" in intent_data:
                        # 处理product_id可能为null的情况
                        if intent_data.get("product_id") is None:
                            intent_data["product_id"] = None
                        # 处理quantity可能为null的情况
                        if intent_data.get("quantity") is None:
                            intent_data["quantity"] = 1
                        return IntentRecognition(**intent_data)
                except Exception:
                    pass
            
            return None
        except Exception as e:
            # 如果大模型识别失败，返回None，使用降级方案
            return None
    
    def _prepare_purchase_confirmation(
        self, product_id: Optional[int], quantity: Optional[int], user_id: int
    ) -> Optional[Dict[str, Any]]:
        """准备购买确认（检查并生成确认消息）"""
        if not product_id or not user_id:
            return None
        
        product = product_crud.get_by_id(product_id)
        if not product:
            return {
                "executed": False,
                "error": "商品不存在"
            }
        
        quantity = quantity or 1
        total_amount = product["price"] * quantity
        
        buyer = user_crud.get_by_id(user_id)
        if not buyer:
            return {
                "executed": False,
                "error": "买家不存在"
            }
        
        if buyer["role"] != "buyer":
            return {
                "executed": False,
                "error": "只有买家可以下单"
            }
        
        # 检查库存
        if product["stock"] < quantity:
            error_msg = prompt_manager.get_order_failure_message(
                error=f"库存不足，当前库存：{product['stock']}",
                product_name=product['name'],
                product_id=product_id,
                quantity=quantity
            )
            return {
                "executed": False,
                "error": error_msg
            }
        
        # 检查余额
        if buyer["balance"] < total_amount:
            error_msg = prompt_manager.get_order_failure_message(
                error=f"余额不足，当前余额：{buyer['balance']:.2f}，订单金额：{total_amount:.2f}",
                product_name=product['name'],
                product_id=product_id,
                quantity=quantity
            )
            return {
                "executed": False,
                "error": error_msg
            }
        
        # 生成确认消息
        confirm_msg = prompt_manager.get_purchase_confirmation_message(
            product_name=product['name'],
            product_id=product_id,
            quantity=quantity,
            price=product['price'],
            total_amount=total_amount,
            current_balance=buyer['balance']
        )
        
        # 保存待确认的购买信息
        self._pending_purchases[user_id] = {
            "product_id": product_id,
            "quantity": quantity,
            "product_name": product['name'],
            "total_amount": total_amount
        }
        
        return {
            "needs_confirmation": True,
            "reply": confirm_msg,
            "pending_purchase": True
        }
    
    def _execute_confirmed_purchase(self, user_id: int) -> Optional[Dict[str, Any]]:
        """执行已确认的购买"""
        if user_id not in self._pending_purchases:
            return None
        
        pending = self._pending_purchases[user_id]
        product_id = pending["product_id"]
        quantity = pending["quantity"]
        
        try:
            order_data = OrderCreate(
                buyer_id=user_id,
                product_id=product_id,
                quantity=quantity
            )
            result = order_service.create_order(order_data)
            
            if result.get("success"):
                order = order_crud.get_by_id(result["order_id"])
                product = product_crud.get_by_id(product_id)
                buyer = user_crud.get_by_id(user_id)
                
                reply = prompt_manager.get_order_success_message(
                    order_id=order['id'],
                    product_name=product['name'],
                    product_id=product_id,
                    quantity=quantity,
                    total_amount=order['total_amount'],
                    old_balance=buyer['balance'] + order['total_amount'],
                    new_balance=buyer['balance'],
                    old_stock=product['stock'] + quantity,
                    new_stock=product['stock']
                )
                
                return {
                    "executed": True,
                    "reply": reply,
                    "order_id": result["order_id"],
                    "action": "create_order"
                }
            else:
                product = product_crud.get_by_id(product_id)
                product_name = product['name'] if product else None
                
                error_msg = prompt_manager.get_order_failure_message(
                    error=result.get("error", "创建订单失败"),
                    product_name=product_name,
                    product_id=product_id,
                    quantity=quantity
                )
                return {
                    "executed": False,
                    "error": error_msg,
                    "error_detail": result.get("error", "创建订单失败")
                }
        except Exception as e:
            return {
                "executed": False,
                "error": f"执行购买时出错：{str(e)}"
            }
    
    def _try_execute_purchase(self, message: str, user_id: int, history: list) -> Optional[Dict[str, Any]]:
        """尝试解析购买意图并执行购买操作"""
        import re
        
        # 检查是否包含购买相关关键词
        purchase_keywords = ["购买", "买", "下单", "订购", "要", "需要"]
        if not any(keyword in message for keyword in purchase_keywords):
            return None
        
        # 从消息和历史中提取商品信息
        products = product_crud.get_all()
        product_id = None
        quantity = 1
        
        # 尝试从消息中提取商品ID
        id_match = re.search(r'(?:商品)?ID[：:]?\s*(\d+)', message, re.IGNORECASE)
        if id_match:
            product_id = int(id_match.group(1))
        else:
            # 尝试从商品名称匹配（更智能的匹配）
            message_lower = message.lower()
            for product in products:
                product_name_lower = product['name'].lower()
                # 检查消息中是否包含商品名称的关键词
                # 提取商品名称中的关键词（去除常见词）
                name_parts = [p for p in product_name_lower.split() if len(p) > 2]
                name_parts.extend(product_name_lower.split('，'))
                name_parts.extend(product_name_lower.split('、'))
                
                # 检查消息中是否包含商品名称的关键部分
                for part in name_parts:
                    if part and part in message_lower:
                        product_id = product['id']
                        break
                
                # 也检查完整的商品名称
                if not product_id and product_name_lower in message_lower:
                    product_id = product['id']
                    break
                
                # 检查商品名称中的关键词（如"耳机"、"手机"等）
                keywords = ["耳机", "手机", "电脑", "键盘", "iphone", "thinkpad", "索尼", "sony"]
                for keyword in keywords:
                    if keyword in message_lower and keyword in product_name_lower:
                        product_id = product['id']
                        break
                
                if product_id:
                    break
        
        # 从历史对话中查找商品ID（如果当前消息没有）
        if not product_id:
            for msg in reversed(history):
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    # 查找商品ID
                    id_match = re.search(r'(?:商品)?ID[：:]?\s*(\d+)', content, re.IGNORECASE)
                    if id_match:
                        product_id = int(id_match.group(1))
                        break
                    # 如果没找到ID，尝试从商品名称匹配
                    if not product_id:
                        content_lower = content.lower()
                        for product in products:
                            if product['name'].lower() in content_lower:
                                # 尝试从内容中提取ID
                                product_id_match = re.search(rf"{re.escape(product['name'])}.*?ID[：:]?\s*(\d+)", content, re.IGNORECASE)
                                if product_id_match:
                                    product_id = int(product_id_match.group(1))
                                    break
                                # 如果内容中提到了商品名称，使用该商品
                                elif product['name'] in content:
                                    product_id = product['id']
                                    break
                        if product_id:
                            break
        
        # 提取数量
        quantity_match = re.search(r'(\d+)\s*(?:件|个|台|只)', message)
        if quantity_match:
            quantity = int(quantity_match.group(1))
        elif "一件" in message or "一个" in message or "1件" in message or "1个" in message:
            quantity = 1
        
        # 如果找到了商品ID，生成确认消息而不是直接执行购买
        if product_id and user_id:
            product = product_crud.get_by_id(product_id)
            if not product:
                return {
                    "executed": False,
                    "error": "商品不存在"
                }
            
            # 计算总金额
            total_amount = product["price"] * quantity
            
            # 检查余额和库存（但不执行购买）
            buyer = user_crud.get_by_id(user_id)
            if not buyer:
                return {
                    "executed": False,
                    "error": "买家不存在"
                }
            
            if buyer["role"] != "buyer":
                return {
                    "executed": False,
                    "error": "只有买家可以下单"
                }
            
            # 检查库存
            if product["stock"] < quantity:
                error_msg = prompt_manager.get_order_failure_message(
                    error=f"库存不足，当前库存：{product['stock']}",
                    product_name=product['name'],
                    product_id=product_id,
                    quantity=quantity
                )
                return {
                    "executed": False,
                    "error": error_msg
                }
            
            # 检查余额
            if buyer["balance"] < total_amount:
                error_msg = prompt_manager.get_order_failure_message(
                    error=f"余额不足，当前余额：{buyer['balance']:.2f}，订单金额：{total_amount:.2f}",
                    product_name=product['name'],
                    product_id=product_id,
                    quantity=quantity
                )
                return {
                    "executed": False,
                    "error": error_msg
                }
            
            # 生成确认消息并保存待确认的购买信息
            confirm_msg = prompt_manager.get_purchase_confirmation_message(
                product_name=product['name'],
                product_id=product_id,
                quantity=quantity,
                price=product['price'],
                total_amount=total_amount,
                current_balance=buyer['balance']
            )
            
            # 保存待确认的购买信息
            self._pending_purchases[user_id] = {
                "product_id": product_id,
                "quantity": quantity,
                "product_name": product['name'],
                "total_amount": total_amount
            }
            
            return {
                "needs_confirmation": True,
                "reply": confirm_msg,
                "pending_purchase": True
            }
        
            return None
    
    def _extract_product_id_from_history(
        self, message: str, history: list, products: list
    ) -> Optional[int]:
        """从历史对话中提取商品ID（降级方案）"""
        import re
        
        # 尝试从消息中提取商品ID
        id_match = re.search(r'(?:商品)?ID[：:]?\s*(\d+)', message, re.IGNORECASE)
        if id_match:
            return int(id_match.group(1))
        
        # 尝试从商品名称匹配
        message_lower = message.lower()
        for product in products:
            product_name_lower = product['name'].lower()
            # 检查消息中是否包含商品名称的关键词
            keywords = ["耳机", "手机", "电脑", "键盘", "iphone", "thinkpad", "索尼", "sony"]
            for keyword in keywords:
                if keyword in message_lower and keyword in product_name_lower:
                    return product['id']
            if product_name_lower in message_lower:
                return product['id']
        
        # 从历史对话中查找
        for msg in reversed(history):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                id_match = re.search(r'(?:商品)?ID[：:]?\s*(\d+)', content, re.IGNORECASE)
                if id_match:
                    return int(id_match.group(1))
        
        return None
    
    def _check_purchase_confirmation(self, message: str, user_id: int) -> Optional[Dict[str, Any]]:
        """检查用户是否确认购买"""
        if user_id not in self._pending_purchases:
            return None
        
        # 检查确认关键词
        confirm_keywords = ["确认", "是的", "好的", "同意", "确定", "ok", "yes", "y", "确认购买", "确认下单"]
        cancel_keywords = ["取消", "不要", "算了", "不买", "no", "n"]
        
        message_lower = message.lower().strip()
        
        # 检查是否取消
        if any(keyword in message_lower for keyword in cancel_keywords):
            pending = self._pending_purchases[user_id]
            del self._pending_purchases[user_id]
            return {
                "executed": False,
                "error": "已取消购买",
                "cancelled": True
            }
        
        # 检查是否确认
        if any(keyword in message_lower for keyword in confirm_keywords):
            pending = self._pending_purchases[user_id]
            product_id = pending["product_id"]
            quantity = pending["quantity"]
            
            # 执行购买
            try:
                order_data = OrderCreate(
                    buyer_id=user_id,
                    product_id=product_id,
                    quantity=quantity
                )
                result = order_service.create_order(order_data)
                
                if result.get("success"):
                    order = order_crud.get_by_id(result["order_id"])
                    product = product_crud.get_by_id(product_id)
                    buyer = user_crud.get_by_id(user_id)
                    
                    reply = prompt_manager.get_order_success_message(
                        order_id=order['id'],
                        product_name=product['name'],
                        product_id=product_id,
                        quantity=quantity,
                        total_amount=order['total_amount'],
                        old_balance=buyer['balance'] + order['total_amount'],
                        new_balance=buyer['balance'],
                        old_stock=product['stock'] + quantity,
                        new_stock=product['stock']
                    )
                    
                    return {
                        "executed": True,
                        "reply": reply,
                        "order_id": result["order_id"],
                        "action": "create_order"
                    }
                else:
                    product = product_crud.get_by_id(product_id)
                    product_name = product['name'] if product else None
                    
                    error_msg = prompt_manager.get_order_failure_message(
                        error=result.get("error", "创建订单失败"),
                        product_name=product_name,
                        product_id=product_id,
                        quantity=quantity
                    )
                    return {
                        "executed": False,
                        "error": error_msg,
                        "error_detail": result.get("error", "创建订单失败")
                    }
            except Exception as e:
                return {
                    "executed": False,
                    "error": f"执行购买时出错：{str(e)}"
                }
        
        return None
    
    def _get_conversation_history(self, user_id: int, max_rounds: int = 10) -> list:
        """获取用户的对话历史（最近N轮）"""
        if user_id not in self._conversations:
            return []
        
        history = self._conversations[user_id]
        # 每轮包含2条消息（user + assistant），所以取最后 max_rounds * 2 条
        max_messages = max_rounds * 2
        return history[-max_messages:] if len(history) > max_messages else history
    
    def _save_conversation(self, user_id: int, user_message: str, assistant_reply: str):
        """保存对话历史"""
        if user_id not in self._conversations:
            self._conversations[user_id] = []
        
        # 添加用户消息和助手回复
        self._conversations[user_id].append({"role": "user", "content": user_message})
        self._conversations[user_id].append({"role": "assistant", "content": assistant_reply})
        
        # 限制历史记录为最近10轮（20条消息）
        max_messages = 10 * 2
        if len(self._conversations[user_id]) > max_messages:
            self._conversations[user_id] = self._conversations[user_id][-max_messages:]
    
    def clear_conversation_history(self, user_id: int) -> bool:
        """清空指定用户的对话历史"""
        cleared = False
        if user_id in self._conversations:
            del self._conversations[user_id]
            cleared = True
        # 同时清空待确认的购买信息
        if user_id in self._pending_purchases:
            del self._pending_purchases[user_id]
            cleared = True
        return cleared
    
    def _fallback_chat(self, message: str, user_id: int) -> Dict[str, Any]:
        """降级方案：关键词匹配"""
        message_lower = message.lower()
        
        if "商品" in message or "产品" in message:
            products = product_crud.get_all()
            reply = prompt_manager.get_product_list_message(products)
            return {"reply": f"当前商品列表：\n{reply}", "action_result": None}
        
        elif "订单" in message or "购买" in message:
            if user_id:
                orders = order_crud.filter(buyer_id=user_id)
                if orders:
                    # 构建商品映射
                    products_map = {}
                    for order in orders:
                        if order['product_id'] not in products_map:
                            product = product_crud.get_by_id(order['product_id'])
                            if product:
                                products_map[order['product_id']] = product
                    reply = prompt_manager.get_order_list_message(orders, products_map)
                    return {"reply": reply, "action_result": None}
                return {"reply": "您暂无订单", "action_result": None}
            return {"reply": "请先选择用户", "action_result": None}
        
        elif "用户" in message or "余额" in message:
            if user_id:
                user = user_crud.get_by_id(user_id)
                if user:
                    reply = prompt_manager.get_user_info_message(user)
                    return {"reply": reply, "action_result": None}
            return {"reply": "请先选择用户", "action_result": None}
        
        return {"reply": "我理解您的需求，但需要更多信息。您可以：\n1. 查询商品\n2. 查询订单\n3. 查询用户信息", 
               "action_result": None}


# 单例服务
order_service = OrderService()
agent_service = AgentService()

