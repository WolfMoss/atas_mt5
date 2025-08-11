# ATAS映射任意MT5
- 只能持有一单
### 用法
1. 配置config.json中，symbol_mapping节点下面的内容即可
2. ATASOrderLogStrategy.dll放到目录C:\Users\Administrator\Documents\ATAS\Strategies （没有文件夹就创建）
3. 启动websocket_server.exe，登录MT5，并设置好：工具->选项->EA交易->允许算法交易
4. ATAS右键打开图表策略，启动OrderLogStrategy