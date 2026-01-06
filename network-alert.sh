#!/bin/bash
# network-alert.sh
# Network monitoring script

# 告警阈值
UTIL_THRESHOLD=80      # 网卡利用率%
RETRANS_THRESHOLD=1    # TCP重传数/s
ERROR_THRESHOLD=1      # 网络错误数/s
DROP_THRESHOLD=5       # 丢包数/s

# 监控当前状态
check_network() {
    local interval=5
    
    # 获取网络设备统计
    local dev_data=$(sar -n DEV $interval 1 | grep -E "^(eth|ens|enp)" | tail -1)
    local edev_data=$(sar -n EDEV $interval 1 | grep -E "^(eth|ens|enp)" | tail -1)
    local etcp_data=$(sar -n ETCP $interval 1 | tail -1)
    
    # 解析数据
    local iface=$(echo $dev_data | awk '{print $2}')
    local util=$(echo $dev_data | awk '{print $11}')
    local rxerr=$(echo $edev_data | awk '{print $3}')
    local txerr=$(echo $edev_data | awk '{print $4}')
    local rxdrop=$(echo $edev_data | awk '{print $5}')
    local retrans=$(echo $etcp_data | awk '{print $3}')
    
    # 检查告警条件
    local alerts=()
    
    if (( $(echo "$util > $UTIL_THRESHOLD" | bc -l) )); then
        alerts+=("网卡 $iface 利用率过高: ${util}%")
    fi
    
    if (( $(echo "$retrans > $RETRANS_THRESHOLD" | bc -l) )); then
        alerts+=("TCP重传过高: ${retrans}/s")
    fi
    
    if (( $(echo "$rxerr > $ERROR_THRESHOLD" | bc -l) )); then
        alerts+=("接收错误: ${rxerr}/s")
    fi
    
    if (( $(echo "$rxdrop > $DROP_THRESHOLD" | bc -l) )); then
        alerts+=("接收丢包: ${rxdrop}/s")
    fi
    
    # 发送告警
    if [ ${#alerts[@]} -gt 0 ]; then
        local message="网络性能告警 - $(date)\n"
        for alert in "${alerts[@]}"; do
            message+="  ⚠️ $alert\n"
        done
        
        # 发送邮件（示例）
        echo -e "$message" | mail -s "网络告警" admin@example.com
        
        # 记录日志
        echo -e "$message" >> /var/log/network-alerts.log
    fi
}

# 持续监控
while true; do
    check_network
    sleep 60  # 每分钟检查一次
done
