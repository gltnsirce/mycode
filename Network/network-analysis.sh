#!/bin/bash
# network-analysis.sh

echo "=== 网络性能综合诊断 ==="
echo "检查时间: $(date)"
echo "采样间隔: 3秒，共3次采样"

# 1. 网络设备吞吐量
echo -e "\n[1] 网络设备吞吐量 (sar -n DEV):"
sar -n DEV 3 1 | tail -4

# 2. 网络设备错误
echo -e "\n[2] 网络设备错误统计 (sar -n EDEV):"
sar -n EDEV 3 1 | tail -3

# 3. TCP连接状态
echo -e "\n[3] TCP连接统计 (sar -n TCP,ETCP):"
echo "TCP连接:"
sar -n TCP 3 1 | tail -1
echo "TCP错误:"
sar -n ETCP 3 1 | tail -1

# 4. 套接字使用
echo -e "\n[4] 套接字使用情况 (sar -n SOCK):"
sar -n SOCK 3 1 | tail -1

# 5. 自动分析建议
echo -e "\n[5] 网络性能分析建议:"

# 分析网卡利用率
IFACE="eth0"
DEV_DATA=$(sar -n DEV 3 1 | grep "$IFACE" | tail -1)
IF_UTIL=$(echo $DEV_DATA | awk '{print $11}')

if (( $(echo "$IF_UTIL > 80" | bc -l) )); then
    echo "  ⚠️  网卡 $IFACE 利用率过高: ${IF_UTIL}%"
    echo "     建议：检查网络流量，考虑升级带宽"
fi

# 分析TCP重传
ETCP_DATA=$(sar -n ETCP 3 1 | tail -1)
RETRANS=$(echo $ETCP_DATA | awk '{print $3}')
TCP_DATA=$(sar -n TCP 3 1 | tail -1)
OSEG=$(echo $TCP_DATA | awk '{print $5}')

if [[ -n "$RETRANS" ]] && [[ -n "$OSEG" ]] && (( $(echo "$OSEG > 0" | bc -l) )); then
    RETRANS_RATE=$(echo "scale=4; $RETRANS / $OSEG * 100" | bc)
    if (( $(echo "$RETRANS_RATE > 0.1" | bc -l) )); then
        echo "  ⚠️  TCP重传率过高: ${RETRANS_RATE}%"
        echo "     建议：检查网络质量，排查丢包原因"
    fi
fi

# 分析套接字使用
SOCK_DATA=$(sar -n SOCK 3 1 | tail -1)
TCP_TW=$(echo $SOCK_DATA | awk '{print $6}')

if (( $(echo "$TCP_TW > 10000" | bc -l) )); then
    echo "  ⚠️  TIME_WAIT套接字过多: ${TCP_TW}"
    echo "     建议：优化TCP参数，检查应用连接管理"
fi
