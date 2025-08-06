#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pybit.unified_trading import HTTP

# 配置日志
logger = logging.getLogger(__name__)

class BybitTrader:
    """Bybit交易类，基于官方pybit库封装"""
    
    def __init__(self, api_key: str = "", secret_key: str = "", testnet: bool = False, demo_trading: bool = False):
        """
        初始化Bybit交易类
        
        Args:
            api_key: Bybit API密钥
            secret_key: Bybit密钥
            testnet: 是否使用测试网络
            demo_trading: 是否使用演示交易（主网演示）
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.testnet = testnet
        self.demo_trading = demo_trading
        self.initialized = False
        
        # 使用pybit官方库
        if demo_trading:
            # 演示交易使用特殊的demo端点
            logger.info("🎭 使用Bybit演示交易服务")
            self.session = HTTP(
                testnet=False,  # 演示交易基于主网
                api_key=api_key,
                api_secret=secret_key,
                demo=True  # 启用演示模式
            )
        else:
            self.session = HTTP(
                testnet=testnet,
                api_key=api_key,
                api_secret=secret_key
            )
    
    def initialize(self) -> bool:
        """
        初始化Bybit连接
        
        Returns:
            bool: 初始化是否成功
        """
        logger.info("正在初始化Bybit连接...")
        
        if not self.api_key or not self.secret_key:
            logger.error("未提供API密钥和密钥")
            return False
        
        try:
            # 测试API连接 - 获取钱包余额
            response = self.session.get_wallet_balance(accountType="UNIFIED")
            
            if response and response.get("retCode") == 0:
                if self.demo_trading:
                    logger.info("✅ Bybit演示交易连接成功！")
                else:
                    logger.info("✅ Bybit连接成功！")
                self.initialized = True
                return True
            else:
                logger.error(f"Bybit连接失败: {response}")
                return False
        except Exception as e:
            logger.error(f"Bybit初始化异常: {str(e)}")
            return False
    
    def is_connected(self) -> bool:
        """
        检查Bybit是否已连接
        
        Returns:
            bool: 连接状态
        """
        return self.initialized
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        获取账户信息
        
        Returns:
            Dict: 账户信息字典
        """
        if not self.is_connected():
            logger.error("Bybit未连接")
            return {}
        
        try:
            response = self.session.get_wallet_balance(accountType="UNIFIED")
            
            if response and response.get("retCode") == 0:
                result = response.get("result", {})
                list_data = result.get("list", [])
                
                if list_data:
                    account = list_data[0]
                    server_name = "Bybit Demo" if self.demo_trading else "Bybit"
                    return {
                        "login": "demo_account" if self.demo_trading else "bybit_account",
                        "server": server_name,
                        "currency": "USDT",
                        "leverage": 1,
                        "balance": float(account.get("totalWalletBalance", "0")),
                        "equity": float(account.get("totalEquity", "0")),
                        "margin": float(account.get("totalMarginBalance", "0")),
                        "margin_free": float(account.get("totalAvailableBalance", "0")),
                        "margin_level": 0,
                        "name": f"{server_name} Account"
                    }
            
            logger.error(f"获取账户信息失败: {response}")
            return {}
            
        except Exception as e:
            logger.error(f"获取账户信息异常: {str(e)}")
            return {}
    
    def calculate_sl_by_percentage(self, symbol: str, order_type: str, entry_price: float, 
                                  percentage: float = 10.0) -> float:
        """
        根据百分比计算止损价格
        
        Args:
            symbol: 交易品种
            order_type: 订单类型，"BUY"或"SELL"
            entry_price: 开仓价格
            percentage: 止损百分比，默认10%
            
        Returns:
            float: 止损价格
        """
        try:
            # 获取品种信息
            response = self.session.get_instruments_info(category="linear", symbol=symbol)
            
            if response and response.get("retCode") == 0:
                result = response.get("result", {})
                list_data = result.get("list", [])
                
                if list_data:
                    instrument = list_data[0]
                    tick_size = float(instrument.get("tickSize", "0.01"))
                    
                    # 计算止损距离
                    sl_distance = entry_price * (percentage / 100.0)
                    
                    # 根据订单类型计算止损价格
                    if order_type.upper() == "BUY":
                        sl_price = entry_price - sl_distance
                    else:  # SELL
                        sl_price = entry_price + sl_distance
                    
                    # 四舍五入到合适的精度
                    sl_price = round(sl_price / tick_size) * tick_size
                    
                    logger.info(f"止损计算: 品种={symbol}, 类型={order_type}, 开仓价={entry_price}, "
                               f"止损百分比={percentage}%, 止损价={sl_price}")
                    
                    return sl_price
            
            logger.error(f"无法获取品种信息: {symbol}")
            return 0.0
            
        except Exception as e:
            logger.error(f"计算止损价格时出错: {e}")
            return 0.0
    
    def open_position(self, symbol: str, order_type: str, volume: float,
                     price: float = 0.0, sl: float = 0.0, tp: float = 0.0,
                     profit_amount: float = 0.0, deviation: int = 20, 
                     comment: str = "") -> Optional[Dict]:
        """
        开仓函数
        
        Args:
            symbol: 交易品种，如"BTCUSDT"
            order_type: 订单类型，"BUY"或"SELL"（也可以通过volume正负数判断）
            volume: 交易量，正数=做多(Buy)，负数=做空(Sell)
            price: 价格，0表示市价
            sl: 止损价格，0表示不设置
            tp: 止盈价格，0表示不设置
            profit_amount: 目标盈利金额（美元），0表示不设置
            deviation: 允许的最大价格偏差（点数）
            comment: 订单注释
            
        Returns:
            Dict: 订单发送结果
        """
        if not self.is_connected():
            logger.error("Bybit未连接")
            return None
        
        try:
            # 获取品种信息以检查最小交易量
            instrument_response = self.session.get_instruments_info(category="linear", symbol=symbol)
            
            if not instrument_response or instrument_response.get("retCode") != 0:
                logger.error(f"获取品种信息失败: {instrument_response}")
                return None
            
            instrument_result = instrument_response.get("result", {})
            instrument_list = instrument_result.get("list", [])
            
            if not instrument_list:
                logger.error(f"无法获取品种信息: {symbol}")
                return None
            
            instrument = instrument_list[0]
            min_order_qty = float(instrument.get("minOrderQty", "0.001"))
            qty_step = float(instrument.get("qtyStep", "0.001"))
            
            # 根据交易量的正负数判断买卖方向
            if volume > 0:
                side = "Buy"
                actual_volume = volume
                actual_order_type = "BUY"
            elif volume < 0:
                side = "Sell"
                actual_volume = abs(volume)  # 取绝对值作为实际交易量
                actual_order_type = "SELL"
            else:
                logger.error("交易量不能为0")
                return None
            
            # 检查最小交易量
            if actual_volume < min_order_qty:
                logger.warning(f"交易量 {actual_volume} 小于最小值 {min_order_qty}，调整为最小值")
                actual_volume = min_order_qty
            
            # 调整交易量到合适的步长
            actual_volume = round(actual_volume / qty_step) * qty_step
            

            
            # 获取当前价格
            ticker_response = self.session.get_tickers(category="linear", symbol=symbol)
            
            if not ticker_response or ticker_response.get("retCode") != 0:
                logger.error(f"获取价格信息失败: {ticker_response}")
                return None
            
            result = ticker_response.get("result", {})
            list_data = result.get("list", [])
            
            if not list_data:
                logger.error(f"无法获取价格信息: {symbol}")
                return None
            
            ticker = list_data[0]
            current_price = float(ticker.get("lastPrice", "0"))
            
            # 如果价格为0，使用当前市价
            if price == 0:
                price = current_price
            
            # 如果指定了盈利金额，计算止盈价格
            if profit_amount > 0:
                # 简化计算：假设每点价值为1美元
                tp_distance = profit_amount / actual_volume
                if actual_order_type == "BUY":
                    tp = price + tp_distance
                else:  # SELL
                    tp = price - tp_distance
                logger.info(f"基于盈利金额 ${profit_amount:.2f} 计算的止盈价格: {tp:.5f}")
            
            # 如果没有设置止损，自动设置10%止损
            if sl == 0:
                sl = self.calculate_sl_by_percentage(symbol, actual_order_type, price, 10.0)
                logger.info(f"自动设置10%止损价格: {sl:.5f}")
            
            # 准备订单参数
            order_params = {
                "category": "linear",
                "symbol": symbol,
                "side": side,
                "orderType": "Market",
                "qty": str(actual_volume),
            }
            
            logger.info(f"订单详情: 原始量={volume}, 方向={side}({actual_order_type}), 实际量={actual_volume}")
            logger.info(f"品种信息: 最小量={min_order_qty}, 步长={qty_step}")
            
            # 添加止损止盈（可选）
            if sl > 0:
                order_params["stopLoss"] = str(sl)
            if tp > 0:
                order_params["takeProfit"] = str(tp)
            
            # 发送订单
            logger.info(f"正在发送订单: {order_params}")
            
            try:
                response = self.session.place_order(**order_params)
            except Exception as api_error:
                # 如果是余额不足或其他API错误，尝试无止损止盈的订单
                logger.warning(f"带止损止盈的订单失败: {api_error}")
                logger.info("尝试发送无止损止盈的订单...")
                
                simple_params = {
                    "category": "linear",
                    "symbol": symbol,
                    "side": side,
                    "orderType": "Market",
                    "qty": str(actual_volume),
                }
                
                response = self.session.place_order(**simple_params)
            
            if response and response.get("retCode") == 0:
                result = response.get("result", {})
                order_id = result.get("orderId", "")
                logger.info(f"订单发送成功，订单号: {order_id}")
                
                return {
                    "retcode": 0,  # 模拟MT5的成功码
                    "order": order_id,
                    "price": price,
                    "comment": "Success"
                }
            else:
                error_msg = response.get("retMsg", "未知错误") if response else "请求失败"
                logger.error(f"订单发送失败: {error_msg}")
                
                return {
                    "retcode": 10001,  # 模拟MT5的错误码
                    "comment": error_msg
                }
                
        except Exception as e:
            logger.error(f"开仓处理异常: {str(e)}")
            return {
                "retcode": 10001,
                "comment": f"开仓异常: {str(e)}"
            }
    
    def close_position_by_ticket(self, ticket: str) -> bool:
        """
        通过持仓票据关闭单个持仓（Bybit使用orderId）
        
        Args:
            ticket: 订单ID
            
        Returns:
            bool: 是否成功关闭
        """
        if not self.is_connected():
            logger.error("Bybit未连接")
            return False
        
        try:
            # 获取持仓信息 - 对于linear类别需要提供settleCoin
            positions_response = self.session.get_positions(
                category="linear",
                settleCoin="USDT"  # 线性合约使用USDT结算
            )
            
            if not positions_response or positions_response.get("retCode") != 0:
                logger.error(f"获取持仓信息失败: {positions_response}")
                return False
            
            result = positions_response.get("result", {})
            list_data = result.get("list", [])
            
            # 查找对应的持仓
            target_position = None
            for position in list_data:
                if str(position.get("positionIdx", "")) == str(ticket):
                    target_position = position
                    break
            
            if not target_position:
                logger.error(f"未找到持仓: {ticket}")
                return False
            
            # 准备平仓参数
            symbol = target_position.get("symbol", "")
            side = "Sell" if target_position.get("side") == "Buy" else "Buy"
            qty = target_position.get("size", "0")
            
            order_params = {
                "category": "linear",
                "symbol": symbol,
                "side": side,
                "orderType": "Market",
                "qty": qty,
                "reduceOnly": True
            }
            
            # 发送平仓订单
            logger.info(f"正在关闭持仓: {order_params}")
            response = self.session.place_order(**order_params)
            
            if response and response.get("retCode") == 0:
                logger.info(f"成功关闭持仓，持仓票据: {ticket}")
                return True
            else:
                error_msg = response.get("retMsg", "未知错误") if response else "请求失败"
                logger.error(f"关闭持仓失败: {error_msg}")
                return False
                
        except Exception as e:
            logger.error(f"关闭持仓异常: {str(e)}")
            return False
    
    def close_positions_by_symbol(self, symbol: str) -> bool:
        """
        关闭指定交易品种的所有持仓
        
        Args:
            symbol: 交易品种
            
        Returns:
            bool: 是否成功关闭所有持仓
        """
        if not self.is_connected():
            logger.error("Bybit未连接")
            return False
        
        try:
            # 获取该品种的所有持仓
            response = self.session.get_positions(category="linear", symbol=symbol)
            
            if not response or response.get("retCode") != 0:
                logger.error(f"获取持仓信息失败: {response}")
                return False
            
            result = response.get("result", {})
            list_data = result.get("list", [])
            
            if not list_data:
                logger.warning(f"没有找到持仓，品种: {symbol}")
                return True  # 没有持仓也算成功
            
            # 依次关闭每个持仓
            all_closed = True
            for position in list_data:
                position_idx = position.get("positionIdx", "")
                if not self.close_position_by_ticket(position_idx):
                    all_closed = False
            
            return all_closed
            
        except Exception as e:
            logger.error(f"关闭品种持仓异常: {str(e)}")
            return False
    
    def close_all_positions(self) -> bool:
        """
        关闭所有持仓
        
        Returns:
            bool: 是否成功关闭所有持仓
        """
        if not self.is_connected():
            logger.error("Bybit未连接")
            return False
        
        try:
            # 获取所有持仓 - 对于linear类别需要提供settleCoin
            response = self.session.get_positions(
                category="linear",
                settleCoin="USDT"  # 线性合约使用USDT结算
            )
            
            if not response or response.get("retCode") != 0:
                logger.error(f"获取持仓信息失败: {response}")
                return False
            
            result = response.get("result", {})
            list_data = result.get("list", [])
            
            if not list_data:
                logger.warning("没有找到任何持仓")
                return True  # 没有持仓也算成功
            
            # 依次关闭每个持仓
            all_closed = True
            for position in list_data:
                position_idx = position.get("positionIdx", "")
                if not self.close_position_by_ticket(position_idx):
                    all_closed = False
            
            return all_closed
            
        except Exception as e:
            logger.error(f"关闭所有持仓异常: {str(e)}")
            return False
    
    def get_positions(self, symbol: str = "") -> List[Dict[str, Any]]:
        """
        获取当前持仓信息
        
        Args:
            symbol: 交易品种，为空则获取所有持仓
            
        Returns:
            List[Dict]: 持仓信息列表
        """
        if not self.is_connected():
            logger.error("Bybit未连接")
            return []
        
        try:
            if symbol:
                # 如果指定了具体品种
                params = {"category": "linear", "symbol": symbol}
            else:
                # 如果要获取所有持仓，使用settleCoin参数
                params = {"category": "linear", "settleCoin": "USDT"}
            
            response = self.session.get_positions(**params)
            
            if not response or response.get("retCode") != 0:
                logger.error(f"获取持仓信息失败: {response}")
                return []
            
            result = response.get("result", {})
            list_data = result.get("list", [])
            
            # 转换为字典列表
            positions = []
            for position in list_data:
                # 只返回有持仓的数据
                size = float(position.get("size", "0"))
                if size > 0:
                    position_dict = {
                        "ticket": position.get("positionIdx", ""),
                        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        "type": "BUY" if position.get("side") == "Buy" else "SELL",
                        "volume": size,
                        "symbol": position.get("symbol", ""),
                        "price_open": float(position.get("avgPrice", "0")),
                        "price_current": float(position.get("markPrice", "0")),
                        "sl": float(position.get("stopLoss", "0")),
                        "tp": float(position.get("takeProfit", "0")),
                        "profit": float(position.get("unrealisedPnl", "0")),
                        "swap": 0.0,
                        "comment": position.get("positionIdx", "")
                    }
                    positions.append(position_dict)
            
            return positions
            
        except Exception as e:
            logger.error(f"获取持仓信息异常: {str(e)}")
            return []
    
    def shutdown(self) -> None:
        """关闭Bybit连接"""
        if self.initialized:
            logger.info("正在关闭Bybit连接...")
            self.initialized = False 