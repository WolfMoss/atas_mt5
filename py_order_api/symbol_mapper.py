#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import logging

logger = logging.getLogger(__name__)

class SymbolMapper:
    """
    符号映射工具类，用于将外部交易系统的符号映射到MT5内部符号
    支持符号映射和手数比例映射
    """
    
    def __init__(self, config_file='config.json'):
        """
        初始化符号映射器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.symbol_mapping = {}
        self.reverse_mapping = {}
        self.load_mapping()
    
    def load_mapping(self):
        """从配置文件加载符号映射"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    mapping_config = config.get("symbol_mapping", {})
                    
                    # 处理新旧格式兼容性
                    for external_symbol, mapping_info in mapping_config.items():
                        if isinstance(mapping_info, str):
                            # 旧格式：直接字符串映射
                            self.symbol_mapping[external_symbol] = {
                                "symbol": mapping_info,
                                "volume_ratio": 1.0
                            }
                        elif isinstance(mapping_info, dict):
                            # 新格式：包含symbol和volume_ratio
                            self.symbol_mapping[external_symbol] = {
                                "symbol": mapping_info.get("symbol", external_symbol),
                                "volume_ratio": mapping_info.get("volume_ratio", 1.0)
                            }
                    
                    # 创建反向映射（只映射符号，不包括手数）
                    self.reverse_mapping = {}
                    for external_symbol, mapping_info in self.symbol_mapping.items():
                        mt5_symbol = mapping_info["symbol"]
                        if mt5_symbol not in self.reverse_mapping:
                            self.reverse_mapping[mt5_symbol] = external_symbol
                    
                    logger.info(f"已加载 {len(self.symbol_mapping)} 个符号映射关系")
            else:
                logger.warning(f"配置文件 {self.config_file} 不存在，使用空映射")
        except Exception as e:
            logger.error(f"加载符号映射时出错: {str(e)}")
    
    def map_to_mt5(self, external_symbol):
        """
        将外部系统符号映射到MT5内部符号
        
        Args:
            external_symbol: 外部系统符号
            
        Returns:
            str: MT5内部符号，如果没有映射关系则返回原符号
        """
        if external_symbol in self.symbol_mapping:
            mt5_symbol = self.symbol_mapping[external_symbol]["symbol"]
            logger.debug(f"符号映射: {external_symbol} -> {mt5_symbol}")
            return mt5_symbol
        return external_symbol
    
    def get_volume_ratio(self, external_symbol):
        """
        获取手数映射比例
        
        Args:
            external_symbol: 外部系统符号
            
        Returns:
            float: 手数比例，如果没有映射关系则返回1.0
        """
        if external_symbol in self.symbol_mapping:
            volume_ratio = self.symbol_mapping[external_symbol]["volume_ratio"]
            logger.debug(f"手数比例映射: {external_symbol} -> {volume_ratio}")
            return volume_ratio
        return 1.0
    
    def map_volume(self, external_symbol, volume):
        """
        根据映射配置转换手数
        
        Args:
            external_symbol: 外部系统符号
            volume: 原始手数
            
        Returns:
            float: 转换后的手数
        """
        volume_ratio = self.get_volume_ratio(external_symbol)
        mapped_volume = volume * volume_ratio
        logger.debug(f"手数映射: {external_symbol} {volume} -> {mapped_volume} (比例: {volume_ratio})")
        return mapped_volume
    
    def map_from_mt5(self, mt5_symbol):
        """
        将MT5内部符号映射回外部系统符号
        
        Args:
            mt5_symbol: MT5内部符号
            
        Returns:
            str: 外部系统符号，如果没有映射关系则返回原符号
        """
        # 使用配置中的第一个映射
        if mt5_symbol in self.reverse_mapping:
            external_symbol = self.reverse_mapping[mt5_symbol]
            logger.debug(f"反向符号映射: {mt5_symbol} -> {external_symbol}")
            return external_symbol
        return mt5_symbol
    
    def add_mapping(self, external_symbol, mt5_symbol, volume_ratio=1.0, save=True):
        """
        添加新的符号映射关系
        
        Args:
            external_symbol: 外部系统符号
            mt5_symbol: MT5内部符号
            volume_ratio: 手数比例
            save: 是否保存到配置文件
            
        Returns:
            bool: 是否成功添加
        """
        if not external_symbol or not mt5_symbol:
            return False
        
        # 添加映射
        self.symbol_mapping[external_symbol] = {
            "symbol": mt5_symbol,
            "volume_ratio": volume_ratio
        }
        self.reverse_mapping[mt5_symbol] = external_symbol
        
        logger.info(f"添加符号映射: {external_symbol} -> {mt5_symbol}, 手数比例: {volume_ratio}")
        
        # 保存到配置文件
        if save:
            return self.save_mapping()
        
        return True
    
    def remove_mapping(self, external_symbol, save=True):
        """
        删除符号映射关系
        
        Args:
            external_symbol: 外部系统符号
            save: 是否保存到配置文件
            
        Returns:
            bool: 是否成功删除
        """
        if external_symbol in self.symbol_mapping:
            mt5_symbol = self.symbol_mapping[external_symbol]["symbol"]
            del self.symbol_mapping[external_symbol]
            
            if mt5_symbol in self.reverse_mapping:
                del self.reverse_mapping[mt5_symbol]
            
            logger.info(f"删除符号映射: {external_symbol}")
            
            # 保存到配置文件
            if save:
                return self.save_mapping()
            
            return True
        
        return False
    
    def save_mapping(self):
        """保存符号映射到配置文件"""
        try:
            # 读取现有配置
            config = {}
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
            
            # 更新符号映射
            config["symbol_mapping"] = self.symbol_mapping
            
            # 写入配置文件
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
            
            logger.info(f"符号映射已保存到 {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存符号映射时出错: {str(e)}")
            return False
    
    def get_all_mappings(self):
        """获取所有符号映射关系"""
        return self.symbol_mapping
    
    def clear_mappings(self, save=True):
        """
        清除所有符号映射关系
        
        Args:
            save: 是否保存到配置文件
            
        Returns:
            bool: 是否成功清除
        """
        self.symbol_mapping = {}
        self.reverse_mapping = {}
        
        logger.info("已清除所有符号映射")
        
        # 保存到配置文件
        if save:
            return self.save_mapping()
        
        return True


# 单例示例
_instance = None

def get_mapper(config_file='config.json'):
    """获取符号映射器单例"""
    global _instance
    if _instance is None:
        _instance = SymbolMapper(config_file)
    return _instance


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    mapper = get_mapper()
    
    # 测试映射
    test_symbols = [
        "BTCUSDT@BinanceFutures",
        "COMEX Gold",
        "COMEX Gold Futures",
        "EURUSD"
    ]
    
    print("符号映射测试:")
    for symbol in test_symbols:
        mt5_symbol = mapper.map_to_mt5(symbol)
        volume_ratio = mapper.get_volume_ratio(symbol)
        mapped_volume = mapper.map_volume(symbol, 1.0)
        print(f"{symbol} -> {mt5_symbol}, 手数比例: {volume_ratio}, 1手映射为: {mapped_volume}手")
    
    # 添加新映射
    mapper.add_mapping("DOGEUSDT@Binance", "DOGEUSDm", 0.5)
    
    # 测试新映射
    print("\n添加新映射后:")
    print(f"DOGEUSDT@Binance -> {mapper.map_to_mt5('DOGEUSDT@Binance')}, 手数比例: {mapper.get_volume_ratio('DOGEUSDT@Binance')}")
    
    # 测试反向映射
    print("\n反向映射测试:")
    print(f"BTCUSDm -> {mapper.map_from_mt5('BTCUSDm')}")
    print(f"XAUUSD -> {mapper.map_from_mt5('XAUUSD')}")
    
    # 显示所有映射
    print("\n所有映射关系:")
    mappings = mapper.get_all_mappings()
    for external, mapping_info in mappings.items():
        print(f"{external} -> {mapping_info['symbol']}, 手数比例: {mapping_info['volume_ratio']}") 