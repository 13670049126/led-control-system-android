from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.groupbox import GroupBox
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.uix.spinner import Spinner
from kivy.uix.slider import Slider
from kivy.uix.textbrowser import TextBrowser
from kivy.clock import Clock
from kivy.properties import StringProperty, ObjectProperty, ListProperty
from kivy.graphics import Color, Rectangle
import time
import os
import numpy as np
# 尝试导入串口模块，Android上可能无法使用
try:
    import serial
    import serial.tools.list_ports
    HAS_SERIAL = True
except ImportError:
    serial = None
    serial.tools = None
    HAS_SERIAL = False
import json

CONFIG_FILE = 'config.json'

class ColorButton(Button):
    """自定义颜色按钮类"""
    pass

class LEDControlApp(App):
    """LED灯条控制系统的Kivy应用"""
    
    # 状态属性
    connection_status = StringProperty("状态：未连接")
    current_time = StringProperty("")
    log_text = StringProperty("")
    
    def build(self):
        """构建应用UI"""
        self.title = "LED灯条控制系统"
        
        # 初始化变量
        self.ser = None
        if HAS_SERIAL:
            self.ser = serial.Serial()
        self.TimeCount = 0
        self.LastTime = 0
        self.waterfall_offset = 0
        
        # 灯条设置初始化
        self.D1 = 11
        self.D2 = 20
        self.D3 = 11
        self.D4 = 15
        
        # 流水灯相关初始化
        self.waterfall_speed = 1
        self.waterfall_color_mode = 0
        
        # 自定义颜色初始化
        self.custom_color = [255, 0, 0]  # 默认红色
        
        # 复选框状态
        self.check_run = True
        self.check_test = True
        self.check_waterfall = True
        
        # 加载配置
        self.load_config()
        
        # 启动时钟
        Clock.schedule_interval(self.update_time, 1)
        Clock.schedule_once(self.port_check, 0.1)
        Clock.schedule_once(self.ShotAndSendThread, 0.2)
        
        return self.create_main_layout()
    
    def create_main_layout(self):
        """创建主布局"""
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # 标题
        title_label = Label(
            text="（华浦科技）LED灯条控制系统",
            font_size='24sp',
            bold=True,
            color=[0.298, 0.804, 0.765, 1],
            size_hint_y=None,
            height=50
        )
        main_layout.add_widget(title_label)
        
        # 上半部分布局
        top_layout = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=250)
        
        # 左侧：串口和灯条设置
        left_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_x=0.5)
        
        # 串口设置组
        serial_group = GroupBox(title="串口设置", padding=10)
        serial_layout = GridLayout(cols=4, spacing=5, size_hint_y=None, height=50)
        
        serial_layout.add_widget(Label(text="串口选择:"))
        
        self.combo_serial = Spinner(
            text='COM1',
            values=['COM1'],
            size_hint=(None, 1),
            width=100
        )
        serial_layout.add_widget(self.combo_serial)
        
        self.btn_connect = Button(
            text="连接",
            size_hint=(None, 1),
            width=100,
            background_color=[0.055, 0.388, 0.612, 1]
        )
        self.btn_connect.bind(on_press=self.open_port)
        serial_layout.add_widget(self.btn_connect)
        
        self.label_status = Label(text=self.connection_status)
        serial_layout.add_widget(self.label_status)
        
        serial_group.add_widget(serial_layout)
        left_layout.add_widget(serial_group)
        
        # 灯条设置组
        light_group = GroupBox(title="灯条设置", padding=10)
        light_layout = GridLayout(cols=4, spacing=5, size_hint_y=None, height=80)
        
        light_layout.add_widget(Label(text="左侧灯珠数:"))
        self.spin_d1 = Spinner(
            text=str(self.D1),
            values=[str(i) for i in range(1, 50)],
            size_hint=(None, 1),
            width=80
        )
        self.spin_d1.bind(text=self.on_d1_change)
        light_layout.add_widget(self.spin_d1)
        
        light_layout.add_widget(Label(text="上侧灯珠数:"))
        self.spin_d2 = Spinner(
            text=str(self.D2),
            values=[str(i) for i in range(1, 50)],
            size_hint=(None, 1),
            width=80
        )
        self.spin_d2.bind(text=self.on_d2_change)
        light_layout.add_widget(self.spin_d2)
        
        light_layout.add_widget(Label(text="右侧灯珠数:"))
        self.spin_d3 = Spinner(
            text=str(self.D3),
            values=[str(i) for i in range(1, 50)],
            size_hint=(None, 1),
            width=80
        )
        self.spin_d3.bind(text=self.on_d3_change)
        light_layout.add_widget(self.spin_d3)
        
        light_layout.add_widget(Label(text="下侧灯珠数:"))
        self.spin_d4 = Spinner(
            text=str(self.D4),
            values=[str(i) for i in range(1, 50)],
            size_hint=(None, 1),
            width=80
        )
        self.spin_d4.bind(text=self.on_d4_change)
        light_layout.add_widget(self.spin_d4)
        
        light_group.add_widget(light_layout)
        left_layout.add_widget(light_group)
        
        top_layout.add_widget(left_layout)
        
        # 右侧：控制选项
        right_layout = BoxLayout(orientation='vertical', spacing=10, size_hint_x=0.5)
        
        # 运行设置组
        run_group = GroupBox(title="运行设置", padding=10)
        run_layout = BoxLayout(orientation='vertical', spacing=5)
        
        # 运行复选框
        self.check_run_box = CheckBox(active=self.check_run)
        run_layout.add_widget(self.create_checkbox_row("启动（默认运行流光溢彩）", self.check_run_box, self.on_run_check))
        
        # 测试模式复选框
        self.check_test_box = CheckBox(active=self.check_test)
        run_layout.add_widget(self.create_checkbox_row("灯条控制", self.check_test_box, self.on_test_check))
        
        # 颜色选择
        color_layout = BoxLayout(orientation='horizontal', spacing=5, size_hint_y=None, height=80)
        
        # 颜色选择器按钮
        self.btn_color_picker = Button(
            text="色彩盘",
            background_color=[1, 0, 0, 1],
            size_hint=(None, 1),
            width=80
        )
        self.btn_color_picker.bind(on_press=self.open_color_dialog)
        color_layout.add_widget(self.btn_color_picker)
        
        # 预设颜色按钮
        preset_colors = [
            [1, 0, 0, 1],  # 红色
            [0, 1, 0, 1],  # 绿色
            [0, 0, 1, 1],  # 蓝色
            [1, 1, 0, 1],  # 黄色
            [1, 0, 1, 1],  # 品红
            [0, 1, 1, 1]   # 青色
        ]
        
        preset_layout = GridLayout(cols=3, spacing=5)
        for i, color in enumerate(preset_colors):
            btn = ColorButton(
                background_color=color,
                size_hint=(None, None),
                size=(30, 30)
            )
            btn.bind(on_press=lambda instance, color=color: self.set_preset_color(color))
            preset_layout.add_widget(btn)
        
        color_layout.add_widget(preset_layout)
        run_layout.add_widget(color_layout)
        
        run_group.add_widget(run_layout)
        right_layout.add_widget(run_group)
        
        # 流水灯设置组
        waterfall_group = GroupBox(title="流水灯设置", padding=10)
        waterfall_layout = BoxLayout(orientation='vertical', spacing=5)
        
        # 流水灯复选框
        self.check_waterfall_box = CheckBox(active=self.check_waterfall)
        waterfall_layout.add_widget(self.create_checkbox_row("流水灯", self.check_waterfall_box, self.on_waterfall_check))
        
        # 颜色模式
        mode_layout = BoxLayout(orientation='horizontal', spacing=5, size_hint_y=None, height=40)
        mode_layout.add_widget(Label(text="颜色模式:"))
        self.spin_color_mode = Spinner(
            text="彩虹色渐变",
            values=["彩虹色渐变", "单色模式", "多彩渐变"],
            size_hint=(1, 1)
        )
        self.spin_color_mode.bind(text=self.on_color_mode_change)
        mode_layout.add_widget(self.spin_color_mode)
        waterfall_layout.add_widget(mode_layout)
        
        # 流水灯速度
        speed_layout = BoxLayout(orientation='horizontal', spacing=5, size_hint_y=None, height=40)
        speed_layout.add_widget(Label(text="流水速度:"))
        self.slider_speed = Slider(
            min=1,
            max=10,
            value=self.waterfall_speed,
            size_hint=(0.7, 1)
        )
        self.slider_speed.bind(value=self.on_speed_change)
        speed_layout.add_widget(self.slider_speed)
        self.label_speed = Label(text=str(self.waterfall_speed), size_hint=(0.1, 1))
        speed_layout.add_widget(self.label_speed)
        waterfall_layout.add_widget(speed_layout)
        
        # 测试按钮
        self.btn_test = Button(
            text="测试效果",
            background_color=[0.807, 0.565, 0.471, 1],
            size_hint_y=None,
            height=40
        )
        self.btn_test.bind(on_press=self.on_test_press)
        waterfall_layout.add_widget(self.btn_test)
        
        waterfall_group.add_widget(waterfall_layout)
        right_layout.add_widget(waterfall_group)
        
        top_layout.add_widget(right_layout)
        main_layout.add_widget(top_layout)
        
        # 日志区域
        log_group = GroupBox(title="日志信息", padding=10)
        log_layout = GridLayout(cols=2, spacing=5, size_hint_y=None, height=40)
        
        self.label_time = Label(text=self.current_time)
        log_layout.add_widget(self.label_time)
        
        self.label_run_status = Label(text="消息日志：")
        log_layout.add_widget(self.label_run_status)
        
        self.text_log = TextBrowser(size_hint_y=1)
        
        log_group.add_widget(log_layout)
        log_group.add_widget(self.text_log)
        main_layout.add_widget(log_group)
        
        return main_layout
    
    def create_checkbox_row(self, text, checkbox, callback):
        """创建带标签的复选框行"""
        layout = BoxLayout(orientation='horizontal', spacing=5, size_hint_y=None, height=30)
        layout.add_widget(checkbox)
        label = Label(text=text, size_hint_x=1, halign='left', valign='middle')
        label.bind(size=label.setter('text_size'))
        layout.add_widget(label)
        checkbox.bind(active=callback)
        return layout
    
    def update_time(self, dt):
        """更新当前时间"""
        self.current_time = time.strftime('%Y年%m月%d日 %H:%M:%S', time.localtime())
        self.label_time.text = self.current_time
    
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                
                # 加载灯条设置
                self.D1 = config.get('D1', 11)
                self.D2 = config.get('D2', 20)
                self.D3 = config.get('D3', 11)
                self.D4 = config.get('D4', 15)
                
                # 加载颜色模式
                self.waterfall_color_mode = config.get('color_mode', 0)
                
                # 加载流水灯速度
                self.waterfall_speed = config.get('waterfall_speed', 5)
                
                # 加载复选框状态
                self.check_run = config.get('check_run', True)
                self.check_test = config.get('check_test', True)
                self.check_waterfall = config.get('check_waterfall', True)
                
                # 加载自定义颜色
                color_data = config.get('custom_color', {'r': 255, 'g': 0, 'b': 0})
                self.custom_color = [color_data['r'], color_data['g'], color_data['b']]
                
                self.log("配置加载成功", 0)
            except Exception as e:
                self.log(f"加载配置失败: {e}", 1)
        else:
            self.log("配置文件不存在，使用默认配置", 0)
    
    def save_config(self):
        """保存配置到文件"""
        config = {
            'D1': self.D1,
            'D2': self.D2,
            'D3': self.D3,
            'D4': self.D4,
            'color_mode': self.waterfall_color_mode,
            'waterfall_speed': self.waterfall_speed,
            'check_run': self.check_run,
            'check_test': self.check_test,
            'check_waterfall': self.check_waterfall,
            'custom_color': {
                'r': self.custom_color[0],
                'g': self.custom_color[1],
                'b': self.custom_color[2]
            }
        }
        
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
            self.log("配置保存成功", 0)
        except Exception as e:
            self.log(f"保存配置失败: {e}", 1)
    
    def log(self, message, error_level=0):
        """记录日志"""
        str_nowtime = time.strftime('%H:%M:%S', time.localtime())
        if error_level == 1:
            log_entry = f"[color=ff0000]{message}  @{str_nowtime}[/color]"
        elif error_level == 2:
            log_entry = f"[color=00ff00]{message}  @{str_nowtime}[/color]"
        else:
            log_entry = f"[color=ffffff]{message}  @{str_nowtime}[/color]"
        
        self.text_log.text += log_entry + "\n"
        self.text_log.scroll_to(self.text_log)
    
    def port_check(self, dt):
        """检测串口"""
        if HAS_SERIAL:
            try:
                port_list = list(serial.tools.list_ports.comports())
                ports = [port[0] for port in port_list]
                
                if ports:
                    self.combo_serial.values = ports
                    self.combo_serial.text = ports[0]
                else:
                    self.combo_serial.values = ['无可用串口']
                    self.combo_serial.text = '无可用串口'
            except Exception as e:
                self.log(f"串口检测错误: {e}", 1)
                self.combo_serial.values = ['串口不可用']
                self.combo_serial.text = '串口不可用'
        else:
            self.combo_serial.values = ['串口功能不可用']
            self.combo_serial.text = '串口功能不可用'
            self.log("当前平台不支持串口功能", 1)
        
        # 每秒刷新一次串口列表
        Clock.schedule_once(self.port_check, 1.0)
    
    def open_port(self, instance):
        """打开或关闭串口"""
        if not HAS_SERIAL:
            self.log("当前平台不支持串口功能", 1)
            return
        
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
                self.connection_status = "状态：已断开"
                self.btn_connect.text = "连接"
                self.label_status.text = self.connection_status
                self.log("关闭串口成功", 0)
            else:
                self.ser.port = self.combo_serial.text
                self.ser.baudrate = 115200
                self.ser.bytesize = 8
                self.ser.parity = 'N'
                self.ser.stopbits = 1
                self.ser.open()
                self.connection_status = "状态：已连接"
                self.btn_connect.text = "断开"
                self.label_status.text = self.connection_status
                self.log("打开串口成功", 0)
        except Exception as e:
            self.log(f"串口操作失败: {e}", 1)
            self.connection_status = "状态：未连接"
            self.label_status.text = self.connection_status
    
    def ShotAndSendThread(self, dt):
        """主功能线程"""
        try:
            fps = round(1 / (time.time() - self.LastTime), 2) if self.LastTime > 0 else 0
            # self.log(f"FPS: {fps}", 0)
        except Exception:
            pass
        self.LastTime = time.time()
        
        if not self.check_run:
            # 1秒后再次执行
            Clock.schedule_once(self.ShotAndSendThread, 1.0)
            return
        
        # 获取上下左右四个方向所设置的灯珠数量
        d1 = self.D1
        d2 = self.D2
        d3 = self.D3
        d4 = self.D4
        total_len = d1 + d2 + d3 + d4
        
        sendrgb = np.zeros((total_len + 1) * 3, dtype=np.uint8)
        sendrgb[0] = 0x28
        sendrgb[1] = total_len // 256
        sendrgb[2] = total_len % 256
        
        if self.check_test:
            if self.check_waterfall:
                # 生成流水灯效果
                for i in range(total_len):
                    offset = (i + self.waterfall_offset) % total_len
                    
                    if self.waterfall_color_mode == 0:  # 彩虹色渐变
                        r = int(255 * (1 + np.sin(np.pi * 2 * offset / total_len)) / 2)
                        g = int(255 * (1 + np.sin(np.pi * 2 * (offset / total_len + 1/3))) / 2)
                        b = int(255 * (1 + np.sin(np.pi * 2 * (offset / total_len + 2/3))) / 2)
                    elif self.waterfall_color_mode == 1:  # 单色模式
                        r, g, b = self.custom_color
                    else:  # 多彩渐变模式
                        r = int(255 * (1 + np.sin(np.pi * 2 * offset / total_len * 2)) / 2)
                        g = int(255 * (1 + np.sin(np.pi * 2 * (offset / total_len * 3 + 0.5))) / 2)
                        b = int(255 * (1 + np.sin(np.pi * 2 * (offset / total_len * 4 + 1))) / 2)
                    
                    sendrgb[3 + i*3] = g     # RGB顺序是G、R、B
                    sendrgb[3 + i*3 + 1] = r
                    sendrgb[3 + i*3 + 2] = b
                
                # 更新流水灯偏移量
                self.waterfall_offset = (self.waterfall_offset + self.waterfall_speed) % total_len
            else:  # 普通单色测试模式
                r, g, b = self.custom_color
                for i in range(total_len):
                    sendrgb[3 + i*3] = g     # RGB顺序是G、R、B
                    sendrgb[3 + i*3 + 1] = r
                    sendrgb[3 + i*3 + 2] = b
        else:   # 正常工作模式，这里简化处理，因为Android上无法直接截图
            # 在Android上，我们需要使用其他方式获取图像，这里暂时使用测试模式的逻辑
            r, g, b = self.custom_color
            for i in range(total_len):
                sendrgb[3 + i*3] = g
                sendrgb[3 + i*3 + 1] = r
                sendrgb[3 + i*3 + 2] = b
        
        if HAS_SERIAL and self.ser and self.ser.is_open:
            self.uart_send_cmd(sendrgb)
        
        # 短时间后再次执行
        Clock.schedule_once(self.ShotAndSendThread, 0.01)
    
    def uart_send_cmd(self, cmd):
        """发送数据到串口"""
        if HAS_SERIAL and self.ser and self.ser.is_open:
            try:
                self.ser.write(cmd)
            except Exception as e:
                self.log(f"串口发送错误: {e}", 1)
    
    def on_test_press(self, instance):
        """测试按钮按下事件"""
        self.log("测试按钮按下", 0)
        # 这里可以添加测试逻辑
    
    def on_d1_change(self, instance, value):
        """左侧灯珠数变化事件"""
        self.D1 = int(value)
        self.save_config()
    
    def on_d2_change(self, instance, value):
        """上侧灯珠数变化事件"""
        self.D2 = int(value)
        self.save_config()
    
    def on_d3_change(self, instance, value):
        """右侧灯珠数变化事件"""
        self.D3 = int(value)
        self.save_config()
    
    def on_d4_change(self, instance, value):
        """下侧灯珠数变化事件"""
        self.D4 = int(value)
        self.save_config()
    
    def on_run_check(self, instance, value):
        """运行复选框变化事件"""
        self.check_run = value
        self.save_config()
    
    def on_test_check(self, instance, value):
        """测试模式复选框变化事件"""
        self.check_test = value
        self.save_config()
    
    def on_waterfall_check(self, instance, value):
        """流水灯复选框变化事件"""
        self.check_waterfall = value
        self.save_config()
    
    def on_color_mode_change(self, instance, value):
        """颜色模式变化事件"""
        color_modes = {
            "彩虹色渐变": 0,
            "单色模式": 1,
            "多彩渐变": 2
        }
        self.waterfall_color_mode = color_modes[value]
        self.save_config()
    
    def on_speed_change(self, instance, value):
        """流水灯速度变化事件"""
        self.waterfall_speed = int(value)
        self.label_speed.text = str(self.waterfall_speed)
        self.save_config()
    
    def open_color_dialog(self, instance):
        """打开颜色选择对话框（简化版）"""
        # 在Kivy中，我们可以使用ColorPicker，但为了简单起见，这里我们使用预设颜色
        self.log("颜色选择功能将在完整版本中实现", 0)
    
    def set_preset_color(self, color):
        """设置预设颜色"""
        self.custom_color = [int(c * 255) for c in color[:3]]
        self.btn_color_picker.background_color = color
        self.log(f"已设置预设颜色: R={self.custom_color[0]}, G={self.custom_color[1]}, B={self.custom_color[2]}", 0)
        self.save_config()

if __name__ == '__main__':
    LEDControlApp().run()
