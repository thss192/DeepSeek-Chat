import flet as ft
from .client import DeepSeekClient
import threading
import requests
import json


class SettingsManager:
    def __init__(self, client: DeepSeekClient):
        self.client = client
        self.current_tab = 0
        self.page = None
        self.chat_view_ref = None  # 新增：聊天视图引用
        self._create_controls()

    def set_page(self, page):
        """设置页面引用"""
        self.page = page

    def set_chat_view_ref(self, chat_view):
        """设置聊天视图引用"""
        self.chat_view_ref = chat_view

    def _create_controls(self):
        """创建设置页面控件"""
        # API 设置控件
        field_style = {"border_color": "#4b5563", "focused_border_color": "#4f46e5"}
        self.api_key_field = ft.TextField(value=self.client.api_key, password=True, can_reveal_password=True,
                                          on_change=lambda e: self._on_config_change('api_key', e.control.value),
                                          label="API Key", expand=True, **field_style)

        self.api_base_url_field = ft.TextField(value=self.client.api_base_url, label="API 基础URL", expand=True,
                                               on_change=lambda e: self._on_config_change('api_base_url',
                                                                                          e.control.value),
                                               hint_text="https://api.deepseek.com/v1", **field_style)

        # 模型参数控件
        self.model_dropdown = ft.Dropdown(value=self.client.model, width=200, label="模型选择", **field_style,
                                          options=[ft.dropdown.Option("deepseek-chat", text="DeepSeek Chat"),
                                                   ft.dropdown.Option("deepseek-coder", text="DeepSeek Coder"),
                                                   ft.dropdown.Option("deepseek-reasoner", text="DeepSeek Reasoner")],
                                          on_change=lambda e: self._on_config_change('model', e.control.value))

        # 参数字段
        param_fields = [
            ('max_tokens', "最大生成长度", 120, ft.KeyboardType.NUMBER),
            ('temperature', "温度 (0-2)", 120, ft.KeyboardType.NUMBER, "0.0-2.0"),
            ('top_p', "Top P (0-1)", 120, ft.KeyboardType.NUMBER, "0.0-1.0"),
            ('frequency_penalty', "频率惩罚 (-2-2)", 140, ft.KeyboardType.NUMBER, "-2.0-2.0"),
            ('presence_penalty', "存在惩罚 (-2-2)", 140, ft.KeyboardType.NUMBER, "-2.0-2.0")
        ]

        self.max_tokens_field = self._create_param_field(*param_fields[0])
        self.temperature_field = self._create_param_field(*param_fields[1])
        self.top_p_field = self._create_param_field(*param_fields[2])
        self.frequency_penalty_field = self._create_param_field(*param_fields[3])
        self.presence_penalty_field = self._create_param_field(*param_fields[4])

        # 提示词设置
        self.system_prompt_field = ft.TextField(value=self.client.system_content, multiline=True, min_lines=2,
                                                max_lines=4,
                                                on_change=lambda e: self._on_config_change('system_content',
                                                                                           e.control.value),
                                                label="系统提示词", expand=True, **field_style)

        # 余额查询控件
        self.balance_status = ft.Text("点击查询余额", size=12, color="#d1d5db")
        self.balance_details = ft.Text("", size=12, color="#9ca3af")
        self.query_balance_button = ft.ElevatedButton("查询余额",
                                                      on_click=lambda e: self.query_balance(),
                                                      style=ft.ButtonStyle(color="#ffffff"),
                                                      bgcolor="#3b82f6")

        # 测试面板控件
        self.network_status = ft.Text("等待测试...", size=12, color="#d1d5db")
        self.api_status = ft.Text("等待测试...", size=12, color="#d1d5db")
        self.full_connection_status = ft.Text("等待测试...", size=12, color="#d1d5db")

        # 测试按钮
        button_style = ft.ButtonStyle(color="#ffffff")
        self.test_network_button = ft.ElevatedButton("测试网络连接", on_click=lambda e: self.test_network(),
                                                     style=button_style, bgcolor="#3b82f6")
        self.test_api_button = ft.ElevatedButton("测试API端点", on_click=lambda e: self.test_api(),
                                                 style=button_style, bgcolor="#8b5cf6")
        self.test_full_button = ft.ElevatedButton("完整连接测试", on_click=lambda e: self.test_full_connection(),
                                                  style=button_style, bgcolor="#10b981")
        self.save_settings_button = ft.ElevatedButton("保存设置", on_click=lambda e: self.client.save_config(),
                                                      style=button_style, bgcolor="#10b981")

        # 输入设置控件
        self.send_shortcut_field = ft.TextField(
            value=self.client.send_shortcut if hasattr(self.client, 'send_shortcut') else "Enter",
            label="发送快捷键",
            width=200,
            hint_text="Enter 或 Ctrl+Enter",
            **field_style
        )

        self.shortcut_status = ft.Text("", size=12, color="#d1d5db")
        self.test_shortcut_button = ft.ElevatedButton(
            "测试快捷键",
            on_click=lambda e: self.test_shortcut(),
            style=button_style,
            bgcolor="#f59e0b"
        )
        self.apply_shortcut_button = ft.ElevatedButton(
            "应用快捷键设置",
            on_click=lambda e: self.apply_shortcut_settings(),
            style=button_style,
            bgcolor="#10b981"
        )

    def _create_param_field(self, key, label, width, keyboard_type, hint_text=None):
        """创建参数输入字段"""
        return ft.TextField(value=str(getattr(self.client, key)), width=width, label=label,
                            on_change=lambda e: self._on_config_change(key, e.control.value),
                            keyboard_type=keyboard_type, hint_text=hint_text,
                            border_color="#4b5563", focused_border_color="#4f46e5")

    def _on_config_change(self, key, value):
        """配置变更处理"""
        if hasattr(self.client, key):
            if key in ['max_tokens']:
                try:
                    setattr(self.client, key, int(value))
                except ValueError:
                    pass
            elif key in ['temperature', 'top_p', 'frequency_penalty', 'presence_penalty']:
                try:
                    setattr(self.client, key, float(value))
                except ValueError:
                    pass
            else:
                setattr(self.client, key, value)
            self.client.save_config()

    def query_balance(self, e=None):
        """查询API余额"""
        self.balance_status.value = "查询中..."
        self.balance_status.color = "#fbbf24"
        self.balance_details.value = ""
        self.query_balance_button.disabled = True
        self.query_balance_button.text = "查询中..."
        if self.page:
            self.page.update()

        def query_in_thread():
            try:
                url = "https://api.deepseek.com/user/balance"
                headers = {
                    'Accept': 'application/json',
                    'Authorization': f'Bearer {self.client.api_key}'
                }

                response = requests.get(url, headers=headers, timeout=10)

                def update_ui():
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("is_available", False) and data.get("balance_infos"):
                            balance_info = data["balance_infos"][0]
                            self.balance_status.value = f"✅ 余额查询成功"
                            self.balance_status.color = "#10b981"

                            # 格式化余额信息
                            details = []
                            details.append(f"货币: {balance_info.get('currency', 'N/A')}")
                            details.append(f"总余额: {balance_info.get('total_balance', 'N/A')}")
                            details.append(f"赠送余额: {balance_info.get('granted_balance', 'N/A')}")
                            details.append(f"充值余额: {balance_info.get('topped_up_balance', 'N/A')}")

                            self.balance_details.value = "\n".join(details)
                        else:
                            self.balance_status.value = "❌ 余额信息不可用"
                            self.balance_status.color = "#ef4444"
                            self.balance_details.value = "API返回的余额信息不可用"
                    else:
                        try:
                            error_data = response.json()
                            error_msg = error_data.get("error", {}).get("message", "未知错误")
                            self.balance_status.value = "❌ 查询失败"
                            self.balance_status.color = "#ef4444"
                            self.balance_details.value = f"错误: {error_msg}"
                        except:
                            self.balance_status.value = f"❌ 请求失败 (HTTP {response.status_code})"
                            self.balance_status.color = "#ef4444"
                            self.balance_details.value = f"状态码: {response.status_code}"

                    self.query_balance_button.disabled = False
                    self.query_balance_button.text = "查询余额"
                    if self.page:
                        self.page.update()

                if self.page:
                    self.page.run_thread(update_ui)
                else:
                    update_ui()

            except requests.exceptions.Timeout:
                def update_timeout():
                    self.balance_status.value = "❌ 查询超时"
                    self.balance_status.color = "#ef4444"
                    self.balance_details.value = "请求超时，请检查网络连接"
                    self.query_balance_button.disabled = False
                    self.query_balance_button.text = "查询余额"
                    if self.page:
                        self.page.update()

                if self.page:
                    self.page.run_thread(update_timeout)
                else:
                    update_timeout()

            except requests.exceptions.ConnectionError:
                def update_connection_error():
                    self.balance_status.value = "❌ 连接失败"
                    self.balance_status.color = "#ef4444"
                    self.balance_details.value = "无法连接到API服务器"
                    self.query_balance_button.disabled = False
                    self.query_balance_button.text = "查询余额"
                    if self.page:
                        self.page.update()

                if self.page:
                    self.page.run_thread(update_connection_error)
                else:
                    update_connection_error()

            except Exception as e:
                def update_exception():
                    self.balance_status.value = "❌ 查询异常"
                    self.balance_status.color = "#ef4444"
                    self.balance_details.value = f"异常: {str(e)}"
                    self.query_balance_button.disabled = False
                    self.query_balance_button.text = "查询余额"
                    if self.page:
                        self.page.update()

                if self.page:
                    self.page.run_thread(update_exception)
                else:
                    update_exception()

        threading.Thread(target=query_in_thread, daemon=True).start()

    def _test_connection(self, test_type, status_field, button, test_func):
        """通用的连接测试方法"""
        status_field.value = "测试中..."
        status_field.color = "#fbbf24"
        button.disabled = True
        button.text = "测试中..."
        if self.page:
            self.page.update()

        def test_in_thread():
            success, message = test_func()

            def update_ui():
                status_field.value = "✅ " + message if success else "❌ " + message
                status_field.color = "#10b981" if success else "#ef4444"
                button.disabled = False
                button.text = button.text.replace("中...", "").replace("测试", "测试").replace("完整", "完整")
                if self.page:
                    self.page.update()

            if self.page:
                self.page.run_thread(update_ui)
            else:
                update_ui()

        threading.Thread(target=test_in_thread, daemon=True).start()

    def test_network(self, e=None):
        """测试网络连接"""

        def test_func():
            try:
                response = requests.get("https://www.baidu.com", timeout=10)
                return response.status_code == 200, "网络连接正常" if response.status_code == 200 else "网络连接异常"
            except requests.exceptions.Timeout:
                return False, "网络连接超时"
            except requests.exceptions.ConnectionError:
                return False, "网络连接失败"
            except Exception as e:
                return False, f"网络测试失败: {str(e)}"

        self._test_connection("network", self.network_status, self.test_network_button, test_func)

    def test_api(self, e=None):
        """测试API端点"""

        def test_func():
            try:
                response = requests.get("https://api.deepseek.com", timeout=10)
                return response.status_code in [200, 401, 403, 404], "API端点可达" if response.status_code in [200, 401,
                                                                                                               403,
                                                                                                               404] else "API端点不可达"
            except requests.exceptions.Timeout:
                return False, "API端点连接超时"
            except requests.exceptions.ConnectionError:
                return False, "无法连接到API端点"
            except Exception as e:
                return False, f"API端点测试失败: {str(e)}"

        self._test_connection("api", self.api_status, self.test_api_button, test_func)

    def test_full_connection(self, e=None):
        """完整连接测试"""

        def test_func():
            return self.client.test_connection()

        self._test_connection("full", self.full_connection_status, self.test_full_button, test_func)

    def test_shortcut(self, e=None):
        """测试快捷键设置"""
        shortcut = self.send_shortcut_field.value.strip()
        if not shortcut:
            self.shortcut_status.value = "❌ 请输入快捷键"
            self.shortcut_status.color = "#ef4444"
        elif shortcut.lower() in ["enter", "ctrl+enter"]:
            self.shortcut_status.value = f"✅ 快捷键设置为: {shortcut}"
            self.shortcut_status.color = "#10b981"
        else:
            self.shortcut_status.value = "❌ 只支持 Enter 或 Ctrl+Enter"
            self.shortcut_status.color = "#ef4444"

        if self.page:
            self.page.update()

    def apply_shortcut_settings(self, e=None):
        """应用快捷键设置"""
        shortcut = self.send_shortcut_field.value.strip()
        if shortcut.lower() in ["enter", "ctrl+enter"]:
            # 保存到客户端配置
            if not hasattr(self.client, 'send_shortcut'):
                # 如果客户端还没有这个属性，需要先添加
                self.client.send_shortcut = shortcut
            else:
                self.client.send_shortcut = shortcut

            # 保存配置
            self.client.save_config()

            self.shortcut_status.value = f"✅ 快捷键设置已应用: {shortcut}"
            self.shortcut_status.color = "#10b981"

            # 通知聊天视图更新显示
            if self.chat_view_ref:
                self.chat_view_ref.update_shortcut_display()

        else:
            self.shortcut_status.value = "❌ 只支持 Enter 或 Ctrl+Enter"
            self.shortcut_status.color = "#ef4444"

        if self.page:
            self.page.update()

    def create_settings_tab(self):
        """创建设置标签页UI"""
        tabs = ft.Tabs(
            selected_index=self.current_tab,
            on_change=self._on_tab_change,
            expand=True,
            tabs=[
                ft.Tab(text="参数设置", content=self._create_settings_panel()),
                ft.Tab(text="输入设置", content=self._create_input_settings_panel()),  # 新增输入设置标签页
                ft.Tab(text="连接测试", content=self._create_test_panel())
            ]
        )
        return ft.Container(content=tabs, expand=True, bgcolor="#111827")

    def _on_tab_change(self, e):
        self.current_tab = e.control.selected_index

    def _create_settings_panel(self):
        """创建参数设置面板"""
        return ft.Container(
            content=ft.Column([
                ft.Text("参数设置", size=20, weight="bold", color="#e5e7eb", text_align=ft.TextAlign.CENTER),
                ft.Divider(color="#374151"),
                ft.Text("API 设置", size=16, weight="bold", color="#e5e7eb"),
                self.api_key_field,
                self.api_base_url_field,
                ft.Divider(color="#374151"),
                ft.Text("模型参数", size=16, weight="bold", color="#e5e7eb"),
                ft.Row([self.model_dropdown, self.max_tokens_field], spacing=10),
                ft.Row([self.temperature_field, self.top_p_field], spacing=10),
                ft.Row([self.frequency_penalty_field, self.presence_penalty_field], spacing=10),
                ft.Divider(color="#374151"),
                ft.Text("提示词设置", size=16, weight="bold", color="#e5e7eb"),
                self.system_prompt_field,
                ft.Divider(color="#374151"),
                ft.Row([ft.Container(expand=True), self.save_settings_button]),
            ], spacing=15, scroll=ft.ScrollMode.ADAPTIVE),
            padding=20, bgcolor="#1f2937", border_radius=12, border=ft.border.all(1, "#374151"), margin=10, expand=True
        )

    def _create_input_settings_panel(self):
        """创建输入设置面板"""
        return ft.Container(
            content=ft.Column([
                ft.Text("输入设置", size=20, weight="bold", color="#e5e7eb", text_align=ft.TextAlign.CENTER),
                ft.Divider(color="#374151"),

                ft.Text("发送快捷键设置", size=16, weight="bold", color="#e5e7eb"),
                ft.Row([
                    self.send_shortcut_field,
                    self.test_shortcut_button,
                    self.apply_shortcut_button
                ], spacing=10),
                ft.Container(content=self.shortcut_status, padding=ft.padding.only(top=5)),
                ft.Text("设置消息发送的快捷键：Enter 或 Ctrl+Enter", size=12, color="#9ca3af"),

                ft.Divider(color="#374151"),

                ft.Text("其他输入设置", size=16, weight="bold", color="#e5e7eb"),
                ft.Text("更多输入相关设置将在后续版本中添加...", size=14, color="#d1d5db"),

            ], spacing=15, scroll=ft.ScrollMode.ADAPTIVE),
            padding=20, bgcolor="#1f2937", border_radius=12, border=ft.border.all(1, "#374151"), margin=10, expand=True
        )

    def _create_test_panel(self):
        """创建连接测试面板"""
        return ft.Container(
            content=ft.Column([
                ft.Text("连接测试", size=20, weight="bold", color="#e5e7eb", text_align=ft.TextAlign.CENTER),
                ft.Divider(color="#374151"),

                # 余额查询部分
                ft.Text("API余额查询", size=16, weight="bold", color="#e5e7eb"),
                ft.Row([self.query_balance_button,
                        ft.Container(content=self.balance_status, expand=True, padding=ft.padding.only(left=10))],
                       spacing=10),
                ft.Container(content=self.balance_details, padding=ft.padding.only(top=5)),
                ft.Text("查询DeepSeek API账户余额信息", size=12, color="#9ca3af"),
                ft.Divider(color="#374151"),

                ft.Text("网络连接测试", size=16, weight="bold", color="#e5e7eb"),
                ft.Row([self.test_network_button,
                        ft.Container(content=self.network_status, expand=True, padding=ft.padding.only(left=10))],
                       spacing=10),
                ft.Text("测试基础网络连通性", size=12, color="#9ca3af"),
                ft.Divider(color="#374151"),
                ft.Text("API端点测试", size=16, weight="bold", color="#e5e7eb"),
                ft.Row([self.test_api_button,
                        ft.Container(content=self.api_status, expand=True, padding=ft.padding.only(left=10))],
                       spacing=10),
                ft.Text("测试DeepSeek API服务器可达性", size=12, color="#9ca3af"),
                ft.Divider(color="#374151"),
                ft.Text("完整连接测试", size=16, weight="bold", color="#e5e7eb"),
                ft.Row([self.test_full_button,
                        ft.Container(content=self.full_connection_status, expand=True,
                                     padding=ft.padding.only(left=10))], spacing=10),
                ft.Text("包含API Key验证的完整功能测试", size=12, color="#9ca3af"),
            ], spacing=15, scroll=ft.ScrollMode.ADAPTIVE),
            padding=20, bgcolor="#1f2937", border_radius=12, border=ft.border.all(1, "#374151"), margin=10, expand=True
        )

    def refresh_settings(self):
        """刷新设置界面显示的值"""
        self.api_key_field.value = self.client.api_key
        self.api_base_url_field.value = self.client.api_base_url
        self.model_dropdown.value = self.client.model
        self.max_tokens_field.value = str(self.client.max_tokens)
        self.temperature_field.value = str(self.client.temperature)
        self.top_p_field.value = str(self.client.top_p)
        self.frequency_penalty_field.value = str(self.client.frequency_penalty)
        self.presence_penalty_field.value = str(self.client.presence_penalty)
        self.system_prompt_field.value = self.client.system_content

        # 刷新快捷键设置
        if hasattr(self.client, 'send_shortcut'):
            self.send_shortcut_field.value = self.client.send_shortcut
        else:
            self.send_shortcut_field.value = "Enter"