#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import flet as ft
import datetime
from typing import Callable


class HistoryManager:
    def __init__(self, client, switch_to_tab_callback: Callable, load_conversation_callback: Callable):
        self.client = client
        self.switch_to_tab_callback = switch_to_tab_callback
        self.load_conversation_callback = load_conversation_callback
        self.history_list = None

    def create_history_tab(self):
        """创建历史记录标签页"""
        self.history_list = ft.Column(expand=True, spacing=3)  # 减小间距

        # 创建顶部操作栏
        top_actions = ft.Container(
            content=ft.Row([
                ft.Text("对话历史", size=16, weight="bold", color="#e5e7eb"),
                ft.Container(expand=True),  # 占位
                ft.ElevatedButton(
                    "一键删除所有对话",
                    on_click=self._on_delete_all_conversations,
                    style=ft.ButtonStyle(
                        color="#ffffff",
                        bgcolor="#ef4444",
                        padding=ft.padding.symmetric(8, 12)
                    )
                )
            ]),
            padding=ft.padding.symmetric(10, 15),
            bgcolor="#1f2937",
            margin=ft.margin.only(bottom=8)
        )

        self.refresh_history()

        return ft.Container(
            content=ft.Column([
                top_actions,
                ft.Container(
                    content=ft.ListView([self.history_list], expand=True),
                    expand=True,
                    padding=10,
                    bgcolor="#1f2937",
                    border_radius=8,
                    margin=10
                )
            ]),
            expand=True,
            bgcolor="#111827"
        )

    def refresh_history(self):
        """刷新历史记录列表"""
        if not self.history_list:
            return

        self.history_list.controls.clear()
        conversations = self.client.get_conversation_list()

        if not conversations:
            self.history_list.controls.append(
                ft.Container(
                    content=ft.Text("暂无对话历史", size=12, color="#9ca3af"),
                    padding=15,
                    alignment=ft.alignment.center
                )
            )
        else:
            for conv in conversations:
                card = self._create_conversation_card(conv)
                self.history_list.controls.append(card)

        # 如果需要在外部更新页面，可以通过回调实现
        # 这里不直接操作 page，由主应用负责更新

    def _create_conversation_card(self, conversation):
        """创建单个对话卡片"""
        time_display = self._format_time(conversation["updated_at"])

        return ft.Card(
            content=ft.Container(
                content=ft.Column([
                    # 标题和消息数量 - 减小高度
                    ft.Row([
                        ft.Text(
                            conversation['name'],
                            size=12,  # 减小字体
                            color="#e5e7eb",
                            weight="bold",
                            expand=True,
                            max_lines=1,
                            overflow="ellipsis"
                        ),
                        ft.Container(
                            content=ft.Text(
                                f"{conversation['message_count']}条",
                                size=9,  # 减小字体
                                color="#9ca3af"
                            ),
                            bgcolor="#374151",
                            border_radius=4,
                            padding=ft.padding.symmetric(3, 5)  # 减小内边距
                        )
                    ], alignment="spaceBetween"),

                    # 预览内容 - 减小高度
                    ft.Container(
                        content=ft.Text(
                            conversation['preview'],
                            size=10,  # 减小字体
                            color="#d1d5db",
                            max_lines=2,  # 限制行数
                            overflow="ellipsis"
                        ),
                        margin=ft.margin.only(top=2, bottom=2)
                    ),

                    # 更新时间 - 减小高度
                    ft.Row([
                        ft.Text(
                            f"更新时间: {time_display}",
                            size=9,  # 减小字体
                            color="#6b7280"
                        )
                    ]),

                    # 操作按钮 - 减小按钮尺寸
                    ft.Row([
                        ft.ElevatedButton(
                            "加载",
                            on_click=lambda e, p=conversation['path']: self._on_load_conversation(p),
                            style=ft.ButtonStyle(
                                color="#ffffff",
                                bgcolor="#4f46e5",
                                padding=ft.padding.symmetric(4, 8),  # 减小内边距
                                overlay_color=ft.Colors.WHITE12
                            )
                        ),
                        ft.ElevatedButton(
                            "删除",
                            on_click=lambda e, p=conversation['path']: self._on_delete_conversation(p),
                            style=ft.ButtonStyle(
                                color="#ffffff",
                                bgcolor="#ef4444",
                                padding=ft.padding.symmetric(4, 8),  # 减小内边距
                                overlay_color=ft.Colors.WHITE12
                            )
                        )
                    ], spacing=3)  # 减小按钮间距
                ], spacing=3),  # 减小列内间距
                padding=8  # 减小内边距
            ),
            color="#374151",
            elevation=1,  # 减小阴影
            margin=ft.margin.only(bottom=5)  # 减小底部边距
        )

    def _format_time(self, time_str):
        """格式化时间显示"""
        if not time_str:
            return "未知时间"

        try:
            time_obj = datetime.datetime.fromisoformat(time_str)
            return time_obj.strftime("%m-%d %H:%M")
        except (ValueError, TypeError):
            return time_str[:16] if time_str else "未知时间"

    def _on_load_conversation(self, filepath):
        """处理加载对话事件"""
        self.load_conversation_callback(filepath)

    def _on_delete_conversation(self, filepath):
        """处理删除对话事件"""
        if hasattr(self, 'page'):
            self._show_delete_confirmation(filepath)
        else:
            # 如果没有页面对象，直接删除
            if self.client.delete_conversation(filepath):
                self.refresh_history()

    def _on_delete_all_conversations(self, e):
        """处理一键删除所有对话事件"""
        if hasattr(self, 'page'):
            self._show_delete_all_confirmation()
        else:
            # 如果没有页面对象，直接删除所有
            conversations = self.client.get_conversation_list()
            success_count = 0
            for conv in conversations:
                if self.client.delete_conversation(conv['path']):
                    success_count += 1
            if success_count > 0:
                self.refresh_history()

    def set_page(self, page: ft.Page):
        """设置页面对象（用于显示对话框等需要页面的操作）"""
        self.page = page

    def _show_delete_confirmation(self, filepath):
        """显示删除确认对话框"""

        def confirm_delete(e):
            if self.client.delete_conversation(filepath):
                self.refresh_history()
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

    def _show_delete_all_confirmation(self):
        """显示删除所有对话确认对话框"""

        def confirm_delete_all(e):
            conversations = self.client.get_conversation_list()
            success_count = 0
            for conv in conversations:
                if self.client.delete_conversation(conv['path']):
                    success_count += 1
            if success_count > 0:
                self.refresh_history()
            self.page.close(dialog)

        dialog = ft.AlertDialog(
            title=ft.Text("确认删除所有对话", color="#e5e7eb"),
            content=ft.Text("确定要删除所有对话记录吗？此操作不可恢复！", color="#d1d5db"),
            bgcolor="#1f2937",
            actions=[
                ft.TextButton("取消", on_click=lambda e: self.page.close(dialog)),
                ft.TextButton("确定删除", on_click=confirm_delete_all, style=ft.ButtonStyle(color="#ef4444")),
            ],
        )
        self.page.open(dialog)