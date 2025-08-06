#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import json
import websockets
import sys
import uuid
import time

# WebSocket服务器地址
WS_URI = "ws://localhost:8766"  # 更新为新的端口

# 重连配置
MAX_RECONNECT_ATTEMPTS = 5
RECONNECT_DELAY = 3  # 秒

async def send_request(websocket, action, params=None):
    """发送请求并等待响应"""
    if params is None:
        params = {}
    
    # 生成唯一的请求ID
    request_id = str(uuid.uuid4())
    
    # 创建请求数据
    request_data = {
        'id': request_id,
        'action': action,
        'params': params
    }
    
    try:
        # 发送请求
        await websocket.send(json.dumps(request_data))
        print(f"\n已发送 {action} 请求: {json.dumps(params)}")
        
        # 等待响应，设置超时时间为120秒
        response = await asyncio.wait_for(websocket.recv(), timeout=120)
        response_data = json.loads(response)
        
        # 格式化输出
        print(f"收到响应: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        
        return response_data
    except asyncio.TimeoutError:
        print("等待响应超时，请检查服务器状态或MT5终端")
        raise
    except websockets.exceptions.ConnectionClosed as e:
        print(f"连接已关闭: {e}")
        raise
    except Exception as e:
        print(f"发送请求时出错: {e}")
        raise

async def connect_with_retry():
    """尝试连接WebSocket服务器，有重试机制"""
    reconnect_attempt = 0
    
    while reconnect_attempt < MAX_RECONNECT_ATTEMPTS:
        try:
            return await websockets.connect(WS_URI, ping_interval=30, ping_timeout=120)
        except (ConnectionRefusedError, OSError) as e:
            reconnect_attempt += 1
            wait_time = RECONNECT_DELAY * reconnect_attempt
            print(f"连接失败: {e}. 正在尝试重连 ({reconnect_attempt}/{MAX_RECONNECT_ATTEMPTS})，等待 {wait_time} 秒...")
            await asyncio.sleep(wait_time)
    
    raise ConnectionError(f"无法连接到服务器，已尝试 {MAX_RECONNECT_ATTEMPTS} 次")

async def client_handler():
    """WebSocket客户端处理函数"""
    websocket = None
    try:
        print(f"正在连接WebSocket服务器: {WS_URI}")
        websocket = await connect_with_retry()
        
        # 接收欢迎消息
        welcome = await websocket.recv()
        print(f"服务器欢迎消息: {welcome}")
        
        # 命令处理循环
        while True:
            print("\n===== MT5 WebSocket客户端 =====")
            print("1. 健康检查")
            print("2. 获取账户信息")
            print("3. 获取持仓信息")
            print("4. 开仓")
            print("5. 按票据号关仓")
            print("6. 按交易品种关仓")
            print("7. 关闭所有持仓")
            print("0. 退出")
            
            try:
                choice = input("\n请选择操作 (0-7): ")
                
                if choice == '0':
                    print("正在退出...")
                    break
                
                elif choice == '1':
                    # 健康检查
                    await send_request(websocket, 'health_check')
                
                elif choice == '2':
                    # 获取账户信息
                    await send_request(websocket, 'get_account_info')
                
                elif choice == '3':
                    # 获取持仓信息
                    symbol = input("请输入交易品种(留空获取所有持仓): ")
                    params = {'symbol': symbol} if symbol else {}
                    await send_request(websocket, 'get_positions', params)
                
                elif choice == '4':
                    # 开仓
                    symbol = input("请输入交易品种(如EURUSD): ")
                    volume = input("请输入交易量(如0.1): ")
                    order_type = input("请输入订单类型(BUY/SELL): ")
                    
                    # 新增：选择止盈方式
                    print("\n请选择止盈方式:")
                    print("1. 按价格设置止盈")
                    print("2. 按盈利金额设置止盈")
                    print("3. 不设置止盈")
                    tp_choice = input("请选择(1-3): ")
                    
                    params = {
                        'symbol': symbol,
                        'volume': float(volume),
                        'order_type': order_type
                    }
                    
                    if tp_choice == '1':
                        # 按价格设置止盈
                        tp = input("请输入止盈价格: ")
                        if tp:
                            params['tp'] = float(tp)
                    elif tp_choice == '2':
                        # 按盈利金额设置止盈
                        profit_amount = input("请输入目标盈利金额(美元): ")
                        if profit_amount:
                            params['profit_amount'] = float(profit_amount)
                    
                    # 止损设置
                    sl = input("请输入止损价格(0表示不设置): ")
                    if sl and float(sl) > 0:
                        params['sl'] = float(sl)
                    
                    print("开仓请求处理中，这可能需要几秒钟时间...")    
                    await send_request(websocket, 'open_position', params)
                
                elif choice == '5':
                    # 按票据号关仓
                    ticket = input("请输入持仓票据号: ")
                    params = {'ticket': int(ticket)}
                    await send_request(websocket, 'close_position_by_ticket', params)
                
                elif choice == '6':
                    # 按交易品种关仓
                    symbol = input("请输入交易品种: ")
                    params = {'symbol': symbol}
                    await send_request(websocket, 'close_positions_by_symbol', params)
                
                elif choice == '7':
                    # 关闭所有持仓
                    confirm = input("确定要关闭所有持仓吗? (y/n): ")
                    if confirm.lower() == 'y':
                        await send_request(websocket, 'close_all_positions')
                
                else:
                    print("无效的选择，请重试。")
            
            except ValueError as e:
                print(f"输入错误: {str(e)}")
            except (websockets.exceptions.ConnectionClosed, ConnectionResetError) as e:
                print(f"连接已关闭，尝试重新连接: {str(e)}")
                # 尝试重新连接
                websocket = await connect_with_retry()
                print("已重新连接到服务器")
            except Exception as e:
                print(f"操作失败: {str(e)}")
    
    except websockets.exceptions.ConnectionClosed:
        print("与服务器的连接已关闭")
    except ConnectionRefusedError:
        print(f"无法连接到服务器，请确保服务器已启动: {WS_URI}")
    except ConnectionError as e:
        print(f"连接错误: {str(e)}")
    except Exception as e:
        print(f"出现异常: {str(e)}")
    finally:
        # 确保连接正确关闭
        if websocket and websocket.open:
            try:
                await websocket.close()
            except:
                pass

if __name__ == "__main__":
    try:
        asyncio.run(client_handler())
    except KeyboardInterrupt:
        print("\n程序已中断")
        sys.exit(0) 