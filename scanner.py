import socket
import os
import struct
import threading
import time
from ctypes import *
from netaddr import IPNetwork,IPAddress

# 监听的主机
host="192.168.213.134"
# 扫描的目标子网
subnet="192.168.213.0/24"

# 自定义的字符串，将在ICMP响应中进行核对
magic_message="PYTHONRULES!"

# 批量发送UDP数据包
def udp_sender(subnet, magic_message):
    time.sleep(5)
    sender=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    for ip in IPNetwork(subnet):
	try:
	    sender.sendto(magic_message, ("%d" % ip,65212))
	except:
	    pass


class IP(Structure):
    _fields_ = [
    ("ihl",		c_ubyte, 4),
    ("version",		c_ubyte, 4),
    ("tos",		c_ubyte),
    ("len",		c_ushort),
    ("id",		c_ushort),
    ("offset",		c_ushort),
    ("ttl",		c_ubyte),
    ("protocol_num",	c_ubyte),
    ("sum",		c_ushort),
    ("src",		c_ulong),
    ("dst",		c_ulong)
    ]

    def __new__(self, socket_buffer=None):
	return self.from_buffer_copy(socket_buffer)

    def __init__(self, socket_buffer=None):
	self.protocol_map={1:"ICMP", 6:"TCP", 17:"UDP"}

	self.src_address=socket.inet_ntoa(struct.pack("<L", self.src))
	self.dst_address=socket.inet_ntoa(struct.pack("<L", self.dst))

	try:
	    self.protocol=self.protocol_map[self.protocol_num]
	except:
	    self.protocol=str(self.protocol_num)

class ICMP(Structure):
    _fields_ = [
    ("type",		c_ubyte),
    ("code",		c_ubyte),
    ("checksum",	c_ushort),
    ("unused",		c_ushort),
    ("next_hop_mtu",	c_ushort)
    ]

    def __new__(self, socket_buffer):
	return self.from_buffer_copy(socket_buffer)

    def __init__(self, socket_buffer):
	pass

if os.name=="nt":
    socket_protocol=socket.IPPROTO_IP
else:
    socket_protocol=socket.IPPROTO_ICMP

sniffer=socket.socket(socket.AF_INET, socket.SOCK_RAW, socket_protocol)

sniffer.bind((host, 0))
sniffer.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

if os.name=="nt":
    sniffer.ioctl(socket.SID_RCVALL, socket.RCVALL_ON)

# 开始发送数据包
t=threading.Thread(target=udp_sender, args=(subnet, magic_message))
t.start()

try:
    while True:
	raw_buffer=sniffer.recvfrom(65565)[0]
	ip_header=IP(raw_buffer[0:20])
	
	print "Protocol: %s %s -> %s" % (ip_header.protocol, ip_header.src_address, ip_header.dst_address)

	if ip_header.protocol == "ICMP":
	    offset=ip_header.ihl*4
	    buf=raw_buffer[offset:offset+sizeof(ICMP)]

	    imcp_header=ICMP(buf)

	    #print "ICMP -> Type: %d Code: %d" % (icmp_header.type,icmp_header.code)
	    # 检查类型代码是否为3
	    if icmp_header.code==3 and icmp_header.type==3:
		# 确认响应的主机在子网内
		if IPAddress(ip_header.src_address) in IPNetwork(subnet):
		    # 确认ICMP数据包中包含自定义的字符串
		    if raw_buffer[len(raw_buffer)-len(magic_message):]==magic_message:
			print "Host up: %s" % ip_header.src_address

except KeyboardInterrupt:
    if os.name=="nt":
	sniffer.ioctl(socket.SID_RCVALL, socket.RCVALL_OFF)
