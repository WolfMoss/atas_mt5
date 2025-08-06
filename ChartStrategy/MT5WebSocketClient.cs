using System;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.IO;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace ATASOrderLogStrategy
{
    class MT5WebSocketClient : IDisposable
    {
        private ClientWebSocket ws;
        private readonly string _logFilePath = @"C:\Users\Administrator\Documents\ATASLogs\TradeLog.txt";
        private readonly string _serverUrl = "ws://127.0.0.1:8766";
        private readonly SemaphoreSlim _sendSemaphore = new SemaphoreSlim(1, 1);
        private CancellationTokenSource _cancellationTokenSource;
        private bool _disposed = false;
        private bool _isConnecting = false;

        public bool IsConnected => ws?.State == WebSocketState.Open;

        public MT5WebSocketClient()
        {
            _cancellationTokenSource = new CancellationTokenSource();
        }

        public async Task<bool> Connect()
        {
            if (_isConnecting)
            {
                File.AppendAllText(_logFilePath, "正在连接中，请勿重复连接\n");
                return false;
            }

            if (IsConnected)
            {
                File.AppendAllText(_logFilePath, "WebSocket已连接\n");
                return true;
            }

            _isConnecting = true;
            try
            {
                // 释放旧的连接
                ws?.Dispose();
                ws = new ClientWebSocket();

                await ws.ConnectAsync(new Uri(_serverUrl), _cancellationTokenSource.Token);
                File.AppendAllText(_logFilePath, "已连接到服务器\n");

                // 启动接收消息任务
                _ = ReceiveMessages();
                return true;
            }
            catch (Exception ex)
            {
                File.AppendAllText(_logFilePath, $"WebSocket连接失败: {ex.Message}\n");
                return false;
            }
            finally
            {
                _isConnecting = false;
            }
        }

        private async Task ReceiveMessages()
        {
            try
            {
                var buffer = new byte[4096];
                while (ws.State == WebSocketState.Open && !_cancellationTokenSource.Token.IsCancellationRequested)
                {
                    var result = await ws.ReceiveAsync(new ArraySegment<byte>(buffer), _cancellationTokenSource.Token);
                    
                    if (result.MessageType == WebSocketMessageType.Text)
                    {
                        var message = Encoding.UTF8.GetString(buffer, 0, result.Count);
                        File.AppendAllText(_logFilePath, $"收到消息: {message}\n");
                    }
                    else if (result.MessageType == WebSocketMessageType.Close)
                    {
                        File.AppendAllText(_logFilePath, "服务器关闭连接\n");
                        break;
                    }
                }
            }
            catch (OperationCanceledException)
            {
                File.AppendAllText(_logFilePath, "接收消息任务被取消\n");
            }
            catch (Exception ex)
            {
                File.AppendAllText(_logFilePath, $"接收消息出错: {ex.Message}\n");
            }
        }

        public async Task<bool> SendRequest(string action, object parameters)
        {
            if (!IsConnected)
            {
                File.AppendAllText(_logFilePath, "WebSocket未连接，无法发送消息\n");
                return false;
            }

            await _sendSemaphore.WaitAsync();
            try
            {
                var request = new
                {
                    id = Guid.NewGuid().ToString(),
                    action = action,
                    @params = parameters,
                    timestamp = DateTime.Now
                };

                var json = JsonConvert.SerializeObject(request);
                var bytes = Encoding.UTF8.GetBytes(json);
                
                await ws.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, _cancellationTokenSource.Token);
                File.AppendAllText(_logFilePath, $"发送消息: {action}\n");
                return true;
            }
            catch (Exception ex)
            {
                File.AppendAllText(_logFilePath, $"发送消息失败: {ex.Message}\n");
                return false;
            }
            finally
            {
                _sendSemaphore.Release();
            }
        }

        public async Task Disconnect()
        {
            try
            {
                if (ws?.State == WebSocketState.Open)
                {
                    await ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "客户端断开连接", CancellationToken.None);
                    File.AppendAllText(_logFilePath, "WebSocket连接已断开\n");
                }
            }
            catch (Exception ex)
            {
                File.AppendAllText(_logFilePath, $"断开连接时出错: {ex.Message}\n");
            }
        }

        public void Dispose()
        {
            if (_disposed) return;

            _cancellationTokenSource?.Cancel();
            
            try
            {
                Disconnect().Wait(TimeSpan.FromSeconds(5));
            }
            catch (Exception ex)
            {
                File.AppendAllText(_logFilePath, $"释放资源时出错: {ex.Message}\n");
            }

            ws?.Dispose();
            _cancellationTokenSource?.Dispose();
            _sendSemaphore?.Dispose();
            
            _disposed = true;
        }
    }
}
