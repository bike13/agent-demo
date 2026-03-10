/** 主应用逻辑 */
const API_BASE = '/api';

let currentUserId = null;
let speechInput = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initUserSwitcher();
    initProductForm();
    initBuyForm();
    initChat();
    loadUsers();
});

// 导航切换
function initNavigation() {
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
            btn.classList.add('active');
            const page = btn.dataset.page;
            document.getElementById(`${page}-page`).classList.add('active');
            
            // 加载对应页面数据
            if (page === 'users') loadUsers();
            else if (page === 'products') loadProducts();
            else if (page === 'orders') loadOrders();
        });
    });
}

// 用户切换
async function initUserSwitcher() {
    const select = document.getElementById('userSelect');
    let previousUserId = currentUserId;
    
    select.addEventListener('change', async (e) => {
        const newUserId = e.target.value ? parseInt(e.target.value) : null;
        
        // 如果切换到了不同的用户，清空聊天记录
        if (previousUserId !== newUserId) {
            // 清空前端显示的聊天消息
            clearChatMessages();
            
            // 如果之前有用户，清空后端该用户的对话历史
            if (previousUserId !== null) {
                try {
                    await fetch(`${API_BASE}/agent/clear-history`, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({user_id: previousUserId})
                    });
                } catch (error) {
                    console.error('清空对话历史失败:', error);
                }
            }
        }
        
        currentUserId = newUserId;
        previousUserId = newUserId;
        updateUserInfo();
        
        if (currentUserId) {
            loadUsers();
            loadProducts();
            loadOrders();
        }
    });
}

function clearChatMessages() {
    const messages = document.getElementById('chatMessages');
    if (messages) {
        messages.innerHTML = '';
    }
}

async function loadUsers() {
    try {
        const res = await fetch(`${API_BASE}/users`);
        const users = await res.json();
        
        // 更新用户选择器
        const select = document.getElementById('userSelect');
        select.innerHTML = '<option value="">请选择用户</option>';
        users.forEach(user => {
            const option = document.createElement('option');
            option.value = user.id;
            option.textContent = `${user.username} (${user.role === 'seller' ? '商家' : '买家'})`;
            if (currentUserId === user.id) option.selected = true;
            select.appendChild(option);
        });
        
        // 更新用户列表
        const list = document.getElementById('usersList');
        list.innerHTML = users.map(user => `
            <div class="card">
                <div class="card-header">
                    <div class="card-title">${user.username}</div>
                </div>
                <div class="card-content">
                    <p>角色：${user.role === 'seller' ? '商家' : '买家'}</p>
                    <p>余额：${user.balance.toFixed(2)}</p>
                    <p>创建时间：${user.created_at}</p>
                </div>
            </div>
        `).join('');
        
        updateUserInfo();
    } catch (error) {
        console.error('加载用户失败:', error);
    }
}

function updateUserInfo() {
    const info = document.getElementById('userInfo');
    if (currentUserId) {
        fetch(`${API_BASE}/users/${currentUserId}`)
            .then(res => res.json())
            .then(user => {
                info.textContent = `${user.username} | ${user.role === 'seller' ? '商家' : '买家'} | 余额: ${user.balance.toFixed(2)}`;
            });
    } else {
        info.textContent = '';
    }
}

// 商品管理
async function loadProducts() {
    try {
        const res = await fetch(`${API_BASE}/products`);
        const products = await res.json();
        
        const list = document.getElementById('productsList');
        list.innerHTML = products.map(product => {
            const isSeller = currentUserId && getUserRole() === 'seller';
            return `
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">${product.name}</div>
                        <div>¥${product.price.toFixed(2)} | 库存: ${product.stock}</div>
                    </div>
                    <div class="card-content">
                        <p>${product.description || '无描述'}</p>
                        <p>商家ID: ${product.seller_id}</p>
                    </div>
                    <div class="card-actions">
                        ${isSeller && product.seller_id === currentUserId ? `
                            <button class="btn btn-primary" onclick="editProduct(${product.id})">编辑</button>
                            <button class="btn btn-danger" onclick="deleteProduct(${product.id})">删除</button>
                        ` : getUserRole() === 'buyer' ? `
                            <button class="btn btn-primary" onclick="buyProduct(${product.id})">购买</button>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
    } catch (error) {
        console.error('加载商品失败:', error);
    }
}

function getUserRole() {
    const select = document.getElementById('userSelect');
    const option = select.options[select.selectedIndex];
    if (!option || !option.value) return null;
    return option.textContent.includes('商家') ? 'seller' : 'buyer';
}

function initProductForm() {
    document.getElementById('addProductBtn').addEventListener('click', () => {
        document.getElementById('modalTitle').textContent = '新增商品';
        document.getElementById('productForm').reset();
        document.getElementById('productId').value = '';
        document.getElementById('productModal').classList.add('active');
    });
    
    document.getElementById('productForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('productId').value;
        const data = {
            name: document.getElementById('productName').value,
            description: document.getElementById('productDescription').value,
            price: parseFloat(document.getElementById('productPrice').value),
            stock: parseInt(document.getElementById('productStock').value),
            seller_id: currentUserId
        };
        
        try {
            if (id) {
                await fetch(`${API_BASE}/products/${id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
            } else {
                await fetch(`${API_BASE}/products`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
            }
            closeModal();
            loadProducts();
        } catch (error) {
            alert('操作失败: ' + error.message);
        }
    });
    
    document.querySelector('#productModal .close').addEventListener('click', closeModal);
}

function closeModal() {
    document.getElementById('productModal').classList.remove('active');
}

async function editProduct(id) {
    const res = await fetch(`${API_BASE}/products/${id}`);
    const product = await res.json();
    
    document.getElementById('modalTitle').textContent = '编辑商品';
    document.getElementById('productId').value = product.id;
    document.getElementById('productName').value = product.name;
    document.getElementById('productDescription').value = product.description || '';
    document.getElementById('productPrice').value = product.price;
    document.getElementById('productStock').value = product.stock;
    document.getElementById('productModal').classList.add('active');
}

async function deleteProduct(id) {
    if (!confirm('确定要删除这个商品吗？')) return;
    try {
        await fetch(`${API_BASE}/products/${id}`, {method: 'DELETE'});
        loadProducts();
    } catch (error) {
        alert('删除失败: ' + error.message);
    }
}

// 购买商品
async function buyProduct(productId) {
    if (!currentUserId) {
        alert('请先选择用户');
        return;
    }
    
    const res = await fetch(`${API_BASE}/products/${productId}`);
    const product = await res.json();
    
    document.getElementById('buyProductId').value = productId;
    document.getElementById('buyProductInfo').innerHTML = `
        <p><strong>${product.name}</strong></p>
        <p>单价: ¥${product.price.toFixed(2)}</p>
        <p>库存: ${product.stock}</p>
    `;
    document.getElementById('buyQuantity').value = 1;
    document.getElementById('buyQuantity').max = product.stock;
    updateBuyTotal();
    document.getElementById('buyModal').classList.add('active');
}

function initBuyForm() {
    document.getElementById('buyQuantity').addEventListener('input', updateBuyTotal);
    
    document.getElementById('buyForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const productId = parseInt(document.getElementById('buyProductId').value);
        const quantity = parseInt(document.getElementById('buyQuantity').value);
        
        try {
            const res = await fetch(`${API_BASE}/orders`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    buyer_id: currentUserId,
                    product_id: productId,
                    quantity: quantity
                })
            });
            
            if (res.ok) {
                const order = await res.json();
                alert(`购买成功！订单ID: ${order.id}，总金额: ¥${order.total_amount.toFixed(2)}`);
                closeBuyModal();
                loadProducts();
                loadOrders();
                updateUserInfo();
            } else {
                const error = await res.json();
                alert(error.detail || '购买失败');
            }
        } catch (error) {
            alert('购买失败: ' + error.message);
        }
    });
}

function updateBuyTotal() {
    const productId = document.getElementById('buyProductId').value;
    const quantity = parseInt(document.getElementById('buyQuantity').value) || 0;
    
    if (productId) {
        fetch(`${API_BASE}/products/${productId}`)
            .then(res => res.json())
            .then(product => {
                const total = product.price * quantity;
                document.getElementById('buyTotalAmount').innerHTML = `
                    <p><strong>总金额: ¥${total.toFixed(2)}</strong></p>
                `;
            });
    }
}

function closeBuyModal() {
    document.getElementById('buyModal').classList.remove('active');
}

// 订单管理
async function loadOrders() {
    try {
        const url = currentUserId ? `${API_BASE}/orders?buyer_id=${currentUserId}` : `${API_BASE}/orders`;
        const res = await fetch(url);
        const orders = await res.json();
        
        const list = document.getElementById('ordersList');
        if (orders.length === 0) {
            list.innerHTML = '<p>暂无订单</p>';
            return;
        }
        
        list.innerHTML = orders.map(order => `
            <div class="card">
                <div class="card-header">
                    <div class="card-title">订单 #${order.id}</div>
                </div>
                <div class="card-content">
                    <p>商品ID: ${order.product_id}</p>
                    <p>购买数量: ${order.quantity}</p>
                    <p>总金额: ¥${order.total_amount.toFixed(2)}</p>
                    <p>下单时间: ${order.order_time}</p>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('加载订单失败:', error);
    }
}

// 智能体对话
function initChat() {
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');
    const voiceBtn = document.getElementById('voiceBtn');
    const voiceStatus = document.getElementById('voiceStatus');
    const voiceIcon = document.getElementById('voiceIcon');
    
    // 初始化语音输入
    speechInput = new SpeechInput(chatInput, voiceStatus, voiceIcon);
    voiceBtn.addEventListener('click', () => speechInput.toggle());
    
    // 发送消息
    sendBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;
    
    if (!currentUserId) {
        alert('请先选择用户');
        return;
    }
    
    // 显示用户消息
    addMessage('user', message);
    input.value = '';
    
    try {
        const res = await fetch(`${API_BASE}/agent/chat`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                message: message,
                user_id: currentUserId
            })
        });
        
        const data = await res.json();
        addMessage('agent', data.reply);
        
        // 如果有操作结果，刷新相关页面
        if (data.action_result) {
            // 延迟一下确保后端数据已更新
            setTimeout(() => {
                loadProducts();
                loadOrders();
                updateUserInfo();
            }, 500);
        } else {
            // 检查回复中是否包含购买成功的关键词，也刷新数据
            const purchaseKeywords = ['订单创建成功', '购买成功', '订单ID', '余额更新', '库存更新'];
            if (purchaseKeywords.some(keyword => data.reply.includes(keyword))) {
                setTimeout(() => {
                    loadProducts();
                    loadOrders();
                    updateUserInfo();
                }, 500);
            }
        }
    } catch (error) {
        addMessage('agent', '发送失败: ' + error.message);
    }
}

function addMessage(role, content) {
    const messages = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    // 格式化消息内容，支持换行和基本格式化
    const formattedContent = formatMessage(content);
    
    messageDiv.innerHTML = `
        <div class="message-content">${formattedContent}</div>
        <div class="message-time">${new Date().toLocaleTimeString()}</div>
    `;
    messages.appendChild(messageDiv);
    
    // 平滑滚动到底部
    messages.scrollTo({
        top: messages.scrollHeight,
        behavior: 'smooth'
    });
}

function formatMessage(content) {
    // 转义HTML特殊字符
    let formatted = content
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    
    // 将换行符转换为<br>
    formatted = formatted.replace(/\n/g, '<br>');
    
    // 匹配商品ID格式：ID:数字 或 商品ID:数字，并高亮显示
    formatted = formatted.replace(/(?:商品)?ID[：:]\s*(\d+)/gi, '<span style="background: rgba(102, 126, 234, 0.1); padding: 2px 6px; border-radius: 4px; font-weight: 600; color: #667eea;">商品ID: $1</span>');
    
    // 匹配价格格式：¥数字 或 价格:数字
    formatted = formatted.replace(/[¥￥]\s*(\d+(?:\.\d+)?)/g, '<span style="color: #e74c3c; font-weight: 600;">¥$1</span>');
    formatted = formatted.replace(/价格[：:]\s*(\d+(?:\.\d+)?)/gi, '价格: <span style="color: #e74c3c; font-weight: 600;">$1</span>');
    
    // 匹配库存格式：库存:数字 或 stock:数字
    formatted = formatted.replace(/库存[：:]\s*(\d+)/gi, '库存: <span style="color: #27ae60; font-weight: 500;">$1</span>');
    
    // 匹配数字+单位（如：50件、80个）
    formatted = formatted.replace(/(\d+)\s*(件|个|台|只|条)/g, '<span style="color: #27ae60; font-weight: 500;">$1$2</span>');
    
    // 匹配商品名称（通常在ID后面）
    formatted = formatted.replace(/商品ID:\s*(\d+)\s*[—-]\s*([^，,。.\n]+)/g, 
        '<div style="margin: 4px 0;"><span style="background: rgba(102, 126, 234, 0.1); padding: 2px 6px; border-radius: 4px; font-weight: 600; color: #667eea;">商品ID: $1</span> - <strong>$2</strong></div>');
    
    return formatted;
}

