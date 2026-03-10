"""提示词统一管理模块"""
from typing import Dict, Any, List


class PromptManager:
    """提示词管理器"""
    
    @staticmethod
    def get_system_prompt(
        users: List[Dict[str, Any]],
        products: List[Dict[str, Any]],
        user_id: int,
        current_user: Dict[str, Any] = None,
        orders: List[Dict[str, Any]] = None
    ) -> str:
        """
        获取系统提示词
        
        Args:
            users: 用户列表
            products: 商品列表
            user_id: 当前用户ID
            current_user: 当前用户信息
            orders: 当前用户的订单列表
        
        Returns:
            系统提示词
        """
        orders = orders or []
        current_user_info = current_user or {}
        
        return f"""你是一个电商智能助手，可以帮助用户查询信息、购买商品等。

当前系统状态：
- 用户列表：{users}
- 商品列表：{products}
- 当前用户ID：{user_id}
- 当前用户信息：{current_user_info}
- 当前用户的订单：{orders}

你可以执行以下操作：
1. 查询商品信息（使用商品ID或名称）
2. 查询用户信息
3. 查询订单信息
4. 购买商品（需要提供商品ID和数量）

重要：当用户要购买商品时，你需要：
1. 从对话历史中识别商品ID和数量
2. 如果商品名称提到但不知道ID，从商品列表中查找匹配的商品
3. 如果数量未明确，默认为1
4. 然后调用 create_order 函数来真正创建订单

请根据用户的请求，理解意图并给出合适的回复。

**重要提示**：
1. 当用户要购买商品时，系统会自动处理购买确认流程，你只需要正常回复即可
2. 如果用户确认购买（回复"确认"、"是的"、"好的"等），系统会自动执行购买
3. 如果用户取消购买（回复"取消"、"不要"等），系统会自动取消
4. 你只需要理解用户意图并给出友好的回复，不需要直接执行购买操作
"""
    
    @staticmethod
    def get_order_success_message(
        order_id: int,
        product_name: str,
        product_id: int,
        quantity: int,
        total_amount: float,
        old_balance: float,
        new_balance: float,
        old_stock: int,
        new_stock: int
    ) -> str:
        """
        获取订单创建成功的消息模板
        
        Args:
            order_id: 订单ID
            product_name: 商品名称
            product_id: 商品ID
            quantity: 购买数量
            total_amount: 总金额
            old_balance: 原余额
            new_balance: 新余额
            old_stock: 原库存
            new_stock: 新库存
        
        Returns:
            订单成功消息
        """
        return f"""订单创建成功！

**订单信息**：
- 订单ID: {order_id}
- 商品: {product_name} (ID:{product_id})
- 数量: {quantity}件
- 金额: ¥{total_amount:.2f}
- 状态: 已创建

**用户余额更新**：
- 您的余额从 ¥{old_balance:.2f} 减少至 ¥{new_balance:.2f}

**商品库存更新**：
- {product_name} (ID:{product_id}) 库存从 {old_stock}件 减少至 {new_stock}件

您可以通过"查询订单信息"操作查看该订单详情。"""
    
    @staticmethod
    def get_order_failure_message(error: str, product_name: str = None, product_id: int = None, quantity: int = None) -> str:
        """
        获取订单创建失败的消息模板
        
        Args:
            error: 错误信息
            product_name: 商品名称（可选）
            product_id: 商品ID（可选）
            quantity: 购买数量（可选）
        
        Returns:
            订单失败消息
        """
        base_msg = "❌ 购买失败"
        
        if product_name:
            base_msg += f"\n\n**商品信息**：\n- 商品：{product_name}"
            if product_id:
                base_msg += f" (ID:{product_id})"
            if quantity:
                base_msg += f"\n- 数量：{quantity}件"
        
        base_msg += f"\n\n**失败原因**：\n{error}"
        base_msg += "\n\n请检查后重试，或联系客服获取帮助。"
        
        return base_msg
    
    @staticmethod
    def get_purchase_confirmation_message(
        product_name: str,
        product_id: int,
        quantity: int,
        price: float,
        total_amount: float,
        current_balance: float
    ) -> str:
        """
        获取购买确认消息模板
        
        Args:
            product_name: 商品名称
            product_id: 商品ID
            quantity: 购买数量
            price: 单价
            total_amount: 总金额
            current_balance: 当前余额
        
        Returns:
            购买确认消息
        """
        return f"""📦 购买确认

**商品信息**：
- 商品：{product_name} (ID:{product_id})
- 单价：¥{price:.2f}
- 数量：{quantity}件
- 总金额：¥{total_amount:.2f}

**账户信息**：
- 当前余额：¥{current_balance:.2f}
- 购买后余额：¥{current_balance - total_amount:.2f}

请确认是否购买？
- 回复"确认"、"是的"、"好的"等来确认购买
- 回复"取消"、"不要"等来取消购买"""
    
    @staticmethod
    def get_product_query_message(product: Dict[str, Any]) -> str:
        """
        获取商品查询结果消息模板
        
        Args:
            product: 商品信息字典
        
        Returns:
            商品信息消息
        """
        return f"""商品ID: {product['id']}
商品名称: {product['name']}
描述: {product.get('description', '无描述')}
价格: ¥{product['price']:.2f}
库存: {product['stock']}件
商家ID: {product['seller_id']}"""
    
    @staticmethod
    def get_product_list_message(products: List[Dict[str, Any]]) -> str:
        """
        获取商品列表消息模板
        
        Args:
            products: 商品列表
        
        Returns:
            商品列表消息
        """
        if not products:
            return "暂无商品"
        
        result = f"共有 {len(products)} 个商品：\n\n"
        for p in products:
            result += f"商品ID: {p['id']} - {p['name']} - ¥{p['price']:.2f} - 库存:{p['stock']}件\n"
        return result
    
    @staticmethod
    def get_order_list_message(orders: List[Dict[str, Any]], products_map: Dict[int, Dict[str, Any]]) -> str:
        """
        获取订单列表消息模板
        
        Args:
            orders: 订单列表
            products_map: 商品ID到商品信息的映射
        
        Returns:
            订单列表消息
        """
        if not orders:
            return "您暂无订单"
        
        result = f"您共有 {len(orders)} 个订单：\n\n"
        for order in orders:
            product = products_map.get(order['product_id'], {})
            product_name = product.get('name', '未知商品') if product else '未知商品'
            result += f"""订单ID: {order['id']}
- 商品: {product_name} (ID:{order['product_id']})
- 数量: {order['quantity']}件
- 金额: ¥{order['total_amount']:.2f}
- 下单时间: {order['order_time']}
---
"""
        return result
    
    @staticmethod
    def get_user_info_message(user: Dict[str, Any]) -> str:
        """
        获取用户信息消息模板
        
        Args:
            user: 用户信息字典
        
        Returns:
            用户信息消息
        """
        role_name = "商家" if user['role'] == 'seller' else "买家"
        return f"""用户ID: {user['id']}
用户名: {user['username']}
角色: {role_name}
余额: ¥{user['balance']:.2f}
创建时间: {user['created_at']}"""
    
    @staticmethod
    def get_error_message(error: str, context: str = "") -> str:
        """
        获取错误消息模板
        
        Args:
            error: 错误信息
            context: 上下文信息
        
        Returns:
            错误消息
        """
        if context:
            return f"{context}时出错：{error}"
        return f"操作失败：{error}"


# 创建单例实例
prompt_manager = PromptManager()

