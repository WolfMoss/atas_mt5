using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using ATAS.DataFeedsCore;
using ATAS.Strategies.Chart;

namespace ATASOrderLogStrategy
{
    public class OrderTradeRecorder : ChartStrategy
    {
        private readonly string _logFilePath = @"C:\Users\Administrator\Documents\ATASLogs\TradeLog.txt";
        private Dictionary<string, decimal> _position = new Dictionary<string, decimal>();
        private MT5WebSocketClient _MT5WebSocketClient = new MT5WebSocketClient();
        private bool _isInitialized = false;
        private bool _disposed = false;

        public OrderTradeRecorder()
        {
            try
            {
                // 确保日志目录存在
                Directory.CreateDirectory(Path.GetDirectoryName(_logFilePath));
                File.AppendAllText(_logFilePath, "监听开始\n");
                

            }
            catch (Exception ex)
            {
                File.AppendAllText(_logFilePath, "报错:"+ ex.Message+"\n");
            }
        }

        protected override void OnStarted()
        {
            // 异步初始化
            _ = InitializeAsync();
        }



        private async Task InitializeAsync()
        {
            try
            {
                File.AppendAllText(_logFilePath, "开始初始化WebSocket连接\n");
                
                // 异步连接WebSocket
                bool connected = await _MT5WebSocketClient.Connect();
                
                if (connected)
                {
                    // 异步发送请求
                    bool requestSent = await _MT5WebSocketClient.SendRequest("get_account_info", new object());
                    
                    if (requestSent)
                    {
                        _isInitialized = true;
                        File.AppendAllText(_logFilePath, "WebSocket初始化完成\n");
                    }
                    else
                    {
                        File.AppendAllText(_logFilePath, "发送账户信息请求失败\n");
                    }
                }
                else
                {
                    File.AppendAllText(_logFilePath, "WebSocket连接失败\n");
                }
            }
            catch (Exception ex)
            {
                File.AppendAllText(_logFilePath, "WebSocket初始化报错: " + ex.Message + "\n");

            }
        }

        //protected override void OnNewOrder(Order order)
        //{
        //    base.OnNewOrder(order);
        //    if (!myorders.Contains(order.Id))
        //    {
        //        myorders.Add(order.Id);
        //    }
 
        //    string logEntry = $"{DateTime.Now}: 下单New Order - ID: {order.Id}, Price: {order.Price}, 触发价格: {order.TriggerPrice},未成交量: {order.Unfilled}, 成交量: {order.QuantityToFill}, Direction: {order.Direction}, State: {order.State}, WasActive: {order.WasActive}, Canceled: {order.Canceled}\n";
        //    File.AppendAllText(_logFilePath, logEntry);
        //}

        //protected override void OnNewMyTrade(MyTrade myTrade)
        //{
        //    base.OnNewMyTrade(myTrade);
        //    if (myorders.Contains(myTrade.Id))
        //    {
        //        File.AppendAllText(_logFilePath, $"成交{DateTime.Now}: New Trade - ID: {myTrade.Id},New Trade - ID: {myTrade.AccountID}, Price: {myTrade.Price}, Volume: {myTrade.Volume}, Direction: {myTrade.OrderDirection}\n");
        //    }

        //    //string logEntry = $"{DateTime.Now}: New Trade - ID: {myTrade.Id},New Trade - ID: {myTrade.AccountID}, Price: {myTrade.Price}, Volume: {myTrade.Volume}, Direction: {myTrade.OrderDirection}\n";
        //    //File.AppendAllText(_logFilePath, logEntry);

        //}

        protected override void OnPositionChanged(Position position)
        {
            var Securityid = position.Security.ToString();
            // 获取当前持仓信息
            string logEntry = $"{DateTime.Now}: 持仓变化 - 合约: {position.Security},数量: {position.Volume}, 均价: {position.AveragePrice}, IsInPosition: {position.IsInPosition}\n";
            if (position.Volume!=0 && !_position.ContainsKey(Securityid))
            {
                _position.Add(Securityid, position.Volume);
                if (position.Volume>0)
                {
                    //开多
                    _ = SendPositionUpdateAsync(position, "开多");
                }
                else
                {
                    //开空
                    _ = SendPositionUpdateAsync(position, "开空");
                }
                File.AppendAllText(_logFilePath,"开仓"+ logEntry);

            }
            else if(position.Volume == 0 && _position.ContainsKey(Securityid))
            {
                _position.Remove(Securityid);
                _ = SendPositionUpdateAsync(position, "平仓");
                File.AppendAllText(_logFilePath, "平仓" + logEntry);
            }
        }

        // 异步发送持仓更新信息
        private async Task SendPositionUpdateAsync(Position position, string actionType)
        {
            if (!_isInitialized || !_MT5WebSocketClient.IsConnected)
            {
                File.AppendAllText(_logFilePath, "WebSocket未就绪，无法发送持仓更新\n");
                return;
            }

            try
            {
                var positionInfo = new
                {
                    action = actionType,
                    security = position.Security.ToString(),
                    volume = position.Volume,
                    averagePrice = position.AveragePrice,
                    isInPosition = position.IsInPosition,
                    timestamp = DateTime.Now
                };

                bool success = await _MT5WebSocketClient.SendRequest("position_update", positionInfo);
                if (success)
                {
                    File.AppendAllText(_logFilePath, $"已发送{actionType}消息到WebSocket服务器\n");
                }
                else
                {
                    File.AppendAllText(_logFilePath, $"发送{actionType}消息失败\n");
                }
            }
            catch (Exception ex)
            {
                File.AppendAllText(_logFilePath, $"发送持仓更新消息异常: {ex.Message}\n");
            }
        }

        protected override void OnCalculate(int bar, decimal value)
        {
            // 策略计算逻辑，暂时不需要实现
            // 我们主要使用此策略监控订单和持仓变化
        }

        protected override void OnSuspended()
        {
            Disconnect();
        }

        protected override void OnStopped()
        {
            Disconnect();
        }

        public void Disconnect()
        {
            if (_disposed) return;

            try
            {
                File.AppendAllText(_logFilePath, "正在释放资源\n");
                _MT5WebSocketClient?.Dispose();
                _disposed = true;
            }
            catch (Exception ex)
            {
                File.AppendAllText(_logFilePath, $"释放资源时出错: {ex.Message}\n");
            }
        }
    }
}