#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import json
import websockets
import uuid

class BybitTestClient:
    """Bybit WebSocket测试客户端"""
    
    def __init__(self, uri="ws://localhost:8766"):
        self.uri = uri
        self.websocket = None
    
    async def connect(self):
        """连接到WebSocket服务器"""
        try:
            self.websocket = await websockets.connect(self.uri)
            print(f"已连接到 {self.uri}")
            return True
        except Exception as e:
            print(f"连接失败: {e}")
            return False
    
    async def send_request(self, action, params=None):
        """发送请求"""
        if not self.websocket:
            print("未连接到服务器")
            return None
        
        request = {
            "action": action,
            "params": params or {},
            "id": str(uuid.uuid4())
        }
        
        try:
            await self.websocket.send(json.dumps(request))
            response = await self.websocket.recv()
            return json.loads(response)
        except Exception as e:
            print(f"请求失败: {e}")
            return None
    
    async def test_health_check(self):
        """测试健康检查"""
        print("\n=== 测试健康检查 ===")
        response = await self.send_request("health_check")
        print(f"响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
    
    async def test_get_account_info(self):
        """测试获取账户信息"""
        print("\n=== 测试获取账户信息 ===")
        response = await self.send_request("get_account_info")
        print(f"响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
    
    async def test_get_symbol_mappings(self):
        """测试获取符号映射"""
        print("\n=== 测试获取符号映射 ===")
        response = await self.send_request("get_symbol_mappings")
        print(f"响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
    
    async def test_open_position(self):
        """测试开仓"""
        print("\n=== 测试开仓 ===")
        params = {
            "symbol": "BTCUSDT@BinanceFutures",
            "volume": 0.01,
            "order_type": "BUY",
            "profit_amount": 0
        }
        response = await self.send_request("open_position", params)
        print(f"响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
        return response
    
    async def test_get_positions(self):
        """测试获取持仓"""
        print("\n=== 测试获取持仓 ===")
        response = await self.send_request("get_positions")
        print(f"响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
    
    async def test_close_all_positions(self):
        """测试关闭所有持仓"""
        print("\n=== 测试关闭所有持仓 ===")
        response = await self.send_request("close_all_positions")
        print(f"响应: {json.dumps(response, indent=2, ensure_ascii=False)}")
    
    async def run_tests(self):
        """运行所有测试"""
        if not await self.connect():
            return
        
        try:
            # 测试基本功能
            await self.test_health_check()
            await self.test_get_account_info()
            
            # 测试交易功能
            await self.test_open_position()
            await self.test_get_positions()
            
            # 等待用户确认是否关闭持仓
            user_input = input("\n是否关闭所有持仓？(y/n): ")
            if user_input.lower() == 'y':
                await self.test_close_all_positions()
            
        except KeyboardInterrupt:
            print("\n测试被中断")
        finally:
            if self.websocket:
                await self.websocket.close()
                print("已断开连接")

async def main():
    """主函数"""
    print("Bybit WebSocket测试客户端")
    print("=" * 50)
    
    client = BybitTestClient()
    await client.run_tests()

if __name__ == "__main__":
    asyncio.run(main()) 