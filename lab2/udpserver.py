# udpserver.py
import socket
import struct
import threading
import random

# 报文头部格式：type(1B), seq(2B), length(2B)
HEADER_FORMAT = '!BHH'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

# 报文类型常量
NTYPE_SYN = 1
NTYPE_ACK = 2
NTYPE_DATA = 3
NTYPE_FIN = 4

DROP_RATE = 0.2  # 丢包概率（用于模拟丢包）

class UDPServer:
    def __init__(self, port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)#创建套接字，ipv4 udp
        self.sock.bind(('', port))  # 监听所有IP地址
        print(f"[启动] UDP服务器已启动，监听端口 {port}")

        self.expected_seq = {}  # 每个客户端的期望序号
        self.lock = threading.Lock()  # 控制并发接收

    def start(self):
        while True:
            data, addr = self.sock.recvfrom(1024)
            threading.Thread(target=self.handle_packet, args=(data, addr)).start()#每收到一个包就开启一个新线程来处理

    #处理
    def handle_packet(self, data, addr):
        # 解包头部信息
        if len(data) < HEADER_SIZE:
            return  # 非法包
        pkt_type, seq, length = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
        payload = data[HEADER_SIZE:HEADER_SIZE + length]

        # 模拟 SYN（三次握手）处理
        if pkt_type == NTYPE_SYN:
            print(f"[握手] 收到来自 {addr} 的 SYN")
            self.expected_seq[addr] = 0 # 初始化该客户端期望序号为0
            response = struct.pack(HEADER_FORMAT, NTYPE_ACK, 0, 0) # 回复ACK，seq为0
            self.sock.sendto(response, addr)
            print(f"[握手] 向 {addr} 回复 SYN-ACK")
            return

        # 模拟数据接收
        if pkt_type == NTYPE_DATA:
            with self.lock:
                # 模拟丢包（服务端丢弃）
                if random.random() < DROP_RATE:
                    print(f"[丢弃] 丢弃来自 {addr} 的包 seq={seq}")
                    return

                # 获取客户端期望的下一个序号
                expected = self.expected_seq.get(addr, 0)

                if seq == expected:
                    print(f"[接收] 来自 {addr} 的正确数据包 seq={seq}, 数据={payload[:10]}...")
                    self.expected_seq[addr] = expected + 1
                else:
                    print(f"[接收] 来自 {addr} 的重复或乱序数据包 seq={seq}，期望 seq={expected}")

                # 无论正确与否，回复累计 ACK
                ack_pkt = struct.pack(HEADER_FORMAT, NTYPE_ACK, self.expected_seq[addr] - 1, 0)
                self.sock.sendto(ack_pkt, addr)
                print(f"[ACK] 回复 ACK {self.expected_seq[addr] - 1} 给 {addr}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("用法: python udpserver.py <port>")
        sys.exit(1)
    server = UDPServer(int(sys.argv[1]))
    server.start()
