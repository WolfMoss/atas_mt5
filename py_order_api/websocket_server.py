#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import json
import logging
import os
import sys
import websockets
import MetaTrader5 as mt5
from mt5_trader import MT5Trader
from symbol_mapper import get_mapper

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 保存所有已连接的WebSocket客户端
connected_clients = set()

# 加载配置
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    logger.error("配置文件不存在！")
    config = {
        "mt5_path": "",
        "server": "",
        "login": 0,
        "password": "",
        "symbol_mapping": {}
    }

# 获取符号映射配置
symbol_mapper = get_mapper()

# 初始化MT5交易者
trader = None

def initialize_mt5():
    """初始化MT5连接"""
    global trader
    
    logger.info("=" * 50)
    logger.info("开始初始化MT5连接")
    
    # 从配置获取MT5路径（可选）
    mt5_path = config.get("mt5_path", "")
    
    # 如果配置的是程序文件名（非完整路径），则清空路径让MT5自动连接
    if mt5_path and not os.path.isabs(mt5_path):
        logger.info(f"检测到程序文件名配置: {mt5_path}，将尝试连接到已运行的MT5")
        mt5_path = ""  # 清空路径，让MT5库自动连接
    
    if mt5_path:
        logger.info(f"使用配置的MT5路径: {mt5_path}")
    else:
        logger.info("未配置MT5路径，将连接到已运行的MT5终端")
        logger.info("请确保MT5终端已手动启动并登录")
    
    trader = MT5Trader(
        mt5_path=mt5_path,
        server=config.get("server", ""),
        login=config.get("login", 0),
        password=config.get("password", "")
    )
    
    try:
        success = trader.initialize()
        if success:
            logger.info("✓ MT5连接成功！")
            logger.info("=" * 50)
            return True
        else:
            logger.error("❌ MT5连接失败")
            logger.error("解决方案:")
            logger.error("1. 请手动启动MT5终端")
            logger.error("2. 确保MT5已登录到正确的账户")
            logger.error("3. 检查config.json中的账户配置是否正确")
            logger.error("4. 如果MT5安装在特殊位置，请在config.json中配置完整路径")
            logger.error("=" * 50)
            return False
    except Exception as e:
        logger.exception(f"MT5初始化过程中发生异常: {str(e)}")
        logger.error("=" * 50)
        return False

async def handle_message(websocket, message):
    """处理从客户端接收到的消息"""
    try:
        data = json.loads(message)
        action = data.get('action')
        params = data.get('params', {})
        
        response = {'id': data.get('id'), 'status': 'error', 'message': '未知操作'}
        
        # 根据操作类型执行相应的功能
        if action == 'health_check':
            response = await health_check(params)
        elif action == 'get_account_info':
            response = await get_account_info(params)
        elif action == 'open_position':
            response = await open_position(params)
        elif action == 'close_position_by_ticket':
            response = await close_position_by_ticket(params)
        elif action == 'close_positions_by_symbol':
            response = await close_positions_by_symbol(params)
        elif action == 'close_all_positions':
            response = await close_all_positions(params)
        elif action == 'get_positions':
            response = await get_positions(params)
        elif action == 'get_symbol_mappings':
            response = await get_symbol_mappings(params)
        elif action == 'add_symbol_mapping':
            response = await add_symbol_mapping(params)
        elif action == 'remove_symbol_mapping':
            response = await remove_symbol_mapping(params)
        else:
            response = {'status': 'error', 'message': f'未知操作: {action}'}
        
        # 添加请求ID到响应中，方便客户端匹配请求和响应
        if 'id' in data:
            response['id'] = data['id']
        
        await websocket.send(json.dumps(response, ensure_ascii=False))
    except json.JSONDecodeError:
        await websocket.send(json.dumps({
            'status': 'error',
            'message': '无效的JSON格式'
        }, ensure_ascii=False))
    except Exception as e:
        logger.exception(f"处理消息时发生异常: {str(e)}")
        await websocket.send(json.dumps({
            'status': 'error',
            'message': f'处理请求时发生错误: {str(e)}'
        }, ensure_ascii=False))

async def health_check(params):
    """健康检查接口"""
    if trader and trader.is_connected():
        return {'status': 'success', 'message': '服务正常运行'}
    else:
        return {'status': 'error', 'message': 'MT5连接异常'}

async def get_account_info(params):
    """获取账户信息"""
    if not trader or not trader.is_connected():
        return {'status': 'error', 'message': 'MT5未连接'}
    
    try:
        account_info = trader.get_account_info()
        if account_info:
            return {'status': 'success', 'data': account_info}
        else:
            return {'status': 'error', 'message': '获取账户信息失败'}
    
    except Exception as e:
        error_message = f"获取账户信息异常: {str(e)}"
        logger.exception(error_message)
        return {'status': 'error', 'message': error_message}

async def open_position(params):
    """开仓接口"""
    if not trader or not trader.is_connected():
        return {'status': 'error', 'message': 'MT5未连接'}

    try:
        # 获取参数
        external_symbol = params.get('symbol')
        if not external_symbol:
            return {'status': 'error', 'message': '缺少必要参数: symbol'}

        # 映射符号
        symbol = symbol_mapper.map_to_mt5(external_symbol)
        
        # 获取原始交易量并进行手数映射
        original_volume = float(params.get('volume', 0))
        volume = symbol_mapper.map_volume(external_symbol, original_volume)
        
        order_type = params.get('order_type', '').upper()  # 'BUY' 或 'SELL'

        price = 0
        sl = 0
        tp = 0
        profit_amount = float(params.get('profit_amount', 0))  # 新增：目标盈利金额
        deviation = 100  # 设置默认偏差为100点
        
        # 检查必要参数
        if not original_volume or not order_type:
            return {'status': 'error', 'message': '缺少必要参数: volume 或 order_type'}
        
        # 可选参数
        comment = params.get('comment', "WebSocket API")
        
        volume_ratio = symbol_mapper.get_volume_ratio(external_symbol)
        logger.info(f"开始处理开仓请求: 品种={symbol}(原始={external_symbol}), 类型={order_type}")
        logger.info(f"交易量映射: 原始={original_volume} -> MT5={volume} (手数比例={volume_ratio})")
        if profit_amount > 0:
            logger.info(f"设置目标盈利金额: ${profit_amount}")
        
        # 创建一个新的线程来执行MT5的交易操作
        loop = asyncio.get_running_loop()
        # 在线程池中执行MT5交易操作，设置90秒超时
        result = await asyncio.wait_for(
            loop.run_in_executor(None, lambda: trader.open_position(
                symbol=symbol,
                order_type=order_type,
                volume=volume,
                price=price,
                sl=sl,
                tp=tp,
                profit_amount=profit_amount,  # 传递盈利金额参数
                deviation=deviation,
                comment=comment
            )),
            timeout=90
        )
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"开仓成功: 品种={symbol}, 订单号={result.order}, 价格={result.price}")
            return {
                'status': 'success',
                'message': '开仓成功',
                'data': {
                    'ticket': result.order,
                    'volume': volume,
                    'price': result.price,
                    'symbol': symbol,
                    'type': order_type,
                    'profit_amount_target': profit_amount if profit_amount > 0 else None
                }
            }
        else:
            error_code = result.retcode if result else 'Unknown'
            error_message = f"开仓失败，错误码: {error_code}"
            if result and hasattr(result, 'comment'):
                error_message += f", 错误信息: {result.comment}"
            logger.error(error_message)
            return {'status': 'error', 'message': error_message}
    
    except asyncio.TimeoutError:
        error_message = f"开仓操作超时，可能是MT5处理时间过长，请检查MT5终端"
        logger.error(error_message)
        return {'status': 'error', 'message': error_message}
            
    except Exception as e:
        error_message = f"开仓处理异常: {str(e)}"
        logger.exception(error_message)
        return {'status': 'error', 'message': error_message}

async def close_position_by_ticket(params):
    """通过持仓票据关闭单个持仓"""
    if not trader or not trader.is_connected():
        return {'status': 'error', 'message': 'MT5未连接'}
    
    try:
        ticket = int(params.get('ticket', 0))
        if not ticket:
            return {'status': 'error', 'message': '缺少必要参数: ticket'}
        
        result = trader.close_position_by_ticket(ticket)
        
        if result:
            return {'status': 'success', 'message': '关仓成功'}
        else:
            error_message = "关仓失败"
            logger.error(error_message)
            return {'status': 'error', 'message': error_message}
            
    except Exception as e:
        error_message = f"关仓处理异常: {str(e)}"
        logger.exception(error_message)
        return {'status': 'error', 'message': error_message}

async def close_positions_by_symbol(params):
    """通过交易品种关闭所有相关持仓"""
    if not trader or not trader.is_connected():
        return {'status': 'error', 'message': 'MT5未连接'}
    
    try:
        external_symbol = params.get('symbol')
        if not external_symbol:
            return {'status': 'error', 'message': '缺少必要参数: symbol'}
        
        # 映射符号
        symbol = symbol_mapper.map_to_mt5(external_symbol)
        
        logger.info(f"正在关闭品种持仓: {symbol}(原始={external_symbol})")
        result = trader.close_positions_by_symbol(symbol)
        
        if result:
            return {'status': 'success', 'message': '关仓成功'}
        else:
            error_message = "关仓失败"
            logger.error(error_message)
            return {'status': 'error', 'message': error_message}
            
    except Exception as e:
        error_message = f"关仓处理异常: {str(e)}"
        logger.exception(error_message)
        return {'status': 'error', 'message': error_message}

async def close_all_positions(params):
    """关闭所有持仓"""
    if not trader or not trader.is_connected():
        return {'status': 'error', 'message': 'MT5未连接'}
    
    try:
        result = trader.close_all_positions()
        
        if result:
            return {'status': 'success', 'message': '所有持仓已关闭'}
        else:
            error_message = "关闭所有持仓失败"
            logger.error(error_message)
            return {'status': 'error', 'message': error_message}
            
    except Exception as e:
        error_message = f"关闭所有持仓异常: {str(e)}"
        logger.exception(error_message)
        return {'status': 'error', 'message': error_message}

async def get_positions(params):
    """获取持仓信息"""
    if not trader or not trader.is_connected():
        return {'status': 'error', 'message': 'MT5未连接'}
    
    try:
        external_symbol = params.get('symbol', '')
        
        # 如果指定了品种，则进行映射
        symbol = ''
        if external_symbol:
            symbol = symbol_mapper.map_to_mt5(external_symbol)
            logger.info(f"获取持仓信息: {symbol}(原始={external_symbol})")
        else:
            logger.info("获取所有持仓信息")
        
        positions = trader.get_positions(symbol)
        
        # 进行反向映射，将MT5符号映射回外部系统符号
        if positions and isinstance(positions, list):
            for position in positions:
                if 'symbol' in position:
                    mt5_symbol = position['symbol']
                    position['original_symbol'] = symbol_mapper.map_from_mt5(mt5_symbol)
        
        return {'status': 'success', 'data': positions}
            
    except Exception as e:
        error_message = f"获取持仓信息异常: {str(e)}"
        logger.exception(error_message)
        return {'status': 'error', 'message': error_message}

async def websocket_handler(websocket):
    """WebSocket连接处理函数"""
    client_address = websocket.remote_address
    logger.info(f"新客户端连接: {client_address}")
    
    # 将新连接的客户端添加到集合中
    connected_clients.add(websocket)
    
    try:
        # 发送欢迎消息
        await websocket.send(json.dumps({
            'status': 'success',
            'message': '已连接到MT5 WebSocket服务',
            'mt5_connected': trader and trader.is_connected()
        }, ensure_ascii=False))
        
        # 持续监听客户端消息
        async for message in websocket:
            await handle_message(websocket, message)
    
    except websockets.exceptions.ConnectionClosed:
        logger.info(f"客户端断开连接: {client_address}")
    except Exception as e:
        logger.exception(f"处理WebSocket连接时发生异常: {str(e)}")
    finally:
        # 从集合中移除断开连接的客户端
        connected_clients.remove(websocket)

async def broadcast_message(message):
    """向所有连接的客户端广播消息"""
    if not connected_clients:
        return
    
    # 创建要广播的消息
    broadcast_data = json.dumps(message, ensure_ascii=False)
    
    # 向所有客户端发送消息
    await asyncio.gather(
        *[client.send(broadcast_data) for client in connected_clients],
        return_exceptions=True
    )

async def start_server():
    """启动WebSocket服务器"""
    # 初始化MT5连接
    initialize_mt5()
    
    # 开始定期任务，如广播价格更新等
    asyncio.create_task(periodic_tasks())
    
    # 启动WebSocket服务器
    host = "0.0.0.0"
    port = 8766
    
    # 设置WebSocket服务器选项，增加ping超时时间
    server_options = {
        "ping_interval": 60,      # 60秒发送一次ping
        "ping_timeout": 180,      # 180秒超时
        "max_size": 10 * 1024 * 1024,  # 最大消息大小10MB
        "max_queue": 1024,        # 最大队列大小
        "close_timeout": 60       # 关闭超时时间
    }
    
    logger.info(f"启动WebSocket服务器 ws://{host}:{port}")
    
    server = await websockets.serve(
        websocket_handler, 
        host, 
        port, 
        **server_options
    )
    await asyncio.Future()  # 持续运行直到被中断

async def periodic_tasks():
    """定期执行的任务，如检查MT5连接状态、广播行情数据等"""
    while True:
        try:
            # 检查MT5连接状态
            if trader and trader.is_connected():
                # 可以在这里添加定期广播的数据，如行情更新等
                pass
            else:
                # 如果MT5连接断开，尝试重新连接
                if trader:
                    logger.warning("MT5连接已断开，尝试重新连接...")
                    trader.initialize()
        except Exception as e:
            logger.exception(f"执行定期任务时出错: {str(e)}")
        
        # 每30秒执行一次
        await asyncio.sleep(30)

async def get_symbol_mappings(params):
    """获取所有符号映射关系"""
    try:
        mappings = symbol_mapper.get_all_mappings()
        return {'status': 'success', 'data': mappings}
    except Exception as e:
        error_message = f"获取符号映射关系异常: {str(e)}"
        logger.exception(error_message)
        return {'status': 'error', 'message': error_message}

async def add_symbol_mapping(params):
    """添加符号映射关系"""
    try:
        external_symbol = params.get('external_symbol')
        mt5_symbol = params.get('mt5_symbol')
        volume_ratio = float(params.get('volume_ratio', 1.0))  # 新增手数比例参数
        
        if not external_symbol or not mt5_symbol:
            return {'status': 'error', 'message': '缺少必要参数: external_symbol 或 mt5_symbol'}
        
        result = symbol_mapper.add_mapping(external_symbol, mt5_symbol, volume_ratio)
        if result:
            return {'status': 'success', 'message': f'成功添加符号映射: {external_symbol} -> {mt5_symbol}, 手数比例: {volume_ratio}'}
        else:
            return {'status': 'error', 'message': '添加符号映射失败'}
    except Exception as e:
        error_message = f"添加符号映射异常: {str(e)}"
        logger.exception(error_message)
        return {'status': 'error', 'message': error_message}

async def remove_symbol_mapping(params):
    """删除符号映射关系"""
    try:
        external_symbol = params.get('external_symbol')
        
        if not external_symbol:
            return {'status': 'error', 'message': '缺少必要参数: external_symbol'}
        
        result = symbol_mapper.remove_mapping(external_symbol)
        if result:
            return {'status': 'success', 'message': f'成功删除符号映射: {external_symbol}'}
        else:
            return {'status': 'error', 'message': f'删除符号映射失败，可能符号不存在: {external_symbol}'}
    except Exception as e:
        error_message = f"删除符号映射异常: {str(e)}"
        logger.exception(error_message)
        return {'status': 'error', 'message': error_message}

if __name__ == "__main__":

    
    try:


        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("服务器关闭中...")
        if trader:
            trader.shutdown()
        logger.info("服务器已关闭") 
        a = input("回车退出")