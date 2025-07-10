import tkinter as tk
from tkinter import messagebox, ttk
import threading
import time
import os
import subprocess
import serial
import serial.tools.list_ports
import numpy as np

class Connect6App:
    def __init__(self, root):
        self.root = root
        self.root.title("六子棋对弈系统")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # 游戏参数
        self.board_size = 9
        self.wait_time = 2  # 文件稳定等待时间
        self.board = np.zeros((self.board_size, self.board_size), dtype=int)
        self.turn_id = 1
        self.player_color = None  # 1:黑方, 2:白方
        self.last_board_state = np.zeros((self.board_size, self.board_size), dtype=int)
        self.game_started = False
        self.game_over = False
        self.is_first_move = True  # 标记是否是第一步
        
        # 串口设置
        self.serial_port = None
        self.baudrate = 115200
        self.bytesize = serial.EIGHTBITS
        self.parity = serial.PARITY_NONE
        self.stopbits = serial.STOPBITS_ONE
        
        # 初始化文件
        self.init_files()
        
        # 创建界面
        self.create_widgets()
        
        
    def init_files(self):
        # 创建或清空文件
        with open("Input.txt", "w") as f:
            for _ in range(self.board_size):
                f.write("0 " * (self.board_size-1) + "0\n")
        
        open("Con6Input.txt", "w").close()
        open("Con6Output.txt", "w").close()
        
        # 重置棋盘状态
        self.board = np.zeros((self.board_size, self.board_size), dtype=int)
        self.last_board_state = np.zeros((self.board_size, self.board_size), dtype=int)
        self.is_first_move = True
        
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧棋盘区域
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 棋盘标签
        board_label = ttk.Label(left_frame, text="棋盘", font=("Arial", 14, "bold"))
        board_label.pack(pady=(0, 10))
        
        # 创建棋盘画布
        self.canvas = tk.Canvas(left_frame, width=500, height=500, bg="#E8C87E")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # 右侧控制区域
        right_frame = ttk.Frame(main_frame, width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        # 控制面板
        control_frame = ttk.LabelFrame(right_frame, text="游戏控制")
        control_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 颜色选择
        color_frame = ttk.Frame(control_frame)
        color_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(color_frame, text="选择我方颜色:").pack(side=tk.LEFT)
        self.color_var = tk.StringVar(value="black")
        ttk.Radiobutton(color_frame, text="黑方", variable=self.color_var, 
                        value="black").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(color_frame, text="白方", variable=self.color_var, 
                        value="white").pack(side=tk.LEFT, padx=5)
        
        # 稳定时间设置
        time_frame = ttk.Frame(control_frame)
        time_frame.pack(fill=tk.X, pady=5)
        ttk.Label(time_frame, text="稳定时间(s):").pack(side=tk.LEFT)
        self.time_var = tk.StringVar(value="2")
        self.time_entry = ttk.Entry(time_frame, textvariable=self.time_var, width=5)
        self.time_entry.pack(side=tk.RIGHT)
        
        # 开始按钮
        self.start_button = ttk.Button(control_frame, text="开始游戏", command=self.start_game)
        self.start_button.pack(fill=tk.X, pady=5)
        
        # 重置按钮
        ttk.Button(control_frame, text="重置游戏", command=self.reset_game).pack(fill=tk.X, pady=5)
        
        # 串口设置
        serial_frame = ttk.LabelFrame(right_frame, text="串口设置")
        serial_frame.pack(fill=tk.X, pady=5)
        
        # 串口选择
        port_frame = ttk.Frame(serial_frame)
        port_frame.pack(fill=tk.X, pady=5)
        ttk.Label(port_frame, text="串口:").pack(side=tk.LEFT)
        self.port_combo = ttk.Combobox(port_frame, width=12)
        self.port_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        self.refresh_ports()
        
        # 波特率选择
        baud_frame = ttk.Frame(serial_frame)
        baud_frame.pack(fill=tk.X, pady=5)
        ttk.Label(baud_frame, text="波特率:").pack(side=tk.LEFT)
        self.baud_combo = ttk.Combobox(baud_frame, values=["9600", "19200", "38400", "57600", "115200"], width=12)
        self.baud_combo.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        self.baud_combo.set("115200")
        
        # 状态信息
        status_frame = ttk.LabelFrame(right_frame, text="游戏状态")
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_text = tk.Text(status_frame, height=10, width=30)
        self.status_text.pack(fill=tk.BOTH, expand=True)
        self.status_text.config(state=tk.DISABLED)
        
        # 刷新串口按钮
        ttk.Button(right_frame, text="刷新串口", command=self.refresh_ports).pack(fill=tk.X, pady=5)
        
        # 绘制棋盘
        self.draw_board()
    
    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo["values"] = ports
        if ports:
            self.port_combo.current(0)
    
    def draw_board(self):
        self.canvas.delete("all")
        cell_size = min(500 // self.board_size, 50)
        board_size = self.board_size
        
        # 绘制坐标轴标签 (0-based)
        for i in range(board_size):
            # 行坐标 (左侧)
            self.canvas.create_text(20, 30 + i * cell_size, text=str(i), font=("Arial", 10))
            # 列坐标 (顶部)
            self.canvas.create_text(50 + i * cell_size, 20, text=str(i), font=("Arial", 10))
        
        # 绘制网格线
        for i in range(board_size):
            # 横线
            self.canvas.create_line(40, 40 + i * cell_size, 
                                  40 + (board_size-1) * cell_size, 
                                  40 + i * cell_size)
            # 竖线
            self.canvas.create_line(40 + i * cell_size, 40, 
                                  40 + i * cell_size, 
                                  40 + (board_size-1) * cell_size)
        
        # 绘制棋子
        for i in range(board_size):
            for j in range(board_size):
                if self.board[i, j] == 1:  # 黑棋
                    self.draw_piece(j, i, "black")
                elif self.board[i, j] == 2:  # 白棋
                    self.draw_piece(j, i, "white")
    
    def draw_piece(self, x, y, color):
        cell_size = min(500 // self.board_size, 50)
        center_x = 40 + x * cell_size
        center_y = 40 + y * cell_size
        radius = cell_size * 0.4
        
        if color == "black":
            self.canvas.create_oval(center_x - radius, center_y - radius, 
                                  center_x + radius, center_y + radius, 
                                  fill="black", outline="black")
        else:  # white
            self.canvas.create_oval(center_x - radius, center_y - radius, 
                                  center_x + radius, center_y + radius, 
                                  fill="white", outline="black")
    
    def start_game(self):
        if self.game_started:
            return
            
        # 获取选择的颜色
        color = self.color_var.get()
        self.player_color = 1 if color == "black" else 2
        
        # 获取串口设置
        port = self.port_combo.get()
        if not port:
            messagebox.showerror("错误", "请选择串口")
            return
            
        try:
            self.baudrate = int(self.baud_combo.get())
        except ValueError:
            messagebox.showerror("错误", "波特率必须为整数")
            return
        
        # 获取稳定时间
        try:
            self.wait_time = float(self.time_var.get())
        except ValueError:
            messagebox.showerror("错误", "稳定时间必须是数字")
            return
        
        # 初始化游戏状态
        self.game_started = True
        self.start_button.config(state=tk.DISABLED)
        self.add_status("游戏开始!")
        self.add_status(f"我方为{'黑方' if self.player_color == 1 else '白方'}")
        
        # 创建并启动游戏线程
        game_thread = threading.Thread(target=self.game_loop, daemon=True)
        game_thread.start()
    
    def reset_game(self):
        self.board = np.zeros((self.board_size, self.board_size), dtype=int)
        self.turn_id = 1
        self.player_color = None
        self.last_board_state = np.zeros((self.board_size, self.board_size), dtype=int)
        self.game_started = False
        self.game_over = False
        self.is_first_move = True
        self.start_button.config(state=tk.NORMAL)
        
        # 清空状态文本
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.config(state=tk.DISABLED)
        
        # 重新初始化文件
        self.init_files()
        
        # 重新绘制棋盘
        self.draw_board()
        self.add_status("游戏已重置")
    
    def add_status(self, message):
        self.status_text.config(state=tk.NORMAL)
        self.status_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.status_text.see(tk.END)
        self.status_text.config(state=tk.DISABLED)
    
    def game_loop(self):
        # 根据玩家颜色初始化Con6Input.txt
        if self.player_color == 1:  # 黑方
            with open("Con6Input.txt", "w") as f:
                f.write("1\n-1 -1 -1 -1\n")
            self.add_status("初始化: 黑方先手")
        else:  # 白方
            self.add_status("等待对方先手...")
            # 等待Input.txt更新（第一步只有1个棋子）
            self.wait_for_input_update(expect_changes=1)
            
            # 获取新增的棋子 (0-based坐标)
            diff = np.where(self.board != self.last_board_state)
            if len(diff[0]) == 1:  # 只有一个新增棋子
                x, y = diff[1][0], diff[0][0]  # 0-based坐标
                with open("Con6Input.txt", "w") as f:
                    f.write("1\n{} {} -1 -1\n".format(x, y))
                self.add_status(f"记录对方落子: ({x}, {y})")
                self.last_board_state = self.board.copy()
                self.is_first_move = False  # 第一步完成
        
        # 主游戏循环
        while not self.game_over:
            self.add_status(f"回合 {self.turn_id} 开始")
            
            # 调用Connect6.exe
            self.add_status("调用Connect6.exe...")
            try:
                subprocess.run(['Connect6.exe'], check=True, timeout=60)
                self.add_status("Connect6.exe执行成功")
            except Exception as e:
                self.add_status(f"执行Connect6.exe失败: {str(e)}")
                messagebox.showerror("错误", f"执行Connect6.exe失败: {str(e)}")
                return
            
            # 读取Con6Output.txt
            try:
                with open("Con6Output.txt", "r") as f:
                    output = f.read().strip().split()
                    if len(output) < 4:
                        self.add_status("错误: Con6Output.txt格式不正确")
                        return
                    
                    coords = list(map(int, output[:4]))
                    self.add_status(f"AI推荐落子: ({coords[0]}, {coords[1]}) 和 ({coords[2]}, {coords[3]})")
            except Exception as e:
                self.add_status(f"读取Con6Output.txt失败: {str(e)}")
                return
            
            # 通过串口发送数据 - 严格按需求等待返回"1"
            self.add_status("通过串口发送落子数据...")
            try:
                # 创建串口连接（无限等待模式）
                ser = serial.Serial(
                    port=self.port_combo.get(),
                    baudrate=self.baudrate,
                    bytesize=self.bytesize,
                    parity=self.parity,
                    stopbits=self.stopbits,
                    timeout= 1 #None  # 无限等待模式
                )
                
                # 发送第一个和第二个坐标
                ser.write(f"{coords[0]} {coords[1]} {coords[2]} {coords[3]}\n".encode())
                self.add_status(f"发送坐标: {coords[0]} {coords[1]} {coords[2]} {coords[3]}")
                self.add_status("等待串口返回1...")
                
                # 无限等待返回"1"
                # while True:
                #     response = ser.readline().decode().strip()
                #     if response == "1":
                #         self.add_status("收到确认: 1")
                #         break
                
                # # 发送第二个坐标
                # ser.write(f"{coords[2]} {coords[3]}\n".encode())
                # self.add_status(f"发送坐标: {coords[2]} {coords[3]}")
                # self.add_status("等待串口返回1...")
                
                # 无限等待返回"1"
                while True:
                    response = ser.readline().decode().strip()
                    if response == "1":
                        self.add_status("收到确认: 1")
                        break
                
                ser.close()
            except Exception as e:
                self.add_status(f"串口通信失败: {str(e)}")
                # return
            
            # 确定预期变化数量（黑方第一步只下一颗棋子）
            if self.is_first_move and self.player_color == 1:
                expect_changes = 1
                self.is_first_move = False  # 第一步完成
            else:
                expect_changes = 2
            
            # 等待Input.txt更新（我方落子）
            self.add_status(f"等待我方落子更新，预期变化: {expect_changes}个棋子...")
            self.wait_for_input_update(expect_changes=expect_changes)
            
            # 获取新增的棋子 (0-based坐标)
            diff = np.where(self.board != self.last_board_state)
            num_changes = len(diff[0])
            
            if num_changes == 1:
                # 只更新了一个棋子（第一步）
                x1, y1 = diff[1][0], diff[0][0]  # 0-based坐标
                # 添加到Con6Input.txt（后两个为-1）
                with open("Con6Input.txt", "a") as f:
                    f.write(f"{x1} {y1} -1 -1\n")
                self.add_status(f"记录我方落子: ({x1}, {y1})")
            elif num_changes == 2:
                # 更新了两个棋子
                x1, y1 = diff[1][0], diff[0][0]  # 0-based坐标
                x2, y2 = diff[1][1], diff[0][1]  # 0-based坐标
                # 添加到Con6Input.txt
                with open("Con6Input.txt", "a") as f:
                    f.write(f"{x1} {y1} {x2} {y2}\n")
                self.add_status(f"记录我方落子: ({x1}, {y1}) 和 ({x2}, {y2})")
            else:
                self.add_status(f"错误：检测到{num_changes}个变化，预期1或2")
            
            self.last_board_state = self.board.copy()
            
            # 等待Input.txt更新（对方落子）
            # 对方落子总是2个棋子（除非是第一步且对方是黑方，但这种情况已在前面处理）
            expect_changes = 2
            self.add_status(f"等待对方落子，预期变化: {expect_changes}个棋子...")
            self.wait_for_input_update(expect_changes=expect_changes)
            
            # 获取新增的棋子 (0-based坐标)
            diff = np.where(self.board != self.last_board_state)
            num_changes = len(diff[0])
            
            if num_changes == 1:
                # 只更新了一个棋子（第一步）
                x1, y1 = diff[1][0], diff[0][0]  # 0-based坐标
                # 添加到Con6Input.txt（后两个为-1）
                with open("Con6Input.txt", "a") as f:
                    f.write(f"{x1} {y1} -1 -1\n")
                self.add_status(f"记录对方落子: ({x1}, {y1})")
            elif num_changes == 2:
                # 更新了两个棋子
                x1, y1 = diff[1][0], diff[0][0]  # 0-based坐标
                x2, y2 = diff[1][1], diff[0][1]  # 0-based坐标
                # 添加到Con6Input.txt
                with open("Con6Input.txt", "a") as f:
                    f.write(f"{x1} {y1} {x2} {y2}\n")
                self.add_status(f"记录对方落子: ({x1}, {y1}) 和 ({x2}, {y2})")
            else:
                self.add_status(f"错误：检测到{num_changes}个变化，预期1或2")
            
            self.last_board_state = self.board.copy()
            
            # 更新回合数
            self.turn_id += 1
            with open("Con6Input.txt", "r") as f:
                lines = f.readlines()
            
            if lines:
                lines[0] = f"{self.turn_id}\n"
                with open("Con6Input.txt", "w") as f:
                    f.writelines(lines)
            
            self.add_status(f"回合 {self.turn_id-1} 结束\n")
    
    def wait_for_input_update(self, expect_changes):
        """
        等待Input.txt更新，并检查变化是否符合要求：
        1. 连续t秒内棋盘不发生新的变化
        2. 当前棋盘比上一次记录的棋盘刚好多出指定数量的相同颜色棋子
        """
        self.add_status(f"等待棋盘更新，预期变化: {expect_changes}个棋子")
        last_change_time = time.time()
        last_content = self.read_input_file()
        stable_start = None
        
        while True:
            current_content = self.read_input_file()
            if current_content is None:
                time.sleep(0.1)
                continue
                
            # 检查内容是否发生变化
            if current_content != last_content:
                self.add_status("检测到文件变化，重置计时器")
                last_content = current_content
                last_change_time = time.time()
                stable_start = None  # 重置稳定计时
                continue
            
            # 如果内容没有变化，检查是否开始计时
            if stable_start is None:
                stable_start = time.time()
                self.add_status(f"开始稳定计时 ({self.wait_time}s)")
            
            # if time.time() - stable_start > 5:
            #     return  # 如果超过5秒没有变化，直接返回
            
            # 检查稳定时间是否达到要求
            if time.time() - stable_start >= self.wait_time:
                # 解析文件内容到棋盘
                self.update_board_from_file(current_content)
                
                # 计算棋盘变化
                diff = np.where(self.board != self.last_board_state)
                changed_positions = list(zip(diff[0], diff[1]))
                
                # 检查变化数量是否符合预期
                if len(changed_positions) != expect_changes:
                    self.add_status(f"变化数量不符: 预期 {expect_changes}, 实际 {len(changed_positions)}")
                    # 重置稳定计时
                    stable_start = time.time()
                    continue
                
                # 检查所有变化位置的棋子颜色是否相同
                colors = set()
                for i, j in changed_positions:
                    if self.board[i, j] != 0:  # 只考虑新增棋子
                        colors.add(self.board[i, j])
                
                if len(colors) != 1:
                    self.add_status(f"棋子颜色不一致: 找到 {len(colors)} 种颜色")
                    # 重置稳定计时
                    stable_start = time.time()
                    continue
                
                # 检查颜色是否有效
                color_value = colors.pop()
                if color_value not in (1, 2):
                    self.add_status(f"无效棋子颜色: {color_value}")
                    # 重置稳定计时
                    stable_start = time.time()
                    continue
                
                # 所有检查通过，更新棋盘
                self.add_status(f"检测到有效更新: {expect_changes}个{color_value}色棋子")
                self.root.after(0, self.draw_board)
                return
            
            # 检查是否超过最大等待时间（避免无限等待）
            if time.time() - last_change_time > 300:  # 5分钟超时
                self.add_status("等待更新超时")
                return
                
            time.sleep(0.1)  # 避免CPU占用过高
    
    def read_input_file(self):
        """读取Input.txt文件内容"""
        try:
            with open("Input.txt", "r") as f:
                return f.read()
        except Exception as e:
            self.add_status(f"读取Input.txt失败: {str(e)}")
            return None
    
    def update_board_from_file(self, content):
        """从文件内容更新棋盘状态 (0-based坐标系统)"""
        lines = content.strip().split("\n")
        if len(lines) != self.board_size:
            return
            
        for i, line in enumerate(lines):
            values = line.split()
            if len(values) != self.board_size:
                return
                
            for j, val in enumerate(values):
                try:
                    self.board[i, j] = int(val)
                except ValueError:
                    pass

if __name__ == "__main__":
    root = tk.Tk()
    app = Connect6App(root)
    root.mainloop()