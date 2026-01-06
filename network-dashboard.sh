#!/bin/bash
# network-dashboard.sh

INTERVAL=2
WIDTH=80

print_header() {
    printf "%-15s %-10s %-10s %-10s %-10s %-10s %-10s\n" \
        "时间" "接收包/s" "发送包/s" "接收KB/s" "发送KB/s" "利用率%" "TCP重传/s"
    echo "$(printf '=%.0s' {1..80})"
}

clear
echo "网络性能实时监控仪表盘"
echo "刷新间隔: ${INTERVAL}秒 | 按 Ctrl+C 退出"
echo

while true; do
    # 获取网络设备数据
    DEV_DATA=$(sar -n DEV $INTERVAL 1 | grep -E "^(平均时间:|eth0|ens|enp)" | tail -1)
    TIMESTAMP=$(date '+%H:%M:%S')
    
    # 获取TCP重传数据
    ETCP_DATA=$(sar -n ETCP $INTERVAL 1 | tail -1)
    RETRANS=$(echo $ETCP_DATA | awk '{print $3}')
    
    # 解析DEV数据
    IFACE=$(echo $DEV_DATA | awk '{print $2}')
    RXPPS=$(echo $DEV_DATA | awk '{printf "%.1f", $3}')
    TXPPS=$(echo $DEV_DATA | awk '{printf "%.1f", $4}')
    RXKB=$(echo $DEV_DATA | awk '{printf "%.1f", $5}')
    TXKB=$(echo $DEV_DATA | awk '{printf "%.1f", $6}')
    IF_UTIL=$(echo $DEV_DATA | awk '{printf "%.1f", $11}')
    
    # 清屏并打印表头
    tput cup 3 0
    print_header
    
    # 打印数据行
    printf "%-15s %-10s %-10s %-10s %-10s %-10s %-10s\n" \
        "$TIMESTAMP" "$RXPPS" "$TXPPS" "$RXKB" "$TXKB" "$IF_UTIL" "$RETRANS"
    
    # 打印状态指示
    tput cup 8 0
    echo "状态指示:"
    
    if (( $(echo "$IF_UTIL > 80" | bc -l) )); then
        echo "  🔴 网卡利用率高 (>80%)"
    elif (( $(echo "$IF_UTIL > 50" | bc -l) )); then
        echo "  🟡 网卡利用率中等 (>50%)"
    else
        echo "  🟢 网卡利用率正常"
    fi
    
    if (( $(echo "$RETRANS > 10" | bc -l) )); then
        echo "  🔴 TCP重传频繁 (>10/s)"
    elif (( $(echo "$RETRANS > 1" | bc -l) )); then
        echo "  🟡 TCP有重传 (>1/s)"
    else
        echo "  🟢 TCP重传正常"
    fi
    
    # 打印流量柱状图
    tput cup 12 0
    echo "接收流量: [$(bar_graph $RXKB 1000 20)]"
    echo "发送流量: [$(bar_graph $TXKB 1000 20)]"
    
    sleep $INTERVAL
done

# 柱状图函数
bar_graph() {
    local value=$1
    local max=$2
    local width=$3
    local bars=$(( ($value * $width) / $max ))
    
    if (( bars > width )); then
        bars=$width
    fi
    
    printf "%${bars}s" | tr ' ' '█'
    printf "%$((width - bars))s" | tr ' ' '░'
}
