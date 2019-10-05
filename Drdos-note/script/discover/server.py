import asyncio
import time
import os
from multiprocessing import Process,Lock,Value,Manager
import queue
import sqlite3
import threading
import collections
import platform
from ctypes import c_bool
import copy
"""
这里使用的是异步触发式服务器，因为在IO上同时需要保证效率，
所以代码会比较冗长，希望能提出宝贵建议
"""
__author__ = "chriskaliX"

class Receive:
    _dict = dict() # 外部
    _dict_tmp = dict() # 内部
    class EchoServerProtocol:
        def connection_made(self, transport):
            self.transport = transport
        def datagram_received(self, data, addr):
            if len(data) > 100:
                Receive.counter(Receive._dict_tmp, addr[0])
        def error_received(self,data,addr):
            pass

    @staticmethod
    async def start_datagram_proxy(ip,port):
        loop = asyncio.get_event_loop()
        return await loop.create_datagram_endpoint(
            lambda: Receive.EchoServerProtocol(),
            local_addr=(ip, port))

    @staticmethod
    def run(ip,port,_dict,signal):
        # 将当前Receive中_dict设为全局共享
        Receive._dict = _dict
        
        # Linux下uvloop提高速度
        if platform.system() == "Linux":
            import uvloop
            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        
        loop = asyncio.get_event_loop()
        
        def getvalue(signal):
            while True:
                time.sleep(1)
                if signal.value:
                    Receive._dict.update(Receive._dict_tmp)
                    Receive._dict_tmp.clear()
                    signal.value = False
                    # loop.call_soon_threadsafe(loop.stop)
                    # break
        
        threading.Thread(target=getvalue,args=(signal,)).start()
        coro = Receive.start_datagram_proxy(ip,port)
        transport, _ = loop.run_until_complete(coro)
        loop.run_forever()
        
    @staticmethod
    def counter(_dict,key):
        _dict[key] = _dict.get(key) + 1 if key in _dict.keys() else 1

# class的调用和使用
if __name__ == '__main__':
    # 用于与子进程交互的字典
    _dict = Manager().dict()
    
    # 信号值，用于获取子进程的字典
    signal = Manager().Value(c_bool,False)
    
    # Performance
    # 
    # Q&A：
    # Q：为什么不直接对Manager进行操作
    # A：效率低
    # 参考 https://stackoverflow.com/questions/10721915/shared-memory-objects-in-multiprocessing
    #     https://www.codesd.com/item/python-manager-dict-is-very-slow-compared-to-dict.html
    #
    # Q：为什么需要count
    # A：有漏洞的服务器不一定都有较好的攻击效果，NTP monlist，SSDP等返回包的大小都比较固定，相反
    #    PPS就比较重要，这边记录下IP以及他们所返回包的数量，一定程度上筛选了漏洞服务器的质量
    
    # 开启进程并且监听
    pro = Process(target=Receive.run,args=('127.0.0.1',9999,_dict,signal))
    pro.start()
    
    time.sleep(20)
    
    # 设置signal.value为True，即可获得_dict的值
    signal.value = True
    while True:
        print(_dict)
        print(pro.is_alive())
        time.sleep(1)