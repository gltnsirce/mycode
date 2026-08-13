#!/usr/bin/env python3
"""
中断监控脚本 - 监控 /proc/interrupts 文件中的中断变化
连续5次对比，间隔1秒，输出有增长的中断信息
------------------------------------------------------------------------------------
How to use this script?

赋予执行权限:
chmod +x interrupt_monitor.py

默认模式：5次采样，间隔1秒:
sudo python3 interrupt_monitor.py

自定义参数：间隔2秒，采样10次:
sudo python3 interrupt_monitor.py -i 2 -n 10

快速检查模式：只显示当前状态:
sudo python3 interrupt_monitor.py --quick

查看帮助:
python3 interrupt_monitor.py -h
"""


import os
import time
import sys
from typing import Dict, List, Tuple, Optional


class InterruptMonitor:
    def __init__(self, interval: float = 1.0, iterations: int = 5):
        """
        初始化中断监控器
        
        Args:
            interval: 采样间隔（秒）
            iterations: 采样次数（对比次数）
        """
        self.interval = interval
        self.iterations = iterations
        self.interrupts_file = "/proc/interrupts"
        
    def check_file_exists(self) -> bool:
        """检查 /proc/interrupts 文件是否存在"""
        if not os.path.exists(self.interrupts_file):
            print(f"错误: {self.interrupts_file} 文件不存在")
            return False
        if not os.access(self.interrupts_file, os.R_OK):
            print(f"错误: 无法读取 {self.interrupts_file} 文件，权限不足")
            return False
        return True
    
    def parse_interrupts(self) -> Tuple[List[str], Dict[str, List[int]], Dict[str, str]]:
        """
        解析 /proc/interrupts 文件
        
        Returns:
            cpu_headers: CPU 头信息列表（如 ['CPU0', 'CPU1', ...]）
            interrupt_data: 中断数据字典 {中断名: [CPU0值, CPU1值, ...]}
            interrupt_info: 中断额外信息字典 {中断名: 描述信息}
        """
        try:
            with open(self.interrupts_file, 'r') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"错误: 读取文件失败 - {e}")
            sys.exit(1)
        
        if not lines:
            print("错误: 文件内容为空")
            sys.exit(1)
        
        # 解析第一行：CPU 头信息
        # 格式: "           CPU0       CPU1       CPU2       CPU3       "
        first_line = lines[0].strip()
        cpu_headers = []
        if first_line:
            # 按空白字符分割，过滤空字符串
            parts = first_line.split()
            # 通常以 'CPU' 开头
            cpu_headers = [p for p in parts if p.startswith('CPU')]
        
        if not cpu_headers:
            print("警告: 无法解析 CPU 头信息，使用默认格式")
            cpu_headers = [f"CPU{i}" for i in range(4)]  # 默认4个CPU
        
        num_cpus = len(cpu_headers)
        
        # 解析中断数据
        interrupt_data = {}
        interrupt_info = {}
        
        for line in lines[1:]:
            if not line.strip():
                continue
            
            parts = line.split()
            if len(parts) < num_cpus + 1:
                continue
            
            # 中断号/名称（第一个字段）
            interrupt_name = parts[0]
            
            # CPU 计数（接下来的 num_cpus 个字段）
            cpu_counts = []
            for i in range(num_cpus):
                try:
                    count = int(parts[i + 1])
                except (ValueError, IndexError):
                    count = 0
                cpu_counts.append(count)
            
            interrupt_data[interrupt_name] = cpu_counts
            
            # 剩余部分是中断描述信息（可选）
            if len(parts) > num_cpus + 1:
                interrupt_info[interrupt_name] = ' '.join(parts[num_cpus + 1:])
            else:
                interrupt_info[interrupt_name] = ''
        
        return cpu_headers, interrupt_data, interrupt_info
    
    def get_interrupt_diff(self, old_data: Dict[str, List[int]], 
                          new_data: Dict[str, List[int]]) -> Dict[str, List[int]]:
        """
        计算两次采样之间的中断差值
        
        Returns:
            差值字典 {中断名: [CPU0增长量, CPU1增长量, ...]}
        """
        diff = {}
        
        for name, new_counts in new_data.items():
            if name in old_data:
                old_counts = old_data[name]
                if len(new_counts) == len(old_counts):
                    diff_counts = [new - old for new, old in zip(new_counts, old_counts)]
                    # 只记录有增长的（任何CPU有增长）
                    if any(count > 0 for count in diff_counts):
                        diff[name] = diff_counts
        
        return diff
    
    def format_output(self, cpu_headers: List[str], 
                     interrupt_data: Dict[str, List[int]],
                     interrupt_info: Dict[str, str],
                     only_changed: Optional[List[str]] = None) -> str:
        """
        格式化输出中断信息，保持原始文件格式
        
        Args:
            cpu_headers: CPU 头信息
            interrupt_data: 中断数据
            interrupt_info: 中断描述信息
            only_changed: 只输出指定的中断名称列表，如果为 None 则输出所有
        
        Returns:
            格式化的字符串
        """
        lines = []
        
        # 构建 CPU 头行
        # 原始格式: "           CPU0       CPU1       CPU2       CPU3       "
        header_parts = []
        # 第一列对齐（通常10个空格）
        header_parts.append(" " * 10)
        for cpu in cpu_headers:
            header_parts.append(f"{cpu:>10}")
        lines.append(''.join(header_parts))
        
        # 确定要输出的中断列表
        if only_changed is None:
            interrupt_names = sorted(interrupt_data.keys())
        else:
            interrupt_names = sorted([name for name in only_changed if name in interrupt_data])
        
        # 输出每个中断
        for name in interrupt_names:
            counts = interrupt_data[name]
            info = interrupt_info.get(name, '')
            
            # 构建行: 中断名称 + 各CPU计数 + 描述信息
            parts = []
            # 中断名称（左对齐，宽度10）
            parts.append(f"{name:<10}")
            
            # CPU 计数（右对齐，宽度10）
            for count in counts:
                parts.append(f"{count:>10}")
            
            # 描述信息
            if info:
                parts.append(f"  {info}")
            
            lines.append(''.join(parts))
        
        return '\n'.join(lines)
    
    def monitor(self):
        """执行监控主逻辑"""
        print("=" * 80)
        print("中断监控脚本启动")
        print(f"采样间隔: {self.interval} 秒")
        print(f"采样次数: {self.iterations} 次")
        print(f"监控文件: {self.interrupts_file}")
        print("=" * 80)
        
        # 检查文件是否存在
        if not self.check_file_exists():
            sys.exit(1)
        
        # 存储采样数据
        samples = []
        
        # 第一次采样
        print(f"\n正在执行第 1 次采样...")
        cpu_headers, interrupt_data, interrupt_info = self.parse_interrupts()
        samples.append(interrupt_data)
        print(f"✓ 第 1 次采样完成，共 {len(interrupt_data)} 个中断")
        
        # 执行后续采样和对比
        all_changed_interrupts = set()
        
        for i in range(1, self.iterations):
            print(f"\n等待 {self.interval} 秒...")
            time.sleep(self.interval)
            
            print(f"正在执行第 {i+1} 次采样...")
            _, new_data, _ = self.parse_interrupts()
            samples.append(new_data)
            
            # 与前一次采样对比
            diff = self.get_interrupt_diff(samples[-2], samples[-1])
            
            if diff:
                print(f"✓ 第 {i+1} 次采样完成，发现 {len(diff)} 个中断有增长:")
                for name, counts in diff.items():
                    total_growth = sum(counts)
                    print(f"  - {name}: 总计增长 {total_growth} 次 ({', '.join([f'CPU{j}={c}' for j, c in enumerate(counts) if c > 0])})")
                    all_changed_interrupts.add(name)
            else:
                print(f"✓ 第 {i+1} 次采样完成，没有发现中断增长")
        
        # 输出最终结果
        print("\n" + "=" * 80)
        print("监控完成 - 在监控期间有增长的中断信息")
        print("=" * 80)
        
        if all_changed_interrupts:
            print("\n以下中断在监控期间发生了增长（按原始格式输出）:\n")
            # 获取最后一次采样的数据
            final_data = samples[-1]
            output = self.format_output(cpu_headers, final_data, interrupt_info, 
                                       only_changed=list(all_changed_interrupts))
            print(output)
        else:
            print("\n在监控期间没有发现任何中断增长")
    
    def quick_check(self):
        """
        快速检查模式：只做一次采样并显示当前中断状态
        """
        print("快速检查模式 - 显示当前中断状态")
        print("=" * 80)
        
        if not self.check_file_exists():
            sys.exit(1)
        
        cpu_headers, interrupt_data, interrupt_info = self.parse_interrupts()
        output = self.format_output(cpu_headers, interrupt_data, interrupt_info)
        print(output)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='监控 /proc/interrupts 文件中的中断变化',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                    # 默认监控：5次采样，间隔1秒
  %(prog)s -i 2 -n 10        # 间隔2秒，采样10次
  %(prog)s --quick           # 快速检查，只显示当前状态
  %(prog)s -h                # 显示帮助信息
        """
    )
    
    parser.add_argument('-i', '--interval', type=float, default=1.0,
                       help='采样间隔（秒），默认: 1.0')
    parser.add_argument('-n', '--iterations', type=int, default=5,
                       help='采样次数，默认: 5')
    parser.add_argument('-q', '--quick', action='store_true',
                       help='快速检查模式：只显示当前中断状态，不进行对比')
    
    args = parser.parse_args()
    
    monitor = InterruptMonitor(interval=args.interval, iterations=args.iterations)
    
    if args.quick:
        monitor.quick_check()
    else:
        monitor.monitor()


if __name__ == "__main__":
    main()
