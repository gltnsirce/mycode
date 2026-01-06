#!/bin/bash
# mtu_test.sh - 云环境MTU综合测试

TARGETS=("8.8.8.8" "内部服务IP" "同区域VM")
CURRENT_MTU=$(ip link show eth0 | grep mtu | awk '{print $5}')

echo "当前MTU: $CURRENT_MTU"
echo ""

for target in "${TARGETS[@]}"; do
  echo "测试目标: $target"
  echo "--------------------------------"
  
  # 测试PMTUD
  ping -M do -s 1500 -c 2 -W 2 $target >/dev/null 2>&1
  if [ $? -eq 0 ]; then
    echo "✓ PMTUD 正常 (可传1500字节包)"
  else
    echo "✗ PMTUD 可能失效"
  fi
  
  # 寻找最大MTU
  found=0
  for size in {1460..500..-20}; do
    if ping -M do -s $size -c 1 -W 1 $target >/dev/null 2>&1; then
      echo "✓ 最大有效载荷: $size 字节 (MTU: $((size+28)))"
      found=1
      break
    fi
  done
  
  if [ $found -eq 0 ]; then
    echo "✗ MTU测试失败，网络可能不通"
  fi
  echo ""
done
