"""MCP服务器 - 提供电商操作工具"""
try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = None
    print("警告: fastmcp 未安装，MCP服务器功能不可用")

from .crud import user_crud, product_crud, order_crud
from .services import order_service
from .models import OrderCreate
from .prompts import prompt_manager
from typing import Optional

if FastMCP is None:
    print("MCP服务器需要安装 fastmcp: pip install fastmcp")
    exit(1)

# 创建MCP服务器
mcp = FastMCP(
    name="ecommerce_agent_tools",
    dependencies=[],
    host="127.0.0.1",
    port=9003
)


@mcp.tool(description="创建订单，购买商品。需要提供买家ID、商品ID和购买数量。")
def create_order(buyer_id: int, product_id: int, quantity: int) -> str:
    """
    创建订单并完成购买
    
    Args:
        buyer_id: 买家用户ID
        product_id: 商品ID
        quantity: 购买数量
    
    Returns:
        订单创建结果的详细信息
    """
    try:
        order_data = OrderCreate(
            buyer_id=buyer_id,
            product_id=product_id,
            quantity=quantity
        )
        result = order_service.create_order(order_data)
        
        if result.get("success"):
            order = order_crud.get_by_id(result["order_id"])
            product = product_crud.get_by_id(product_id)
            buyer = user_crud.get_by_id(buyer_id)
            
            # 使用统一的提示词管理器
            return prompt_manager.get_order_success_message(
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
        else:
            # 获取商品信息用于错误提示
            product = product_crud.get_by_id(product_id)
            product_name = product['name'] if product else None
            
            return prompt_manager.get_order_failure_message(
                error=result.get('error', '未知错误'),
                product_name=product_name,
                product_id=product_id,
                quantity=quantity
            )
    except Exception as e:
        return prompt_manager.get_error_message(str(e), "创建订单")


@mcp.tool(description="查询商品信息，可以通过商品ID或商品名称查询。")
def query_product(product_id: Optional[int] = None, product_name: Optional[str] = None) -> str:
    """
    查询商品信息
    
    Args:
        product_id: 商品ID（可选）
        product_name: 商品名称（可选，支持模糊匹配）
    
    Returns:
        商品详细信息
    """
    try:
        if product_id:
            product = product_crud.get_by_id(product_id)
            if product:
                return prompt_manager.get_product_query_message(product)
            else:
                return f"未找到ID为 {product_id} 的商品"
        elif product_name:
            products = product_crud.get_all()
            matched = [p for p in products if product_name.lower() in p['name'].lower()]
            if matched:
                result = "找到以下商品：\n\n"
                for p in matched:
                    result += f"商品ID: {p['id']} - {p['name']} - ¥{p['price']:.2f} - 库存:{p['stock']}件\n"
                return result
            else:
                return f"未找到名称包含 '{product_name}' 的商品"
        else:
            return "请提供商品ID或商品名称"
    except Exception as e:
        return prompt_manager.get_error_message(str(e), "查询商品")


@mcp.tool(description="查询用户的所有订单信息")
def query_orders(buyer_id: int) -> str:
    """
    查询用户的订单列表
    
    Args:
        buyer_id: 买家用户ID
    
    Returns:
        订单列表信息
    """
    try:
        orders = order_crud.filter(buyer_id=buyer_id)
        if not orders:
            return "您暂无订单"
        
        # 构建商品映射
        products_map = {}
        for order in orders:
            if order['product_id'] not in products_map:
                product = product_crud.get_by_id(order['product_id'])
                if product:
                    products_map[order['product_id']] = product
        
        return prompt_manager.get_order_list_message(orders, products_map)
    except Exception as e:
        return prompt_manager.get_error_message(str(e), "查询订单")


@mcp.tool(description="查询用户信息，包括用户名、角色和余额")
def query_user(user_id: int) -> str:
    """
    查询用户信息
    
    Args:
        user_id: 用户ID
    
    Returns:
        用户详细信息
    """
    try:
        user = user_crud.get_by_id(user_id)
        if user:
            return prompt_manager.get_user_info_message(user)
        else:
            return f"未找到ID为 {user_id} 的用户"
    except Exception as e:
        return prompt_manager.get_error_message(str(e), "查询用户")


@mcp.tool(description="列出所有商品")
def list_products() -> str:
    """
    列出所有商品
    
    Returns:
        所有商品的列表
    """
    try:
        products = product_crud.get_all()
        return prompt_manager.get_product_list_message(products)
    except Exception as e:
        return prompt_manager.get_error_message(str(e), "查询商品列表")


if __name__ == "__main__":
    print("启动电商智能体MCP服务器...")
    print("可用工具:")
    print("1. create_order - 创建订单")
    print("2. query_product - 查询商品")
    print("3. query_orders - 查询订单")
    print("4. query_user - 查询用户")
    print("5. list_products - 列出所有商品")
    print(f"服务器地址: http://127.0.0.1:9003/sse")
    
    mcp.run(
        transport="sse",
    )

