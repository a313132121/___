#!/usr/bin/env python3

import gzip         #https://www.cnblogs.com/eliwang/p/14591861.html
import os
import shutil   #主要：拷贝文件https://blog.csdn.net/weixin_41261833/article/details/108050152
import subprocess   #子进程管理 https://zhuanlan.zhihu.com/p/91342640    https://www.runoob.com/w3cnote/python3-subprocess.html
from concurrent.futures import ThreadPoolExecutor   #线程池 https://zhuanlan.zhihu.com/p/65638744 https://www.jianshu.com/p/6d6e4f745c27
from urllib.parse import quote  #https://blog.csdn.net/weixin_43788986/article/details/125572389

import requests #python中requests库使用方法详解 https://zhuanlan.zhihu.com/p/137649301  https://www.runoob.com/python3/python-requests.html
import yaml
import json

import time
from multiprocessing import Process, Manager, Semaphore
from tqdm import tqdm



def download(url, file, unpack_gzip=False):
    os.makedirs(os.path.normpath(os.path.dirname(file)), exist_ok=True)
    #os.path.dirname(path)功能：去掉文件名，返回目录 ,此处clash_path='/usr/local/bin/clash'，返回'/usr/local/bin/'
    #os.path.normpath(path)，规范路径path字符串 https://blog.csdn.net/jn10010537/article/details/122769205
    #os.makedirs(path,mode) 用于递归创建目录，path -- 需要递归创建的目录，可以是相对或者绝对路径，mode -- 权限模式
    with (
        #python中requests库使用方法详解 https://zhuanlan.zhihu.com/p/137649301  https://www.runoob.com/python3/python-requests.html
        requests.get(url, headers={'Accept-Encoding': 'gzip'}, stream=True) as resp,
        open(file, 'wb') as _out
    ):
        _in = resp.raw
        if unpack_gzip or resp.headers.get('Content-Encoding') == 'gzip':
            _in = gzip.open(_in)    #解压文件https://www.cnblogs.com/eliwang/p/14591861.html
        shutil.copyfileobj(_in, _out)   #拷贝文件https://zhuanlan.zhihu.com/p/213919757 和 https://www.cnblogs.com/xiangsikai/p/7787101.html


def test_latency(alive,proxy, timeout=2000):
    try:
        #urllib.parse.quote()   https://blog.csdn.net/weixin_43788986/article/details/125572389
        #quote() 介绍2：https://blog.csdn.net/weixin_43411585/article/details/89067127
        r = requests.get(f"http://127.0.0.1:9090/proxies/{quote(proxy['name'], safe='')}/delay", params={
            'url': 'https://i.ytimg.com/generate_204',
            'timeout': timeout
        }, timeout=timeout / 400)
        response = json.loads(r.text)
        if response['delay'] > 0:
            alive['proxies'].append(proxy)
    except Exception as e:
        print(e)



def test_all_latency(   #latency：潜伏
    config_url: str = None, #函数注释（定义函数时使用“：”及“ ->”符号） https://blog.csdn.net/finalkof1983/article/details/87943032 https://blog.csdn.net/hou09tian/article/details/124435432
    config_path='/etc/clash/config.yaml',
    config_cover=True,
    clash_url='https://github.com/Dreamacro/clash/releases/download/v1.14.0/clash-linux-amd64-v1.14.0.gz',
    clash_path='/usr/local/bin/clash',
    clash_cover=False,
    max_workers=32,
    timeout=2000,
) -> list[tuple[str, dict]]:# tuple和list的区别：https://zhuanlan.zhihu.com/p/92527888 https://www.liaoxuefeng.com/wiki/1016959663602400/1017092876846880
    if clash_cover or not os.path.exists(clash_path):   #os.path.exists()就是判断括号里的文件是否存在，括号内的可以是文件路径
        download(clash_url, clash_path, unpack_gzip=True)#下载clash
    if config_url and (config_cover or not os.path.exists(config_path)):
        download(config_url, config_path)#下载config.yaml（实际就是节点文件）
    os.chmod(clash_path, 0o755)#os.chmod() 方法用于更改文件或目录的权限。
    #读取节点
    with open(config_path, 'r') as reader:
        try:
            proxyconfig = yaml.load(reader, Loader=yaml.FullLoader)
        except Exception as err:
            print(err) 
    alive = {'proxies':[]}
    clash = subprocess.Popen([clash_path, '-f', config_path, '--ext-ctl', ':9090'])
    processes =[]
    sema = Semaphore(max_workers)
    time.sleep(5)
    for i in tqdm(range(int(len(proxyconfig['proxies']))), desc="Testing"):
        sema.acquire()
        p = Process(target=test_latency, args=(alive,proxyconfig['proxies'][i]))
        p.start()
        processes.append(p)
    for p in processes:
        p.join
    time.sleep(5)
    alive = yaml.dump(alive, default_flow_style=False, sort_keys=False, allow_unicode=True, width=750, indent=2)
    return alive 
    """
    with subprocess.Popen([clash_path, '-f', config_path, '--ext-ctl', ':9090'], stdout=subprocess.PIPE) as popen:
    #subprocess子进程管理 https://zhuanlan.zhihu.com/p/91342640
    #自己推荐看这个 https://www.runoob.com/w3cnote/python3-subprocess.html
    #https://blog.csdn.net/weixin_45314192/article/details/123310026
        with open(config_path, 'r') as reader:
            try:
                proxyconfig = yaml.load(reader, Loader=yaml.FullLoader)
            except Exception as err:
                print(err)   
        while b':9090' not in popen.stdout.readline():#为了停止popen.stdout.readline()吗？
            pass    #pass 语句不执行任何操作。语法上需要一个语句，但程序不实际执行任何动作时，可以使用该语句，或者是当站位语句
        try:
            with ThreadPoolExecutor(max_workers) as executor:
                for i in range(int(len(proxyconfig['proxies']))):
                    executor.submit(test_latency,alive,proxyconfig['proxies'][i])

                #sorted() 函数对所有可迭代的对象进行排序操作 https://blog.csdn.net/PY0312/article/details/88956795
                #zip() 函数用于将可迭代的对象作为参数,
                #map() 会根据提供的函数对指定序列做映射 https://blog.csdn.net/PY0312/article/details/88956795
                #将lambda函数赋值给一个变量，通过这个变量间接调用该lambda函数 https://blog.csdn.net/PY0312/article/details/88956795
        finally:    #无论try语句中是否抛出异常，finally中的语句一定会被执行https://blog.csdn.net/gyniu/article/details/80345160
            popen.terminate()#Popen.terminate()停止子进程
        alive = yaml.dump(alive, default_flow_style=False, sort_keys=False, allow_unicode=True, width=750, indent=2)
        return alive    
    """
if __name__ == '__main__':
    alive = test_all_latency('https://raw.githubusercontent.com/rxsweet/proxies/main/sub/sources/staticAll.yaml', timeout=10000)
    #alive = test_all_latency('https://raw.githubusercontent.com/zsokami/sub/main/trials_providers/All.yaml', timeout=10000)
    f = open('xxx.yaml', 'w',encoding="UTF-8")
    f.write(alive)
    f.close()
    #for item in test_all_latency('https://raw.githubusercontent.com/zsokami/sub/main/trials_providers/All.yaml', timeout=10000):
        #print(*item)    #*参数，**参数 https://zhuanlan.zhihu.com/p/89304906  https://blog.csdn.net/cadi2011/article/details/84871401
