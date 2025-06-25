# udpclient.py
import socket        # 用于创建 UDP socket
import struct        # 用于封装和解析自定义报文头部
import threading     # 用于实现并发处理 ACK 接收
import time          # 用于记录发送时间以计算 RTT
import sys           # 用于命令行参数解析
import pandas as pd  # 用于统计 RTT 等信息

# 自定义协议格式：type(1B), seq(2B), length(2B)
HEADER_FORMAT = '!BHH'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)#5B

# 报文类型常量定义
NTYPE_SYN = 1   # 连接请求
NTYPE_ACK = 2   # 确认应答
NTYPE_DATA = 3  # 数据包
NTYPE_FIN = 4   # 断开连接（未实现）

# GBN 相关参数
WINDOW_SIZE = 5     # 滑动窗口大小，最多发送5个未确认包
DATA_SIZE = 80      # 每个数据包大小（字节）
TIMEOUT = 0.3       # 超时重传定时（秒）

# 要发送的数据（模拟内容）
data = b'This is a test message to demonstrate reliable UDP transmission. ' * 10
# 拆分数据为每个80字节的包
chunks = [data[i:i + DATA_SIZE] for i in range(0, len(data), DATA_SIZE)]

# 封装并发送一个数据包（带头部）
def send_packet(sock, server_addr, seq, payload):#sock: 当前使用的 UDP socket, 服务器的地址（IP + 端口）,当前包的序号（序列号）实际要发送的内容（字节串）
    header = struct.pack(HEADER_FORMAT, NTYPE_DATA, seq, len(payload))
    sock.sendto(header + payload, server_addr)#通过 sock.sendto() 把数据发送到指定的服务器地址。

# 客户端类封装
class UDPClient:
    def __init__(self, server_ip, server_port):
        # 初始化参数
        self.server_addr = (server_ip, server_port)  # 目标服务器地址
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)#创建一个套接字，ipv4,udp
        self.base = 0  # 已发送但未确认的最小序号
        self.next_seq = 0  # 下一个要发送的序号
        self.lock = threading.Lock()  # 用于线程安全
        self.send_times = {}  # 每个序号发送时间，用于计算RTT
        self.timers = {}  # 每个序号的重传定时器
        self.rtt_list = []  # 存储RTT值
        self.acknowledged = set()  # 已确认序号集合
        self.send_attempts = [0] * len(chunks)  # 每个包的尝试发送次数（用于丢包统计）


    # 模拟 TCP 的三次握手
    def handshake(self):
        print("[连接] 发送 SYN")
        syn_packet = struct.pack(HEADER_FORMAT, NTYPE_SYN, 0, 0)
        self.sock.sendto(syn_packet, self.server_addr)

        # 等待服务端返回 SYN-ACK
        data, _ = self.sock.recvfrom(1024)
        ptype, _, _ = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])#解包，只关心第一个字段
        if ptype == NTYPE_ACK:
            print("[连接] 收到 SYN-ACK，连接建立")

    # 启动客户端主逻辑，主流程控制
    def start(self):
        self.handshake()  # 执行三次握手建立连接
        threading.Thread(target=self.receive_ack, daemon=True).start()  # 启动线程接收ACK
        self.send_data()  # 开始发送数据
        time.sleep(1)  # 等待剩余ACK处理，过1s再打印统计信息
        self.statistics()  # 打印统计信息

    # 主线程负责数据发送（基于窗口）
    # 不断检查窗口内是否可以继续发送数据，并将数据包一个一个地发送出去
    def send_data(self):
        while self.base < len(chunks):#当前窗口起始序号<所有数据块的列表
            with self.lock:
                while self.next_seq < self.base + WINDOW_SIZE and self.next_seq < len(chunks):#下一个要发送的包”在窗口范围内
                    print(f"[发送] 第 {self.next_seq} 包")
                    send_packet(self.sock, self.server_addr, self.next_seq, chunks[self.next_seq])
                    self.send_attempts[self.next_seq] += 1#记录当前这个包的“发送尝试次数”
                    self.send_times[self.next_seq] = time.time()#记录这个包本次发送的时间戳
                    self.start_timer(self.next_seq)#启动一个定时器如果超时就自动重传。
                    self.next_seq += 1

    # ACK 接收线程逻辑
    def receive_ack(self):
        while True:
            data, _ = self.sock.recvfrom(1024)
            ptype, ack_seq, _ = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
            if ptype == NTYPE_ACK:
                with self.lock:
                    # 首次收到该 ACK，记录 RTT
                    if ack_seq not in self.acknowledged:
                        rtt = (time.time() - self.send_times[ack_seq]) * 1000#转化为毫秒
                        self.rtt_list.append(rtt)
                        self.acknowledged.add(ack_seq)
                        print(f"[ACK] 收到 ACK {ack_seq}, RTT = {rtt:.2f}ms")

                    self.base = max(self.base, ack_seq + 1)  # 滑动窗口
                    self.stop_timer(ack_seq)

    # 超时重传逻辑GBN
    def retransmit(self, seq):
        with self.lock:#避免线程冲突
            if seq in self.acknowledged:
                return  # 已确认，不重传

            print(f"[重传] 序号 {seq}")
            self.send_attempts[seq] += 1
            send_packet(self.sock, self.server_addr, seq, chunks[seq])
            self.send_times[seq] = time.time()
            self.start_timer(seq)  # 重新启动定时器

    # 为一个序号设置重传定时器
    def start_timer(self, seq):
        timer = threading.Timer(TIMEOUT, self.retransmit, args=(seq,))
        self.timers[seq] = timer
        timer.start()

    # 停止某个序号的定时器
    def stop_timer(self, seq):
        if seq in self.timers:
            self.timers[seq].cancel()
            del self.timers[seq]

    # 打印统计信息
    def statistics(self):
        print("\n[统计] 发送完成")
        df = pd.Series(self.rtt_list)
        print(f"平均 RTT: {df.mean():.2f}ms")
        print(f"最大 RTT: {df.max():.2f}ms")
        print(f"最小 RTT: {df.min():.2f}ms")
        print(f"RTT 标准差: {df.std():.2f}ms")

        # 统计丢包率 = 重传次数 / 总发送次数
        total_retrans = sum([x - 1 for x in self.send_attempts if x > 1])
        loss_rate = total_retrans / sum(self.send_attempts)
        print(f"丢包率: {loss_rate:.2%}")

# 主程序入口，读取命令行参数
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("用法: python udpclient.py <server_ip> <port>")
        sys.exit(1)
    client = UDPClient(sys.argv[1], int(sys.argv[2]))
    client.start()
