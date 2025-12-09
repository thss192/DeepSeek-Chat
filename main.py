#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import flet as ft
from src.client import DeepSeekClient
from src.file_manager import FileManager
from src.settings_manager import SettingsManager
from src.chat_view import ChatView
from src.history_manager import HistoryManager  # 新增导入
from src.concurrent_manager.conversation_manager import ConversationTab
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parent.parent.parent

class DeepSeekApp:
    def __init__(self):
        self.client = DeepSeekClient()
        self.current_tab = 0
        self.tabs_control = None
        self.file_manager = None
        self.settings_manager = SettingsManager(self.client)
        self.chat_view = ChatView(self.client, self.handle_title_update_callback)
        self.history_manager = HistoryManager(  # 新增历史管理器
            self.client,
            self.switch_to_tab,
            self.load_conversation
        )
        self.conversation_tab = None  # 延迟初始化

    def main(self, page: ft.Page):
        self.page = page
        self._setup_page()

        # 在这里初始化需要 page 对象的管理器
        self.file_manager = FileManager(main_page=page)
        self.settings_manager.set_page(page)
        self.settings_manager.set_chat_view_ref(self.chat_view)  # 新增：设置聊天视图引用
        self.history_manager.set_page(page)  # 设置页面对象

        # 延迟初始化对话标签页，确保有 page 对象
        self.conversation_tab = ConversationTab(page)

        self.create_ui()

        # 在控件添加到页面后，立即手动初始化多对话 UI
        self.conversation_tab.initialize_ui()

        self.load_settings()
        self.file_manager.refresh_files(page)

    def _setup_page(self):
        self.page.title = "DeepSeek Chat"
        self.page.theme_mode = "dark"
        self.page.window.width = 1200
        self.page.window.height = 800
        self.page.padding = 0
        self.page.bgcolor = "#111827"

    def create_ui(self):
        self.tabs_control = ft.Tabs(
            selected_index=self.current_tab,
            on_change=self._on_tab_change,
            tabs=[
                ft.Tab(text="聊天", content=self._create_chat_tab()),
                ft.Tab(text="设置", content=self._create_settings_tab()),
                ft.Tab(text="历史", content=self._create_history_tab()),  # 使用历史管理器
                ft.Tab(text="文件管理", content=self._create_file_manager_tab()),
                ft.Tab(text="多对话", content=self.conversation_tab.create_tab())
            ],
            expand=True
        )

        self.page.add(self.tabs_control)
        self.page.on_keyboard_event = self._on_keyboard_event

    def switch_to_tab(self, tab_index: int):
        self.current_tab = tab_index
        if self.tabs_control:
            self.tabs_control.selected_index = tab_index
            if hasattr(self, 'page'):
                self.page.update()

    def _on_tab_change(self, e):
        self.current_tab = e.control.selected_index
        if self.current_tab == 0:  # 新增：切换到聊天标签时更新快捷键显示
            self.chat_view.update_shortcut_display()
        elif self.current_tab == 1:
            self.settings_manager.refresh_settings()
        elif self.current_tab == 2:
            self.history_manager.refresh_history()  # 使用历史管理器
        elif self.current_tab == 3 and self.file_manager:
            try:
                self.file_manager.refresh_files(self.page)
            except Exception as ex:
                print(f"刷新文件列表时出错: {ex}")

    def _create_chat_tab(self):
        return self.chat_view.create_chat_tab(self.page)

    def _create_settings_tab(self):
        return self.settings_manager.create_settings_tab()

    def _create_history_tab(self):
        return self.history_manager.create_history_tab()  # 使用历史管理器

    def _create_file_manager_tab(self):
        if self.file_manager:
            return self.file_manager.create_file_manager_tab()
        return ft.Container(
            content=ft.Text("文件管理器初始化失败", color="#ef4444"),
            alignment=ft.alignment.center
        )

    def _on_keyboard_event(self, e: ft.KeyboardEvent):
        self.chat_view.handle_keyboard_event(e)

    def delete_conversation(self, filepath):
        """删除对话（供历史管理器回调使用）"""
        def confirm_delete(e):
            if self.client.delete_conversation(filepath):
                self.history_manager.refresh_history()
            self.page.close(dialog)

        dialog = ft.AlertDialog(
            title=ft.Text("确认删除", color="#e5e7eb"),
            content=ft.Text("确定要删除这个对话记录吗？此操作不可恢复。", color="#d1d5db"),
            bgcolor="#1f2937",
            actions=[
                ft.TextButton("取消", on_click=lambda e: self.page.close(dialog)),
                ft.TextButton("确定", on_click=confirm_delete, style=ft.ButtonStyle(color="#ef4444")),
            ],
        )
        self.page.open(dialog)

    def load_conversation(self, filepath):
        """加载对话（供历史管理器回调使用）"""
        if self.client.load_conversation(filepath):
            self.chat_view.load_conversation(self.client.history)
            try:
                conversations = self.client.get_conversation_list()
                conv = next(c for c in conversations if c['path'] == filepath)
                self.chat_view.update_conversation_name(conv['name'])
            except (StopIteration, KeyError):
                name = filepath.split('/')[-1].replace('.json', '')
                self.chat_view.update_conversation_name(name)
            self.switch_to_tab(0)

    def handle_title_update_callback(self, new_title: str):
        """处理标题更新回调"""
        if self.current_tab == 2:
            self.history_manager.refresh_history()  # 使用历史管理器

    def load_settings(self):
        pass


def main():
    ft.app(target=DeepSeekApp().main)


if __name__ == "__main__":
    main()