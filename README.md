
项目名称：
    UDP Reliable Transfer 模拟系统（基于 GBN 协议）


功能概述：
    本项目在不可靠的 UDP 协议之上，模拟实现了类似 TCP 的可靠数据传输机制，
    包括连接建立（SYN-ACK）、滑动窗口控制、超时重传、ACK 累计确认等功能。
    使用 Python 编写，实现客户端与服务端协同通信，并对 RTT 和丢包率进行统计。

一、运行环境要求

    - Python 3.7 及以上
    - 安装依赖库：
        pip install pandas

二、文件结构说明

    udpserver.py     -- UDP 服务端程序
    udpclient.py     -- UDP 客户端程序
    README.txt       -- 项目说明文档（本文件）

三、使用说明


1. 启动服务器端：
    语法：
        python udpserver.py <端口号>
    示例：
        python udpserver.py 12345

2. 启动客户端：
    语法：
        python udpclient.py <服务器IP> <端口号>
    示例（本机测试）：
        python udpclient.py 127.0.0.1 12345


四、主要功能与技术点

    - 自定义应用层协议头（type, seq, length）
    - 模拟三次握手（SYN → SYN-ACK → ACK）
    - 实现 Go-Back-N 滑动窗口协议
    - 超时重传机制（每包设定 300ms 超时）
    - 服务端模拟丢包（DROP_RATE = 0.2）
    - 客户端多线程：发送数据 + 接收 ACK
    - 实时 RTT 计算与丢包率统计（pandas 支持）


五、示例输出（部分日志）

    [连接] 发送 SYN
    [连接] 收到 SYN-ACK，连接建立
    [发送] 第 0 包
    [发送] 第 1 包
    ...
    [ACK] 收到 ACK 0, RTT = 35.21ms
    ...
    [重传] 序号 2
    ...
    [统计] 发送完成
    平均 RTT: 47.12ms
    最大 RTT: 88.43ms
    最小 RTT: 32.11ms
    RTT 标准差: 14.22ms
    丢包率: 10.00%

六、注意事项

    - 客户端和服务器端必须使用相同端口进行通信
    - 丢包为随机模拟，测试结果可能有差异
    - 可自行修改 `DATA_SIZE` 和 `WINDOW_SIZE` 参数进行实验对比
    - 若想进行跨主机通信，请确保防火墙和 NAT 设置允许 UDP 通信


