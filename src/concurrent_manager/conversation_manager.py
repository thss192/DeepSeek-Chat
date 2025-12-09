#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import flet as ft
import json
import uuid
import threading
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable


class GlobalConfig:
    def __init__(self):
        self.config_file = Path("global_config.json")
        self.api_key = ""
        self.api_base_url = "https://api.deepseek.com/v1"
        self.load()

    def load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.api_key = data.get('api_key', "")
                self.api_base_url = data.get('api_base_url', "https://api.deepseek.com/v1")
            except Exception as e:
                print(f"加载全局配置失败: {e}")

    def save(self):
        data = {'api_key': self.api_key, 'api_base_url': self.api_base_url}
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存全局配置失败: {e}")
            return False


class ConversationConfig:
    def __init__(self, config_id: str = None):
        self.config_id = config_id or str(uuid.uuid4())
        self.name = f"对话_{datetime.now().strftime('%H:%M')}"
        self.model = "deepseek-chat"
        self.max_tokens = 2048
        self.temperature = 0.7
        self.top_p = 0.9
        self.frequency_penalty = 0.0
        self.presence_penalty = 0.0
        self.system_content = "你是一个有用的AI助手"
        self.created_at = self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {key: getattr(self, key) for key in ['config_id', 'name', 'model', 'max_tokens',
                                                    'temperature', 'top_p', 'frequency_penalty', 'presence_penalty',
                                                    'system_content', 'created_at', 'updated_at']}

    @classmethod
    def from_dict(cls, data: dict) -> 'ConversationConfig':
        config = cls(data.get('config_id'))
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config


class ConversationData:
    def __init__(self, config: ConversationConfig):
        self.config = config
        self.history = []
        self.data_file = Path(f"independent_conversations/conv_{config.config_id}.json")
        self.data_file.parent.mkdir(exist_ok=True)
        self.load()

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content, "timestamp": datetime.now().isoformat()})
        self.save()

    def save(self):
        self.config.updated_at = datetime.now().isoformat()
        data = {'config': self.config.to_dict(), 'history': self.history}
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存对话数据失败: {e}")

    def load(self):
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.history = data.get('history', [])
                config_data = data.get('config', {})
                if config_data.get('config_id') == self.config.config_id:
                    self.config = ConversationConfig.from_dict(config_data)
            except Exception as e:
                print(f"加载对话数据失败: {e}")

    def clear_history(self):
        self.history.clear()
        self.save()


class DeepSeekAPI:
    def __init__(self, global_config: GlobalConfig):
        self.global_config = global_config

    def send_message(self, messages: List[dict], conversation_config: ConversationConfig, callback: Callable):
        if not self.global_config.api_key:
            callback("请先在API配置中设置API Key", "error")
            return

        url = f"{self.global_config.api_base_url}/chat/completions"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.global_config.api_key}"}

        payload = {
            "model": conversation_config.model, "messages": messages, "max_tokens": conversation_config.max_tokens,
            "temperature": conversation_config.temperature, "top_p": conversation_config.top_p,
            "frequency_penalty": conversation_config.frequency_penalty,
            "presence_penalty": conversation_config.presence_penalty,
            "stream": True
        }

        def api_call():
            try:
                response = requests.post(url, headers=headers, json=payload, stream=True, timeout=30)
                if response.status_code != 200:
                    callback(f"API请求失败: {response.status_code} - {response.text}", "error")
                    return

                full_response = ""
                for line in response.iter_lines():
                    if line:
                        line = line.decode('utf-8')
                        if line.startswith('data: '):
                            data = line[6:]
                            if data == '[DONE]':
                                break
                            try:
                                json_data = json.loads(data)
                                if 'choices' in json_data and json_data['choices']:
                                    delta = json_data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        content = delta['content']
                                        full_response += content
                                        # 修复：传递累积的完整响应内容，而不是单个片段
                                        callback(full_response, "stream")
                            except json.JSONDecodeError:
                                continue

                callback(full_response, "complete")

            except requests.exceptions.Timeout:
                callback("请求超时，请稍后重试", "error")
            except requests.exceptions.ConnectionError:
                callback("网络连接错误，请检查网络连接", "error")
            except Exception as e:
                callback(f"发生错误: {str(e)}", "error")

        threading.Thread(target=api_call, daemon=True).start()


class ConversationChatView:
    def __init__(self, on_send_message: Callable):
        self.on_send_message = on_send_message
        self.current_response = ""
        self.is_streaming = False
        self.page = None

        self.chat_display = ft.ListView(expand=True, spacing=5, auto_scroll=True)
        self.input_field = ft.TextField(
            multiline=True, min_lines=1, max_lines=4, expand=True, hint_text="输入消息...",
            border_color="#4b5563", focused_border_color="#3b82f6", content_padding=12,
            on_submit=lambda e: self._send_message()
        )
        self.send_button = ft.ElevatedButton("发送", on_click=self._send_message,
                                             style=ft.ButtonStyle(color="#ffffff", bgcolor="#3b82f6"))

    def _send_message(self, e=None):
        message = self.input_field.value.strip()
        if not message or self.is_streaming:
            return

        self.input_field.value = ""
        self._add_message_display("user", message)
        self.is_streaming, self.send_button.disabled, self.send_button.text = True, True, "发送中..."
        if self.page:
            self.page.update()

        self.on_send_message(message, self._handle_response)

    def _handle_response(self, content: str, msg_type: str):
        if msg_type == "stream":
            # 修复：累积显示流式内容
            self.current_response = content
            self._update_streaming_message()
        elif msg_type == "complete":
            # 完成时移除闪烁光标并显示最终内容
            if self._is_last_message_ai():
                self.chat_display.controls.pop()
            self._add_message_display("assistant", content)
            self.current_response, self.is_streaming = "", False
            self.send_button.disabled, self.send_button.text = False, "发送"
            if self.page:
                self.page.update()
        elif msg_type == "error":
            if self._is_last_message_ai():
                self.chat_display.controls.pop()
            self._add_message_display("system", f"错误: {content}")
            self.current_response, self.is_streaming = "", False
            self.send_button.disabled, self.send_button.text = False, "发送"
            if self.page:
                self.page.update()

    def _is_last_message_ai(self):
        return (self.chat_display.controls and
                self.chat_display.controls[-1].controls and
                hasattr(self.chat_display.controls[-1].controls[0], 'color') and
                self.chat_display.controls[-1].controls[0].color == "#10b981")

    def _add_message_display(self, role: str, content: str):
        color = "#3b82f6" if role == "user" else "#10b981" if role == "assistant" else "#ef4444"
        markdown_content = ft.Markdown(content, selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                                       code_theme="github-dark")
        message_card = ft.Card(
            content=ft.Container(content=ft.Column([markdown_content], tight=True), padding=12, bgcolor="#1f2937"),
            color=color, margin=ft.margin.only(bottom=5), width=500)

        row_alignment = ft.MainAxisAlignment.END if role == "user" else ft.MainAxisAlignment.START
        message_row = ft.Row([message_card], alignment=row_alignment)
        self.chat_display.controls.append(message_row)

        if self.page:
            self.chat_display.update()

    def _update_streaming_message(self):
        if self._is_last_message_ai():
            # 更新现有的流式消息
            last_msg_md = self.chat_display.controls[-1].controls[0].content.content.controls[0]
            last_msg_md.value = self.current_response + "▌"
        else:
            # 创建新的流式消息
            self._add_message_display("assistant", self.current_response + "▌")

        if self.page:
            self.chat_display.update()

    def load_history(self, history: List[dict]):
        self.chat_display.controls.clear()
        for msg in history:
            self._add_message_display(msg["role"], msg["content"])
        if self.page:
            self.chat_display.update()

    def create_chat_tab(self) -> ft.Container:
        return ft.Container(
            content=ft.Column([
                ft.Container(content=self.chat_display, expand=True, padding=10, bgcolor="#111827"),
                ft.Container(content=ft.Row([self.input_field, self.send_button], spacing=10),
                             padding=10, bgcolor="#1f2937")
            ], expand=True),
            expand=True, bgcolor="#111827")


class ConversationSettings:
    def __init__(self, on_config_update: Callable, on_clear_history: Callable):
        self.on_config_update = on_config_update
        self.on_clear_history = on_clear_history
        self._create_controls()

    def _create_controls(self):
        # 移除会导致内容恢复的on_change事件，改为手动触发更新
        field_style = {"border_color": "#4b5563", "focused_border_color": "#3b82f6"}

        self.name_field = ft.TextField(label="对话名称", **field_style, on_blur=self._on_config_change)
        self.model_field = ft.Dropdown(
            label="模型",
            options=[ft.dropdown.Option(m) for m in ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"]],
            **field_style, on_change=self._on_config_change)
        self.system_prompt_field = ft.TextField(label="系统提示词", multiline=True, min_lines=3,
                                                **field_style, on_blur=self._on_config_change)
        self.temperature_field = ft.Slider(label="温度", min=0, max=2, divisions=20,
                                           on_change_end=self._on_config_change)
        self.max_tokens_field = ft.TextField(label="最大令牌数", keyboard_type=ft.KeyboardType.NUMBER,
                                             **field_style, on_blur=self._on_config_change)
        self.top_p_field = ft.Slider(label="Top P", min=0, max=1, divisions=20, on_change_end=self._on_config_change)
        self.clear_history_button = ft.ElevatedButton("清除对话历史", on_click=self.on_clear_history,
                                                      style=ft.ButtonStyle(color="#ffffff", bgcolor="#ef4444"))

    def update_config(self, config: ConversationConfig):
        # 更新字段值但不触发on_change事件
        self.name_field.value = config.name
        self.model_field.value = config.model
        self.system_prompt_field.value = config.system_content
        self.temperature_field.value = config.temperature
        self.max_tokens_field.value = str(config.max_tokens)
        self.top_p_field.value = config.top_p
        if self.name_field.page:
            self.name_field.page.update()

    def _on_config_change(self, e):
        # 延迟触发配置更新，避免在用户输入时频繁保存
        if hasattr(self, '_update_timer'):
            self._update_timer.cancel()

        def delayed_update():
            self.on_config_update()

        self._update_timer = threading.Timer(0.5, delayed_update)
        self._update_timer.start()

    def get_updated_config(self, original_config: ConversationConfig) -> ConversationConfig:
        config = ConversationConfig(original_config.config_id)
        for attr in ['created_at', 'frequency_penalty', 'presence_penalty']:
            setattr(config, attr, getattr(original_config, attr))

        # 允许空值，不设置默认值
        config.name = self.name_field.value or f"对话_{datetime.now().strftime('%H:%M')}"
        config.model = self.model_field.value or "deepseek-chat"
        config.system_content = self.system_prompt_field.value or "你是一个有用的AI助手"
        config.temperature = float(self.temperature_field.value) if self.temperature_field.value is not None else 0.7
        config.top_p = float(self.top_p_field.value) if self.top_p_field.value is not None else 0.9

        try:
            config.max_tokens = int(self.max_tokens_field.value) if self.max_tokens_field.value else 2048
        except ValueError:
            config.max_tokens = original_config.max_tokens

        config.updated_at = datetime.now().isoformat()
        return config

    def create_settings_tab(self) -> ft.Container:
        return ft.Container(
            content=ft.Column([
                ft.Text("对话设置", size=18, weight="bold", color="#e5e7eb"),
                self.name_field, self.model_field, self.system_prompt_field,
                ft.Text("温度 (0-2):", color="#e5e7eb"), self.temperature_field,
                self.max_tokens_field, ft.Text("Top P (0-1):", color="#e5e7eb"), self.top_p_field,
                self.clear_history_button
            ], scroll=ft.ScrollMode.ADAPTIVE, spacing=15),
            padding=20, bgcolor="#1f2937", border_radius=8, margin=10, expand=True)


class APIConfigTab:
    def __init__(self, global_config: GlobalConfig):
        self.global_config = global_config
        self._create_controls()

    def _create_controls(self):
        field_style = {"border_color": "#4b5563", "focused_border_color": "#3b82f6"}

        self.api_key_field = ft.TextField(label="API Key", password=True, can_reveal_password=True, **field_style)
        self.api_base_url_field = ft.TextField(label="API Base URL", **field_style)
        self.save_button = ft.ElevatedButton("保存配置", on_click=self._save_config,
                                             style=ft.ButtonStyle(color="#ffffff", bgcolor="#10b981"))
        self.status_text = ft.Text("", color="#e5e7eb")

    def _save_config(self, e):
        self.global_config.api_key = self.api_key_field.value or ""
        self.global_config.api_base_url = self.api_base_url_field.value or "https://api.deepseek.com/v1"

        if self.global_config.save():
            self.status_text.value, self.status_text.color = "配置保存成功！", "#10b981"
        else:
            self.status_text.value, self.status_text.color = "配置保存失败！", "#ef4444"

        if self.api_key_field.page:
            self.status_text.update()

    def load_config(self):
        self.api_key_field.value = self.global_config.api_key
        self.api_base_url_field.value = self.global_config.api_base_url
        if self.api_key_field.page:
            self.api_key_field.page.update()

    def create_tab(self) -> ft.Container:
        return ft.Container(
            content=ft.Column([
                ft.Text("API 配置", size=18, weight="bold", color="#e5e7eb"),
                ft.Text("在此设置全局API配置，所有对话将使用相同的API Key", color="#d1d5db", size=14),
                self.api_key_field, self.api_base_url_field, self.save_button, self.status_text
            ], scroll=ft.ScrollMode.ADAPTIVE, spacing=20),
            padding=20, bgcolor="#1f2937", border_radius=8, margin=10, expand=True)


class ConversationManager:
    def __init__(self, global_config: GlobalConfig):
        self.conversations = {}
        self.active_conversation_id = None
        self.global_config = global_config
        self.api = DeepSeekAPI(global_config)
        self.conversations_dir = Path("./independent_conversations")
        self.conversations_dir.mkdir(exist_ok=True)
        self._load_conversations()

        if not self.conversations:
            self.active_conversation_id = self.create_conversation()
        elif not self.active_conversation_id:
            conv_list = self.get_conversation_list()
            self.active_conversation_id = next(iter(conv_list), {}).get('id', None)

    def _load_conversations(self):
        for file in self.conversations_dir.glob("conv_*.json"):
            try:
                conv_id = file.stem.replace('conv_', '')
                config = ConversationConfig(config_id=conv_id)
                conversation_data = ConversationData(config)
                self.conversations[config.config_id] = conversation_data
            except Exception as e:
                print(f"加载对话文件失败 {file}: {e}")

    def create_conversation(self) -> str:
        config = ConversationConfig()
        conversation_data = ConversationData(config)
        self.conversations[config.config_id] = conversation_data
        self.active_conversation_id = config.config_id
        conversation_data.save()
        return config.config_id

    def delete_conversation(self, conversation_id: str):
        if conversation_id in self.conversations:
            conversation_data = self.conversations[conversation_id]
            if conversation_data.data_file.exists():
                conversation_data.data_file.unlink()
            del self.conversations[conversation_id]
            if self.active_conversation_id == conversation_id:
                conv_list = self.get_conversation_list()
                self.active_conversation_id = next(iter(conv_list), {}).get('id', None)

    def switch_conversation(self, conversation_id: str):
        if conversation_id in self.conversations:
            self.active_conversation_id = conversation_id

    def get_active_conversation(self) -> Optional[ConversationData]:
        return self.conversations.get(self.active_conversation_id)

    def get_conversation_list(self) -> List[dict]:
        conversations = [{'id': conv_id, 'name': conv_data.config.name, 'message_count': len(conv_data.history),
                          'updated_at': conv_data.config.updated_at,
                          'is_active': conv_id == self.active_conversation_id}
                         for conv_id, conv_data in self.conversations.items()]
        conversations.sort(key=lambda x: x['updated_at'], reverse=True)
        return conversations


class ConversationTab:
    def __init__(self, page: ft.Page):
        self.page = page
        self.global_config = GlobalConfig()
        self.conversation_manager = ConversationManager(self.global_config)
        self._create_controls()

    def _create_controls(self):
        self.conversation_list = ft.Column(spacing=5, expand=True, scroll=ft.ScrollMode.ADAPTIVE)
        self.chat_view = ConversationChatView(self._send_message)
        self.settings_view = ConversationSettings(self._on_config_update, self._clear_history)
        self.api_config_tab = APIConfigTab(self.global_config)

        self.tabs = ft.Tabs(
            selected_index=0, expand=True, on_change=self._on_tab_change,
            tabs=[
                ft.Tab(text="聊天", content=self.chat_view.create_chat_tab()),
                ft.Tab(text="对话设置", content=self.settings_view.create_settings_tab()),
                ft.Tab(text="API配置", content=self.api_config_tab.create_tab())
            ]
        )

        self.new_conversation_btn = ft.ElevatedButton(
            "新建对话", on_click=lambda e: self._create_new_conversation(),
            style=ft.ButtonStyle(color="#ffffff", bgcolor="#10b981"), icon=ft.Icons.ADD)
        self.current_conversation_title = ft.Text("当前对话: 无", size=16, weight="bold", color="#e5e7eb")

    def _on_tab_change(self, e):
        if e.control.selected_index == 1:
            self._update_settings()
        elif e.control.selected_index == 2:
            self.api_config_tab.load_config()

    def _create_new_conversation(self):
        new_id = self.conversation_manager.create_conversation()
        self._refresh_ui()
        self._switch_to_conversation(new_id, switch_tab=True)

    def initialize_ui(self):
        if not self.chat_view.page:
            self.chat_view.page = self.page
        self._refresh_ui()

    def _refresh_ui(self):
        if not self.page:
            return
        self._update_conversation_list()
        self._update_current_title()
        self._update_chat_display()
        self._update_settings()
        self.page.update()

    def _update_conversation_list(self):
        self.conversation_list.controls.clear()
        for conv in self.conversation_manager.get_conversation_list():
            btn_color = "#3b82f6" if conv['is_active'] else "#4b5563"
            conv_button = ft.Container(
                content=ft.Row([
                    ft.Text(f"{conv['name']} ({conv['message_count']}条)", color="#ffffff",
                            expand=True, size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, icon_color="#ef4444", tooltip="删除对话",
                                  visible=not conv['is_active'],
                                  on_click=lambda e, cid=conv['id']: self._delete_conversation(cid))
                ], spacing=5, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=8, margin=ft.margin.only(bottom=5), bgcolor=btn_color, border_radius=6,
                on_click=lambda e, cid=conv['id']: self._switch_to_conversation(cid),
                alignment=ft.alignment.center_left, ink=True
            )
            self.conversation_list.controls.append(conv_button)
        if self.page:
            self.conversation_list.update()

    def _update_current_title(self):
        active_conv = self.conversation_manager.get_active_conversation()
        self.current_conversation_title.value = f"当前对话: {active_conv.config.name}" if active_conv else "当前对话: 无"
        if self.page:
            self.current_conversation_title.update()

    def _update_chat_display(self):
        active_conv = self.conversation_manager.get_active_conversation()
        if active_conv:
            self.chat_view.load_history(active_conv.history)
        else:
            self.chat_view.chat_display.controls.clear()
            if self.page:
                self.chat_view.chat_display.update()

    def _update_settings(self):
        active_conv = self.conversation_manager.get_active_conversation()
        if active_conv:
            self.settings_view.update_config(active_conv.config)

    def _switch_to_conversation(self, conversation_id: str, switch_tab: bool = False):
        self.conversation_manager.switch_conversation(conversation_id)
        self._refresh_ui()
        if switch_tab:
            self.tabs.selected_index = 0
            if self.page:
                self.page.update()

    def _delete_conversation(self, conversation_id: str):
        conv_to_delete = self.conversation_manager.conversations.get(conversation_id)
        conv_name = conv_to_delete.config.name if conv_to_delete else "未知对话"

        def confirm_delete(e):
            self.conversation_manager.delete_conversation(conversation_id)
            self._refresh_ui()
            self.page.close(dialog)

        dialog = ft.AlertDialog(
            title=ft.Text("确认删除", color="#e5e7eb"),
            content=ft.Text(f"确定要删除对话 '{conv_name}' 吗？此操作不可恢复。", color="#d1d5db"),
            bgcolor="#1f2937",
            actions=[
                ft.TextButton("取消", on_click=lambda e: self.page.close(dialog)),
                ft.TextButton("确定", on_click=confirm_delete, style=ft.ButtonStyle(color="#ef4444"))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        self.page.open(dialog)

    def _clear_history(self, e):
        active_conv = self.conversation_manager.get_active_conversation()
        if not active_conv:
            return

        def confirm_clear(e):
            active_conv.clear_history()
            self._update_chat_display()
            self._update_conversation_list()
            self.page.close(dialog)
            self.page.snack_bar = ft.SnackBar(ft.Text("历史记录已清空", color=ft.colors.WHITE),
                                              bgcolor=ft.colors.GREEN_700)
            self.page.snack_bar.open = True
            self.page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("确认清除", color="#e5e7eb"),
            content=ft.Text(f"确定要清除对话 '{active_conv.config.name}' 的历史记录吗？", color="#d1d5db"),
            bgcolor="#1f2937",
            actions=[
                ft.TextButton("取消", on_click=lambda e: self.page.close(dialog)),
                ft.TextButton("确定", on_click=confirm_clear, style=ft.ButtonStyle(color="#ef4444"))
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        self.page.open(dialog)

    def _send_message(self, message: str, callback: Callable):
        active_conv = self.conversation_manager.get_active_conversation()
        if not active_conv:
            return

        # 添加用户消息到历史
        active_conv.add_message("user", message)

        # 构建消息列表
        messages = []
        if active_conv.config.system_content:
            messages.append({"role": "system", "content": active_conv.config.system_content})

        # 添加对话历史
        for msg in active_conv.history:
            messages.append({"role": msg["role"], "content": msg["content"]})

        def handle_api_response(content: str, msg_type: str):
            if msg_type == "complete":
                # 在API完成时添加助手消息到历史记录
                active_conv.add_message("assistant", content)
                self._update_conversation_list()
            callback(content, msg_type)

        # 调用API
        self.conversation_manager.api.send_message(messages, active_conv.config, handle_api_response)

    def _on_config_update(self):
        active_conv = self.conversation_manager.get_active_conversation()
        if active_conv:
            updated_config = self.settings_view.get_updated_config(active_conv.config)
            active_conv.config = updated_config
            active_conv.save()
            self._refresh_ui()

    def create_tab(self) -> ft.Container:
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Column([
                        self.new_conversation_btn,
                        ft.Container(content=self.conversation_list, expand=True, padding=10, bgcolor="#1f2937",
                                     border_radius=8)
                    ], spacing=10), width=300, padding=10, bgcolor="#111827"),
                ft.Container(
                    content=ft.Column([
                        ft.Container(content=self.current_conversation_title, padding=10, bgcolor="#374151",
                                     border_radius=6),
                        self.tabs
                    ], expand=True), expand=True, padding=10, bgcolor="#111827")
            ], expand=True), expand=True, bgcolor="#111827")


def main(page: ft.Page):
    page.title = "DeepSeek Chat"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.window.width = 1200
    page.window.height = 800

    conversation_tab = ConversationTab(page)
    page.add(conversation_tab.create_tab())
    conversation_tab.initialize_ui()


if __name__ == "__main__":
    ft.app(target=main)