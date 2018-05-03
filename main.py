# coding:utf-8
import cStringIO
import httplib
import os
import pycurl
import time
from Queue import Queue
from optparse import OptionParser
from threading import Thread

import requests
from urllib3 import disable_warnings

from module import get_ua

httplib.HTTPConnection._http_vsn = 10
httplib.HTTPConnection._http_vsn_str = 'HTTP/1.0'

disable_warnings()
succ = 0
fail = 0
socks_timeout = 3
ip_queue = Queue()
result_queue = Queue()

parser = OptionParser()
parser.add_option('-o', '--output', dest='output', metavar="FILE", help='write to file', default='proxy.txt')
parser.add_option('-t', '--type', dest='proxy_type', default='http', help='possible type: http(default) https socks5 socks4')
parser.add_option('-T', '--thread', dest='thread', type='int', default=40, help='thread count')
parser.add_option('-p', '--port', dest='port', type='int', default=1080, help='port of proxy not specified port')
(options, args) = parser.parse_args()

if len(args) == 0:
    parser.exit(parser.format_help())
ip = open(args[0]).read().splitlines()
port = options.port
proxy_type = options.proxy_type


class ScanThread(Thread):
    def __init__(self):
        super(ScanThread, self).__init__()
        self.ua = get_ua()
        if proxy_type == 'socks5' or proxy_type == 'socks4':
            self.socksc = pycurl.Curl()
            self.socksc.setopt(pycurl.CONNECTTIMEOUT, socks_timeout)
            self.socksc.setopt(pycurl.TIMEOUT, socks_timeout)
            self.socksc.setopt(pycurl.NOSIGNAL, socks_timeout)
            self.socksc.setopt(pycurl.HTTP_VERSION, pycurl.CURL_HTTP_VERSION_1_0)
            self.socksc.setopt(pycurl.NOBODY, 1)
            self.socksc.setopt(pycurl.HEADER, 1)
            self.buf = cStringIO.StringIO()
            self.socksc.setopt(self.socksc.WRITEFUNCTION, self.buf.write)
            self.url = 'http://www.baidu.com/img/bd_logo1.png'
        elif proxy_type == 'https':
            self.url = 'https://www.baidu.com/img/bd_logo1.png'
        else:
            self.url = 'http://www.baidu.com/img/bd_logo1.png'

    def SocksProxyCheck(self, ip, port):
        self.socksc.setopt(pycurl.PROXY, ip)
        self.socksc.setopt(pycurl.URL, self.url)
        self.socksc.setopt(pycurl.PROXYPORT)
        if proxy_type == 'socks5':
            self.socksc.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS5)
        else:
            self.socksc.setopt(pycurl.PROXYTYPE, pycurl.PROXYTYPE_SOCKS4)
        try:
            self.socksc.perform()
            return True
        except Exception:
            return False

    def run(self):
        global succ, fail
        while True:
            ip = ip_queue.get()
            if proxy_type == 'socks5' or proxy_type == 'socks4':
                self.buf.truncate(0)
                check = self.SocksProxyCheck(ip, port)
            else:
                try:
                    with requests.head(self.url, verify=False, timeout=socks_timeout, headers={'User-Agent': self.ua},
                                       proxies={'http': 'http://%s:%d' % (ip, port), 'https': 'https://%s:%d' % (ip, port)}) as r:
                        check = len(r.headers) > 0
                except Exception:
                    check = False
            if check:
                succ += 1
                result_queue.put(ip)
            else:
                fail += 1


if __name__ == '__main__':
    for i in ip:
        if i.strip() == '':
            continue
        ip_queue.put(i)

    for _ in range(options.thread):
        t = ScanThread()
        t.setDaemon(True)
        t.start()
    os.remove(options.output)
    while True:
        print('Success: %d Failed: %d Left: %d' % (succ, fail, ip_queue.qsize()))
        while result_queue.qsize() > 0:
            open(options.output, 'a+').write(result_queue.get() + '\n')
        time.sleep(10)
