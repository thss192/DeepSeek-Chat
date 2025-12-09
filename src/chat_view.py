import flet as ft
import uuid
from .client import DeepSeekClient


class ChatView:
    def __init__(self, client: DeepSeekClient, title_update_callback=None):
        self.client = client
        self.title_update_callback = title_update_callback
        self.current_responses = {}  # 改为字典，存储每个消息ID对应的响应内容
        self.is_streaming = False
        self.current_conversation_name = "新的对话"
        self.chat_container = None
        self.page = None
        self.current_message_id = None
        self._create_controls()

    def _create_controls(self):
        """创建聊天相关的UI控件"""
        self.conversation_title = ft.Text(self.current_conversation_name, size=16, weight="bold", color="#f8fafc")

        self.chat_display = ft.ListView(expand=True, spacing=1, auto_scroll=True, padding=5)

        try:
            self.welcome_icon = ft.Image(src="../asset/icon.png", width=120, height=120, fit=ft.ImageFit.CONTAIN)
        except Exception:
            self.welcome_icon = ft.Icon(name=ft.icons.SMART_TOY_OUTLINED, size=80, color="#6366f1")

        self.welcome_container = ft.Container(
            content=ft.Column([
                self.welcome_icon,
                ft.Text("欢迎使用 DeepSeek Chat", size=24, weight="bold", color="#e2e8f0"),
                ft.Text("开始与AI助手对话吧！", size=16, color="#94a3b8")
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER, spacing=20),
            expand=True, alignment=ft.alignment.center, visible=True, bgcolor="#0f172a"
        )

        # 动态设置提示文本
        self._update_input_hint()

        self.input_field = ft.TextField(
            multiline=True, min_lines=1, max_lines=4, expand=True,
            hint_text=self.current_hint_text, border_color="transparent",
            focused_border_color="transparent", content_padding=12, cursor_color="#6366f1",
            cursor_width=2, text_style=ft.TextStyle(color="#f1f5f9", size=14),
            hint_style=ft.TextStyle(color="#94a3b8", size=14), bgcolor="#1e293b", border_radius=12
        )

        self.send_stop_button = ft.ElevatedButton(
            "发送", style=ft.ButtonStyle(color="#ffffff", bgcolor="#6366f1",
                                         padding=ft.padding.symmetric(horizontal=16, vertical=8),
                                         overlay_color="#4f46e5"), height=36
        )

        self.new_chat_button = ft.ElevatedButton(
            "新建对话", style=ft.ButtonStyle(color="#e2e8f0", bgcolor="#475569",
                                             padding=ft.padding.symmetric(horizontal=12, vertical=6),
                                             overlay_color="#334155"), height=32
        )

        self.input_field.on_submit = lambda e: self.send_message()
        self.send_stop_button.on_click = lambda e: self.send_message()
        self.new_chat_button.on_click = lambda e: self.new_conversation()

    def _update_input_hint(self):
        """更新输入框提示文本"""
        shortcut = getattr(self.client, 'send_shortcut', 'Enter')
        self.current_hint_text = f"输入消息... ({shortcut}发送)"

    def update_shortcut_display(self):
        """更新快捷键显示（供外部调用）"""
        self._update_input_hint()
        if self.input_field:
            self.input_field.hint_text = self.current_hint_text
            if self.page:
                self.input_field.update()

    def create_chat_tab(self, page: ft.Page):
        """创建聊天标签页"""
        self.page = page
        self.chat_container = ft.Container(content=self.chat_display, expand=True, bgcolor="#0f172a", padding=0,
                                           margin=0, visible=False)

        input_container = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=self.input_field, expand=True, border_radius=12,
                    border=ft.border.all(1, "rgba(99, 102, 241, 0.3)"),
                    shadow=ft.BoxShadow(spread_radius=1, blur_radius=8, color="rgba(0, 0, 0, 0.3)",
                                        offset=ft.Offset(0, 2), blur_style=ft.ShadowBlurStyle.OUTER)
                ), self.send_stop_button
            ], spacing=12),
            padding=12, bgcolor="rgba(30, 41, 59, 0.9)", border_radius=0, margin=0
        )

        self.title_bar_container = ft.Container(
            content=ft.Row([
                ft.Container(content=self.conversation_title, alignment=ft.alignment.center_left, expand=True,
                             padding=ft.padding.only(left=16)),
                self.new_chat_button
            ]), padding=ft.padding.symmetric(vertical=8, horizontal=16), bgcolor="#1e293b",
            border=ft.border.only(bottom=ft.border.BorderSide(1, "#6366f1")), visible=False
        )

        return ft.Container(
            content=ft.Column([
                self.title_bar_container,
                ft.Container(content=ft.Column([self.chat_container, self.welcome_container], expand=True), expand=True,
                             padding=0, margin=0),
                input_container
            ], expand=True, spacing=0), expand=True, padding=0, margin=0, bgcolor="#0f172a"
        )

    def handle_keyboard_event(self, e: ft.KeyboardEvent):
        """处理键盘事件"""
        if e.key == "Enter":
            # 获取当前的快捷键设置
            shortcut = getattr(self.client, 'send_shortcut', 'Enter')

            if shortcut == "Enter" and not e.ctrl and not e.shift and not e.alt:
                # Enter 直接发送
                self.send_message()
                return
            elif shortcut == "Ctrl+Enter" and e.ctrl and not e.shift and not e.alt:
                # Ctrl+Enter 发送
                self.send_message()
                return
            else:
                # 其他情况允许换行
                if not e.ctrl and not e.shift and not e.alt:
                    # 单纯的 Enter，根据设置决定行为
                    if shortcut == "Enter":
                        self.send_message()
                    else:
                        # 允许换行
                        pass

    def add_message(self, role: str, content: str, streaming: bool = False, message_id: str = None):
        """添加消息到聊天窗口"""
        self.welcome_container.visible = False
        if self.chat_container:
            self.chat_container.visible = True
        self.title_bar_container.visible = True

        if role == "user":
            bg_color, align, margin = "#3730a3", ft.CrossAxisAlignment.END, ft.margin.only(left=60, right=8, top=1,
                                                                                           bottom=1)
            message_content = ft.Text(content, color="#f8fafc", selectable=True)
        elif role == "assistant":
            bg_color, align, margin = "#111827", ft.CrossAxisAlignment.START, ft.margin.only(left=8, right=60, top=1,
                                                                                             bottom=1)
            message_content = ft.Markdown(content + "▌" if streaming else content,
                                          extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                                          selectable=True, code_theme="atom-one-dark")
        else:  # system
            bg_color, align, margin = "#7c2d12", ft.CrossAxisAlignment.CENTER, ft.margin.symmetric(horizontal=12,
                                                                                                   vertical=1)
            message_content = ft.Text(content, color="#f8fafc", selectable=True)

        message_card = ft.Container(
            content=ft.Column([ft.Container(content=message_content, padding=6)], spacing=0, alignment=align,
                              tight=True),
            padding=0, border_radius=6, bgcolor=bg_color, margin=margin,
            shadow=ft.BoxShadow(spread_radius=0, blur_radius=4, color="rgba(0, 0, 0, 0.2)",
                                offset=ft.Offset(0, 1)) if role != "assistant" else None
        )

        # 为每个消息分配唯一ID，用于后续更新
        if message_id is None:
            message_id = str(uuid.uuid4())
        message_card.data = f"message_{message_id}"

        # 如果是正在流式输出的助手消息，记录其ID并初始化响应内容
        if role == "assistant" and streaming:
            self.current_message_id = message_id
            self.current_responses[message_id] = ""  # 初始化该消息的响应内容

        self.chat_display.controls.append(message_card)
        self.page.update()

    def update_streaming_message(self, content: str, message_id: str = None):
        """更新流式输出的消息"""
        target_message_id = message_id or self.current_message_id
        if not target_message_id:
            return

        # 更新该消息的响应内容
        if target_message_id in self.current_responses:
            self.current_responses[target_message_id] += content
        else:
            self.current_responses[target_message_id] = content

        # 根据消息ID找到对应的消息控件
        for message in self.chat_display.controls:
            if hasattr(message, 'data') and message.data == f"message_{target_message_id}":
                content_container = message.content.controls[0]
                if isinstance(content_container.content, ft.Markdown):
                    content_container.content.value = self.current_responses[target_message_id] + "▌"
                    self.page.update()
                break

    def complete_streaming_message(self, content: str = None, message_id: str = None):
        """完成流式输出，移除光标并更新内容"""
        target_message_id = message_id or self.current_message_id
        if not target_message_id:
            return

        # 获取最终内容
        final_content = content
        if final_content is None and target_message_id in self.current_responses:
            final_content = self.current_responses[target_message_id]

        if final_content is None:
            final_content = ""

        # 根据消息ID找到对应的消息控件
        for message in self.chat_display.controls:
            if hasattr(message, 'data') and message.data == f"message_{target_message_id}":
                content_container = message.content.controls[0]
                if isinstance(content_container.content, ft.Markdown):
                    content_container.content.value = final_content
                    self.page.update()
                break

        # 清理该消息的响应数据
        if target_message_id in self.current_responses:
            del self.current_responses[target_message_id]

        # 如果是当前消息，重置current_message_id
        if target_message_id == self.current_message_id:
            self.current_message_id = None

    def send_message(self):
        """发送消息"""
        message = self.input_field.value.strip()
        if not message:
            return

        if not self.client.api_key:
            self.add_message("system", "❌ 请先在设置中配置 API Key")
            return

        self.input_field.value = ""
        self.page.update()

        # 添加用户消息
        self.add_message("user", message)

        # 为这次对话生成唯一的消息ID
        current_msg_id = str(uuid.uuid4())

        # 添加助手消息（流式输出状态）
        self.add_message("assistant", "", streaming=True, message_id=current_msg_id)

        self.is_streaming = True
        self.send_stop_button.text = "停止"
        self.send_stop_button.on_click = lambda e: self.stop_generation()
        self.send_stop_button.bgcolor = "#dc2626"
        self.page.update()

        # 传递消息ID给回调函数
        def response_callback(content: str, msg_type: str):
            self.handle_response(content, msg_type, current_msg_id)

        self.client.chat_stream(message, callback=response_callback,
                                title_update_callback=self.handle_title_update_callback)

    def handle_response(self, content: str, msg_type: str, message_id: str):
        """处理API响应"""
        if msg_type == "error":
            self.add_message("system", f"❌ 错误: {content}")
            self.is_streaming = False
            self._reset_send_button()
            self.complete_streaming_message("❌ 生成失败", message_id)
        elif msg_type == "stream":
            self.update_streaming_message(content, message_id)
        elif msg_type == "complete":
            self.complete_streaming_message(content, message_id)
            self.is_streaming = False
            self._reset_send_button()
        elif msg_type == "start":
            # 流式输出开始，不需要特别处理
            pass
        self.page.update()

    def _reset_send_button(self):
        """重置发送按钮状态"""
        self.send_stop_button.text = "发送"
        self.send_stop_button.on_click = lambda e: self.send_message()
        self.send_stop_button.bgcolor = "#6366f1"
        self.page.update()

    def stop_generation(self):
        """停止生成"""
        self.client.stop_streaming()
        self.is_streaming = False
        self._reset_send_button()

        # 完成所有正在进行的流式消息
        for message_id in list(self.current_responses.keys()):
            self.complete_streaming_message(message_id=message_id)

        self.current_message_id = None
        self.page.update()

    def new_conversation(self):
        """新建对话"""
        self.chat_display.controls.clear()
        self.client.new_conversation()
        self.welcome_container.visible = True
        if self.chat_container:
            self.chat_container.visible = False
        self.title_bar_container.visible = False
        self.current_conversation_name = "新的对话"
        self.conversation_title.value = self.current_conversation_name
        self.current_message_id = None
        self.current_responses.clear()  # 清空所有响应数据
        self.page.update()

    def handle_title_update_callback(self, new_title: str):
        """处理对话标题更新回调"""
        self.current_conversation_name = new_title
        self.conversation_title.value = self.current_conversation_name
        self.conversation_title.update()
        self.page.update()

    def load_conversation(self, history):
        """加载对话历史"""
        self.chat_display.controls.clear()
        self.current_message_id = None
        self.current_responses.clear()  # 清空所有响应数据

        if history:
            self.welcome_container.visible = False
            if self.chat_container:
                self.chat_container.visible = True
            self.title_bar_container.visible = True
            for role, content in history:
                self.add_message(role, content)
        else:
            self.welcome_container.visible = True
            if self.chat_container:
                self.chat_container.visible = False
            self.title_bar_container.visible = False
        self.page.update()

    def update_conversation_name(self, name: str):
        """更新对话名称"""
        self.current_conversation_name = name
        self.conversation_title.value = self.current_conversation_name
        self.conversation_title.update()
        self.page.update()