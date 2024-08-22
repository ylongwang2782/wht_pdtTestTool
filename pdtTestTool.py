import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import json
import threading
import logging


class SerialTester:
    def __init__(self, root):
        self.root = root
        self.root.title("串口生产测试软件")

        # 设置日志系统
        logging.basicConfig(
            filename="serial_test_log.txt",
            level=logging.INFO,
            format="%(asctime)s - %(message)s",
        )

        # 串口配置部分
        self.port_label = ttk.Label(root, text="串口号:")
        self.port_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.port_combobox = ttk.Combobox(root, values=self.get_serial_ports())
        self.port_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        # 默认选择串口列表中的第一个
        self.port_combobox.current(0)

        self.baud_label = ttk.Label(root, text="波特率:")
        self.baud_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        self.baud_combobox = ttk.Combobox(
            root, values=[9600, 19200, 38400, 57600, 115200]
        )
        self.baud_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.baud_combobox.set(115200)  # 默认设置为115200

        self.refresh_button = ttk.Button(
            root, text="刷新串口", command=self.refresh_ports
        )
        self.refresh_button.grid(
            row=2, column=0, columnspan=2, padx=5, pady=5, sticky="ew"
        )

        self.connect_button = ttk.Button(
            root, text="连接", command=self.toggle_connection
        )
        self.connect_button.grid(
            row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew"
        )

        self.serial_connection = None

        # 创建测试表格
        self.tree = ttk.Treeview(
            root, columns=("序号", "测试项目", "测试结果"), show="headings"
        )
        self.tree.heading("序号", text="序号")
        self.tree.heading("测试项目", text="测试项目")
        self.tree.heading("测试结果", text="测试结果")
        self.tree.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

        # 添加测试项目
        self.test_cases = [
            {"序号": 1, "测试项目": "进入生产测试模式", "指令": {"PdtTest": "enter"}},
            {"序号": 2, "测试项目": "I2C数据收集", "指令": {"PdtTest": "I2C"}},
            {"序号": 3, "测试项目": "ADC数据测试", "指令": {"PdtTest": "ADC"}},
            {"序号": 4, "测试项目": "查询软件版本", "指令": {"PdtTest": "softver"}},
            {"序号": 5, "测试项目": "无线功能测试", "指令": {"PdtTest": "radio"}},
            {
                "序号": 6,
                "测试项目": "引脚映射表配置",
                "指令": {"pinMappingConfig": {"mapping": list(range(48))}},
            },
            {"序号": 7, "测试项目": "查询设备UID", "指令": {"PdtTest": "uid"}},
            {"序号": 8, "测试项目": "查询PinMap", "指令": {"PdtTest": "pinMap"}},
            {"序号": 9, "测试项目": "退出生产测试模式", "指令": {"PdtTest": "exit"}},
        ]

        for case in self.test_cases:
            self.tree.insert("", "end", values=(case["序号"], case["测试项目"], ""))

        self.tree.bind("<Double-1>", self.on_start_test)

        # 设置列和行的权重，使其在窗口大小调整时扩展
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(4, weight=1)

        self.data_refresh_button = ttk.Button(
            root, text="刷新检测数据", command=self.clear_test_results
        )
        self.data_refresh_button.grid(
            row=5, column=0, columnspan=2, padx=5, pady=5, sticky="ew"
        )

    def get_serial_ports(self):
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def refresh_ports(self):
        self.port_combobox["values"] = self.get_serial_ports()
        self.port_combobox.set("")  # 清空当前选择

    def toggle_connection(self):
        if self.serial_connection is None:
            self.connect_serial()
        else:
            self.disconnect_serial()

    def connect_serial(self):
        port = self.port_combobox.get()
        baudrate = int(self.baud_combobox.get())
        try:
            self.serial_connection = serial.Serial(port, baudrate, timeout=1)
            messagebox.showinfo("信息", "串口连接成功")
            self.connect_button.config(text="断开连接")
            logging.info(f"连接到串口: {port} 波特率: {baudrate}")
        except Exception as e:
            messagebox.showerror("错误", f"串口连接失败: {e}")
            logging.error(f"串口连接失败: {e}")

    def disconnect_serial(self):
        if self.serial_connection:
            self.serial_connection.close()
            self.serial_connection = None
            self.connect_button.config(text="连接")
            messagebox.showinfo("信息", "串口已断开")
            logging.info("串口已断开")

    def on_start_test(self, event):
        item = self.tree.selection()[0]
        values = self.tree.item(item, "values")
        case = next(
            (case for case in self.test_cases if case["序号"] == int(values[0])), None
        )

        if case:
            self.send_command(case, item)

    def send_command(self, case, item):
        if self.serial_connection is None:
            messagebox.showerror("错误", "请先连接串口")
            return

        command_json = json.dumps(case["指令"])

        def send_and_receive():
            self.serial_connection.write(command_json.encode())
            logging.info(f"发送指令: {command_json}")
            response = self.serial_connection.readline().decode().strip()
            logging.info(f"接收响应: {response}")
            self.process_response(response, item)

        threading.Thread(target=send_and_receive).start()

    def process_response(self, response, item):
        try:
            response_json = json.loads(response)
            result = response_json.get("result", "无效的响应")
            result_str = json.dumps(
                result, ensure_ascii=False, separators=(",", ":")
            ).replace("\n", " ")
            self.tree.set(item, column="测试结果", value=result_str)
        except json.JSONDecodeError:
            self.tree.set(item, column="测试结果", value="无效的响应")
            logging.error("无效的响应")

    def bind_events(self):
        self.tree.bind("<Double-1>", self.on_start_test)
        self.root.bind("<Control-c>", self.clear_test_results)  # 绑定清除结果的按键事件

    def clear_test_results(self):
        # 清除测试结果列
        for item in self.tree.get_children():
            self.tree.set(item, column="测试结果", value="")


if __name__ == "__main__":
    root = tk.Tk()
    app = SerialTester(root)
    root.mainloop()
