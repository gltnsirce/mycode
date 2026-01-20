#!/bin/bash   
# network_monitor.sh      
LOG_FILE="/var/log/network_monitor.log"   
INTERVAL=300  # 5分钟      
whiletrue; do
    TIMESTAMP=$(date'+%Y-%m-%d %H:%M:%S')              # 测试连通性
    PING_RESULT=$(ping -c 4 8.8.8.8 | tail -2)              # 测速
    SPEED_RESULT=$(speedtest-cli --simple 2>/dev/null)              # 记录到日志
    echo"[$TIMESTAMP]" >> $LOG_FILE
    echo"Ping结果:" >> $LOG_FILE
    echo"$PING_RESULT" >> $LOG_FILE
    echo -e "测速结果:\n$SPEED_RESULT" >> $LOG_FILE
    echo"====================" >> $LOG_FILE
    sleep$INTERVAL   
done
