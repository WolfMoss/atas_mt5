import MetaTrader5 as mt5
import logging
import time
from datetime import datetime
from typing import Union, Dict, List, Any, Optional

# 配置日志
logger = logging.getLogger(__name__)

class MT5Trader:
    """MetaTrader 5交易类，封装MT5交易相关功能"""
    
    def __init__(self, mt5_path: str = "", server: str = "", login: int = 0, password: str = ""):
        """
        初始化MT5交易类
        
        Args:
            mt5_path: MT5安装路径，为空则使用默认路径
            server: 交易服务器名称
            login: 账号
            password: 密码
        """
        self.mt5_path = mt5_path
        self.server = server
        self.login = login
        self.password = password
        self.initialized = False
    
    def initialize(self) -> bool:
        """
        初始化MT5连接
        
        Returns:
            bool: 初始化是否成功
        """
        logger.info("正在初始化MT5连接...")
        
        # 首先检查是否已有MT5终端在运行
        terminal_info = mt5.terminal_info()
        if terminal_info is not None:
            logger.info("检测到MT5终端已在运行")
            # 如果需要登录到不同的账户，先断开当前连接
            if self.login and self.password:
                current_account = mt5.account_info()
                if current_account and current_account.login != self.login:
                    logger.info(f"当前登录账户 {current_account.login}，需要切换到 {self.login}")
                    mt5.shutdown()
                    terminal_info = None
        
        # 如果没有运行的MT5终端，尝试初始化
        if terminal_info is None:
            # 如果指定了路径，使用指定路径启动
            if self.mt5_path:
                logger.info(f"使用指定路径启动MT5: {self.mt5_path}")
                initialize_result = mt5.initialize(path=self.mt5_path)
            else:
                # 不指定路径，尝试连接到默认位置或已运行的MT5
                logger.info("尝试连接到默认MT5或已运行的终端")
                initialize_result = mt5.initialize()
                
            if not initialize_result:
                error_code = mt5.last_error()
                logger.error(f"MT5初始化失败，错误码: {error_code}")
                
                # 给出更详细的错误提示
                if error_code == (-10004,):  # 无法找到MT5终端
                    logger.error("解决方案:")
                    logger.error("1. 请手动启动MT5终端")
                    logger.error("2. 或在config.json中配置正确的mt5_path")
                    logger.error("3. 确保MT5已正确安装")
                elif error_code == (-10001,):  # 网络错误
                    logger.error("网络连接问题，请检查网络设置")
                
                return False
        
        # 验证连接是否成功
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            logger.error("MT5连接验证失败")
            return False
        
        logger.info(f"MT5终端信息: {terminal_info.name}, 构建: {terminal_info.build}")
        
        # 如果提供了登录信息，则进行登录
        if self.login and self.password:
            logger.info(f"正在登录账户: {self.login}")
            login_result = mt5.login(
                login=self.login,
                password=self.password,
                server=self.server
            )
            
            if not login_result:
                error_code = mt5.last_error()
                logger.error(f"MT5登录失败，错误码: {error_code}")
                logger.error(f"登录信息: 账户={self.login}, 服务器={self.server}")
                
                # 不完全关闭连接，保持MT5终端运行
                # mt5.shutdown()  # 注释掉这行，让用户可以手动操作
                return False
            
            # 验证登录结果
            account_info = mt5.account_info()
            if account_info:
                logger.info(f"登录成功: 账户={account_info.login}, 服务器={account_info.server}")
                logger.info(f"账户余额: {account_info.balance} {account_info.currency}")
            else:
                logger.warning("登录可能成功但无法获取账户信息")
        else:
            logger.info("未提供登录信息，使用当前MT5终端的登录状态")
            account_info = mt5.account_info()
            if account_info:
                logger.info(f"当前账户: {account_info.login}, 服务器: {account_info.server}")
            else:
                logger.warning("MT5终端可能未登录任何账户")
        
        logger.info(f"MT5初始化成功，版本: {mt5.version()}")
        self.initialized = True
        return True
    
    def is_connected(self) -> bool:
        """
        检查MT5是否已连接
        
        Returns:
            bool: 连接状态
        """
        return self.initialized and mt5.terminal_info() is not None
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        获取账户信息
        
        Returns:
            Dict: 账户信息字典
        """
        if not self.is_connected():
            logger.error("MT5未连接")
            return {}
        
        account_info = mt5.account_info()
        if not account_info:
            logger.error(f"获取账户信息失败，错误码: {mt5.last_error()}")
            return {}
        
        # 转换为字典
        return {
            "login": account_info.login,
            "server": account_info.server,
            "currency": account_info.currency,
            "leverage": account_info.leverage,
            "balance": account_info.balance,
            "equity": account_info.equity,
            "margin": account_info.margin,
            "margin_free": account_info.margin_free,
            "margin_level": account_info.margin_level,
            "margin_so_mode": account_info.margin_so_mode,
            "margin_so_call": account_info.margin_so_call,
            "margin_so_so": account_info.margin_so_so,
            "margin_initial": account_info.margin_initial,
            "margin_maintenance": account_info.margin_maintenance,
            "assets": account_info.assets,
            "liabilities": account_info.liabilities,
            "commission_blocked": account_info.commission_blocked,
            "name": account_info.name,
            "trade_mode": account_info.trade_mode,
            "limit_orders": account_info.limit_orders
        }
    
    def calculate_tp_by_profit_amount(self, symbol: str, order_type: str, volume: float, 
                                     entry_price: float, profit_amount: float) -> float:
        """
        根据盈利金额计算止盈价格
        
        Args:
            symbol: 交易品种
            order_type: 订单类型，"BUY"或"SELL"
            volume: 交易量
            entry_price: 开仓价格
            profit_amount: 目标盈利金额
            
        Returns:
            float: 止盈价格，如果计算失败返回0
        """
        try:
            # 获取交易品种信息
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                logger.error(f"无法获取交易品种信息: {symbol}")
                return 0.0
            
            # 获取当前价格信息
            tick_info = mt5.symbol_info_tick(symbol)
            if tick_info is None:
                logger.error(f"无法获取价格信息: {symbol}")
                return 0.0
            
            # 计算每点价值
            tick_value = symbol_info.trade_tick_value
            tick_size = symbol_info.trade_tick_size
            
            if tick_value == 0 or tick_size == 0:
                logger.error(f"无法获取有效的点值信息: tick_value={tick_value}, tick_size={tick_size}")
                return 0.0
            
            # 简化计算: 每个tick的实际价值
            value_per_tick = tick_value * volume
            
            # 需要的tick数量
            ticks_needed = profit_amount / value_per_tick
            
            # 计算止盈价格
            if order_type.upper() == "BUY":
                # 买入时，止盈价格 = 开仓价格 + (tick数量 * tick大小)
                tp_price = entry_price + (ticks_needed * tick_size)
            else:  # SELL
                # 卖出时，止盈价格 = 开仓价格 - (tick数量 * tick大小)
                tp_price = entry_price - (ticks_needed * tick_size)
            
            # 检查止盈价格是否符合最小距离要求
            stops_level = symbol_info.trade_stops_level
            min_distance = stops_level * symbol_info.point
            
            if order_type.upper() == "BUY":
                # 买入止盈必须高于当前价格至少 min_distance
                min_tp_price = entry_price + min_distance
                if tp_price < min_tp_price:
                    logger.warning(f"计算的止盈价格 {tp_price:.5f} 太接近开仓价格，调整为最小允许距离 {min_tp_price:.5f}")
                    tp_price = min_tp_price
            else:  # SELL
                # 卖出止盈必须低于当前价格至少 min_distance
                max_tp_price = entry_price - min_distance
                if tp_price > max_tp_price:
                    logger.warning(f"计算的止盈价格 {tp_price:.5f} 太接近开仓价格，调整为最小允许距离 {max_tp_price:.5f}")
                    tp_price = max_tp_price
            
            # 四舍五入到合适的小数位数
            tp_price = round(tp_price, symbol_info.digits)
            
            logger.info(f"盈利金额计算: 品种={symbol}, 类型={order_type}, 开仓价={entry_price:.5f}, "
                       f"目标盈利=${profit_amount:.2f}, 止盈价={tp_price:.5f}, "
                       f"最小距离={min_distance:.5f} (stops_level={stops_level})")
            
            return tp_price
            
        except Exception as e:
            logger.error(f"计算止盈价格时出错: {e}")
            return 0.0

    def get_supported_filling_mode(self, symbol: str) -> int:
        """
        获取交易品种支持的订单填充模式
        
        Args:
            symbol: 交易品种
            
        Returns:
            int: 支持的填充模式
        """
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.warning(f"无法获取品种 {symbol} 信息，使用默认填充模式")
            return mt5.ORDER_FILLING_IOC
        
        # 检查支持的填充模式
        filling_mode = symbol_info.filling_mode
        
        # 按优先级检查支持的填充模式
        # 注意：这里需要检查symbol_info.filling_mode的位标志
        # 1 = FOK, 2 = IOC, 4 = RETURN
        if filling_mode & 2:  # IOC模式
            logger.debug(f"品种 {symbol} 支持 IOC 填充模式")
            return mt5.ORDER_FILLING_IOC
        elif filling_mode & 1:  # FOK模式
            logger.debug(f"品种 {symbol} 支持 FOK 填充模式")
            return mt5.ORDER_FILLING_FOK
        else:  # 默认使用RETURN模式
            logger.debug(f"品种 {symbol} 使用默认 RETURN 填充模式")
            return mt5.ORDER_FILLING_RETURN

    def open_position(self, symbol: str, order_type: str, volume: float,
                     price: float = 0.0, sl: float = 0.0, tp: float = 0.0,
                     profit_amount: float = 0.0, deviation: int = 20, 
                     comment: str = "") -> Optional[mt5.OrderSendResult]:
        """
        开仓函数
        
        Args:
            symbol: 交易品种，如"EURUSD"
            order_type: 订单类型，"BUY"或"SELL"
            volume: 交易量
            price: 价格，0表示市价
            sl: 止损价格，0表示不设置
            tp: 止盈价格，0表示不设置
            profit_amount: 目标盈利金额（美元），0表示不设置，优先级高于tp
            deviation: 允许的最大价格偏差（点数）
            comment: 订单注释
            
        Returns:
            OrderSendResult: 订单发送结果对象
        """
        # 获取交易品种信息
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            logger.error(f"交易品种 {symbol} 不存在")
            return None
        
        # 打印品种详细信息（用于调试）
        logger.info(f"交易品种信息: {symbol}")
        logger.info(f"  - 最小交易量: {symbol_info.volume_min}")
        logger.info(f"  - 最大交易量: {symbol_info.volume_max}")
        logger.info(f"  - 交易量步长: {symbol_info.volume_step}")
        logger.info(f"  - 小数位数: {symbol_info.digits}")
        logger.info(f"  - 点大小: {symbol_info.point}")
        logger.info(f"  - 止损止盈级别: {symbol_info.trade_stops_level}")
        logger.info(f"  - Tick价值: {symbol_info.trade_tick_value}")
        logger.info(f"  - Tick大小: {symbol_info.trade_tick_size}")
        
        # 如果该品种在行情中不可见，则添加
        if not symbol_info.visible:
            logger.info(f"添加交易品种 {symbol} 到行情窗口")
            if not mt5.symbol_select(symbol, True):
                logger.error(f"添加交易品种 {symbol} 失败")
                return None

        if volume<0:
            volume=volume*-1


        
        # 确定订单类型
        if order_type == "BUY":
            order_direction = mt5.ORDER_TYPE_BUY
            current_price = mt5.symbol_info_tick(symbol).ask
        elif order_type == "SELL":
            order_direction = mt5.ORDER_TYPE_SELL
            current_price = mt5.symbol_info_tick(symbol).bid
        else:
            logger.error(f"未知订单类型: {order_type}")
            return None
        
        # 如果价格为0，则使用当前市场价格
        if price == 0:
            price = current_price
        
        # 如果指定了盈利金额，则计算止盈价格
        if profit_amount > 0:
            calculated_tp = self.calculate_tp_by_profit_amount(
                symbol, order_type, volume, price, profit_amount
            )
            if calculated_tp > 0:
                tp = calculated_tp
                logger.info(f"基于盈利金额 ${profit_amount:.2f} 计算的止盈价格: {tp:.5f}")
            else:
                logger.warning("无法计算止盈价格，将不设置止盈")
                tp = 0.0
        
        # 获取支持的填充模式
        filling_type = self.get_supported_filling_mode(symbol)
        
        # 准备订单请求
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),  # 确保是浮点数
            "type": order_direction,
            "price": float(price),    # 确保是浮点数
            "sl": float(sl) if sl > 0 else 0.0,  # 设置止损
            "tp": float(tp) if tp > 0 else 0.0,  # 设置止盈
            "deviation": int(deviation),  # 确保是整数
            "magic": 123456,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_type,  # 使用智能检测的填充模式
        }
        
        # 发送订单
        logger.info(f"正在发送订单: {request}")
        result = mt5.order_send(request)
        
        if result is None:
            error_code = mt5.last_error()
            logger.error(f"订单发送失败，返回None，错误码: {error_code}")
            return None
        elif result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"订单发送失败，错误码: {result.retcode}, 说明: {result.comment}")
        else:
            logger.info(f"订单发送成功，订单号: {result.order}")
        
        return result
    
    def close_position_by_ticket(self, ticket: int) -> bool:
        """
        通过持仓票据关闭单个持仓
        
        Args:
            ticket: 持仓票据号
            
        Returns:
            bool: 是否成功关闭
        """
        # if not self.is_connected():
        #     logger.error("MT5未连接")
        #     return False
        
        # 获取持仓信息
        positions = mt5.positions_get(ticket=ticket)
        if not positions:
            logger.error(f"获取持仓失败，持仓票据: {ticket}, 错误码: {mt5.last_error()}")
            return False
        
        position = positions[0]
        
        # 获取持仓符号信息
        symbol = position.symbol
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            logger.error(f"获取交易品种信息失败，品种: {symbol}")
            return False
        
        # 如果该品种在行情中不可见，则添加
        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)
        
        # 准备平仓请求
        # 如果是买入持仓，则需要卖出平仓；如果是卖出持仓，则需要买入平仓
        deal_type = mt5.ORDER_TYPE_SELL if position.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if position.type == mt5.POSITION_TYPE_BUY else mt5.symbol_info_tick(symbol).ask
        
        # 获取支持的填充模式
        filling_type = self.get_supported_filling_mode(symbol)
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": position.volume,
            "type": deal_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 123456,
            "comment": "关闭持仓",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_type,  # 使用智能检测的填充模式
        }
        
        # 发送订单
        logger.info(f"正在关闭持仓: {request}")
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"关闭持仓失败，错误码: {result.retcode}, 说明: {result.comment}")
            return False
        else:
            logger.info(f"成功关闭持仓，持仓票据: {ticket}")
            return True
    
    def close_positions_by_symbol(self, symbol: str) -> bool:
        """
        关闭指定交易品种的所有持仓
        
        Args:
            symbol: 交易品种
            
        Returns:
            bool: 是否成功关闭所有持仓
        """
        if not self.is_connected():
            logger.error("MT5未连接")
            return False
        
        # 获取该品种的所有持仓
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            logger.warning(f"没有找到持仓，品种: {symbol}")
            return True  # 没有持仓也算成功
        
        # 依次关闭每个持仓
        all_closed = True
        for position in positions:
            if not self.close_position_by_ticket(position.ticket):
                all_closed = False
        
        return all_closed
    
    def close_all_positions(self) -> bool:
        """
        关闭所有持仓
        
        Returns:
            bool: 是否成功关闭所有持仓
        """
        if not self.is_connected():
            logger.error("MT5未连接")
            return False
        
        # 获取所有持仓
        positions = mt5.positions_get()
        if not positions:
            logger.warning("没有找到任何持仓")
            return True  # 没有持仓也算成功
        
        # 依次关闭每个持仓
        all_closed = True
        for position in positions:
            if not self.close_position_by_ticket(position.ticket):
                all_closed = False
        
        return all_closed
    
    def get_positions(self, symbol: str = "") -> List[Dict[str, Any]]:
        """
        获取当前持仓信息
        
        Args:
            symbol: 交易品种，为空则获取所有持仓
            
        Returns:
            List[Dict]: 持仓信息列表
        """
        if not self.is_connected():
            logger.error("MT5未连接")
            return []
        
        # 获取持仓
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
        
        if not positions:
            return []
        
        # 转换为字典列表
        result = []
        for position in positions:
            position_dict = {
                "ticket": position.ticket,
                "time": datetime.fromtimestamp(position.time).strftime('%Y-%m-%d %H:%M:%S'),
                "type": "BUY" if position.type == mt5.POSITION_TYPE_BUY else "SELL",
                "volume": position.volume,
                "symbol": position.symbol,
                "price_open": position.price_open,
                "price_current": position.price_current,
                "sl": position.sl,
                "tp": position.tp,
                "profit": position.profit,
                "swap": position.swap,
                "comment": position.comment
            }
            result.append(position_dict)
        
        return result
    
    def shutdown(self) -> None:
        """关闭MT5连接"""
        if self.initialized:
            logger.info("正在关闭MT5连接...")
            mt5.shutdown()
            self.initialized = False 