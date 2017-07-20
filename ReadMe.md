**CMDB客户端**

    适用于 python 2.6+ ~ 3.x， 收集客户端机器上的硬件信息并定时上报到server端
    
    目前收集器 只有Linux平台的, Windows平台尚未开发， 支持自定义收集器
  

**安装/运行**
    
    $ git clone https://github.com/charlesxs/cmdb_agent.git
    
    $ cd cmdb_agent && pip install -r requirements.txt
    
    $ python cmdb_agent.py
    
    # 添加到cron, 定期上报
    
    $ 34 1 * * * python cmdb_agent.py
    
    