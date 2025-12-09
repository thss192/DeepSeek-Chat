#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import flet as ft
from .file_explorer import FileExplorer
from .file_editor import FileViewer, FileEditor as SimpleFileEditor
from pathlib import Path


class FileManager:
    """文件管理器 - 实现三面板（Explorer | Viewer | Editor）布局"""

    def __init__(self, main_page: ft.Page):
        self.main_page = main_page

        # 实例化组件
        self.file_explorer = FileExplorer(main_page, on_file_select=self.on_file_selected)
        self.file_viewer = FileViewer(main_page)
        self.file_editor = SimpleFileEditor(main_page, on_content_change=self.handle_editor_content_update)

        # 状态管理
        self.explorer_visible = self.viewer_visible = self.editor_visible = True
        initial_width = max(900, main_page.width)
        self.explorer_width = max(150, initial_width * 0.25)
        self.viewer_width = max(150, initial_width * 0.35)
        self.is_dragging = False
        self.active_splitter = None
        self._refresh_in_progress = False

        # 创建UI控件
        self.layout_controls = self._create_layout_controls()
        self.explorer_container = self._create_container(self.file_explorer.create_component())
        self.viewer_container = self._create_container(self.file_viewer.create_component())
        self.editor_container = self._create_container(self.file_editor.create_component())
        self.splitter_ex_vi = self.create_splitter(1)
        self.splitter_vi_ed = self.create_splitter(2)
        self.content_row = ft.Row(controls=[], expand=True, spacing=0)
        self.main_container = self.create_main_container()

        # 绑定事件
        main_page.on_resize = self._handle_page_resize
        self.update_layout()

    def _create_container(self, content):
        """创建通用容器"""
        return ft.Container(content=content, padding=0, border_radius=0)

    def handle_editor_content_update(self, content: str, file_path: Path):
        """处理编辑器内容更新并同步到查看器"""
        if self.viewer_visible:
            self.file_viewer.set_content_for_realtime_update(content, file_path)
        if self.file_editor.is_dirty:
            self.file_explorer.set_file_modified(file_path, True)

    def _handle_page_resize(self, e: ft.ControlEvent):
        """处理页面尺寸变化"""
        if self.main_page.width > 0 and not self.is_dragging:
            total_width = self.main_page.width
            if total_width > 400:
                self.explorer_width = max(150, total_width * 0.25)
                self.viewer_width = max(150, total_width * 0.35)
            self.update_layout()

    def on_file_selected(self, file_info):
        """文件选择回调"""
        self.file_viewer.open_file(file_info)
        self.file_editor.open_file(file_info)
        if not any([self.explorer_visible, self.viewer_visible, self.editor_visible]):
            self.explorer_visible = self.editor_visible = True
        self.update_layout()

    def _create_layout_controls(self):
        """创建布局控制按钮"""
        btn_style = ft.ButtonStyle(padding=ft.padding.all(6))
        buttons = [
            ft.IconButton(icon=ft.Icons.SAVE, icon_size=18, tooltip="保存文件", on_click=self.save_current_file,
                          style=ft.ButtonStyle(color="#ffffff", bgcolor="#f59e0b", padding=ft.padding.all(6))),
            ft.IconButton(icon=ft.Icons.FOLDER_OPEN, icon_size=18, tooltip="文件浏览器",
                          on_click=lambda e: self._toggle_panel('explorer_visible'), style=btn_style),
            ft.IconButton(icon=ft.Icons.VISIBILITY, icon_size=18, tooltip="查看器 (只读)",
                          on_click=lambda e: self._toggle_panel('viewer_visible'), style=btn_style),
            ft.IconButton(icon=ft.Icons.EDIT, icon_size=18, tooltip="编辑器 (可编辑)",
                          on_click=lambda e: self._toggle_panel('editor_visible'), style=btn_style)
        ]
        return ft.Row(buttons, spacing=2)

    def _toggle_panel(self, panel_attr):
        """切换面板可见性"""
        setattr(self, panel_attr, not getattr(self, panel_attr))
        self.update_layout()

    def create_splitter(self, splitter_id):
        """创建可拖拽的分割条"""
        splitter_container = ft.Container(width=6, bgcolor="#4b5563")
        return ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.RESIZE_LEFT_RIGHT,
            content=splitter_container,
            data=splitter_id,
            on_pan_start=self.on_splitter_pan_start,
            on_pan_update=self.on_splitter_pan_update,
            on_pan_end=self.on_splitter_pan_end,
            visible=False
        )

    def on_splitter_pan_start(self, e: ft.DragStartEvent):
        """开始拖拽分割条"""
        splitter_id = e.control.data
        if (splitter_id == 1 and (not self.explorer_visible or not self.viewer_visible)) or \
                (splitter_id == 2 and (not self.editor_visible or not (self.viewer_visible or self.explorer_visible))):
            return

        self.is_dragging = True
        self.active_splitter = e.control
        self.active_splitter.content.bgcolor = "#3b82f6"
        self.active_splitter.content.update()
        self.main_page.cursor = ft.MouseCursor.RESIZE_LEFT_RIGHT
        self.main_page.update()

    def on_splitter_pan_update(self, e: ft.DragUpdateEvent):
        """拖拽更新 - 调整面板宽度"""
        if not self.is_dragging: return

        splitter_id, delta, min_pane_width = e.control.data, e.delta_x, 150
        total_available_width = self.main_page.width - 16

        if splitter_id == 1 and self.explorer_visible and self.viewer_visible:
            new_width = self.explorer_width + delta
            if min_pane_width <= new_width < total_available_width - min_pane_width * 2 - 12:
                self.explorer_width = new_width
                self.explorer_container.width = new_width
                self.explorer_container.update()

        elif splitter_id == 2:
            if self.viewer_visible:
                new_width = self.viewer_width + delta
                left_width = self.explorer_width + 6 if self.explorer_visible else 0
                if min_pane_width <= new_width < total_available_width - left_width - 6 - min_pane_width:
                    self.viewer_width = new_width
                    self.viewer_container.width = new_width
                    self.viewer_container.update()
            elif self.explorer_visible and not self.viewer_visible:
                new_width = self.explorer_width + delta
                if min_pane_width <= new_width < total_available_width - 6 - min_pane_width:
                    self.explorer_width = new_width
                    self.explorer_container.width = new_width
                    self.explorer_container.update()

    def on_splitter_pan_end(self, e: ft.DragEndEvent):
        """结束拖拽"""
        self.is_dragging = False
        if self.active_splitter:
            self.active_splitter.content.bgcolor = "#4b5563"
            self.active_splitter.content.update()
        self.main_page.cursor = ft.MouseCursor.BASIC
        self.main_page.update()

    def _update_control_states(self):
        """更新按钮和面板状态"""
        colors = ["#10b981", "#3b82f6", "#f59e0b"]
        for i, (visible, btn) in enumerate(zip(
                [self.explorer_visible, self.viewer_visible, self.editor_visible],
                self.layout_controls.controls[1:]
        )):
            btn.icon_color = colors[i] if visible else "#6b7280"
            btn.style.bgcolor = "#1e40af" if visible else "transparent"

        self.explorer_container.visible = self.explorer_visible
        self.viewer_container.visible = self.viewer_visible
        self.editor_container.visible = self.editor_visible

    def update_layout(self):
        """更新布局"""
        self._update_control_states()

        # 重置容器属性
        for container in [self.explorer_container, self.viewer_container, self.editor_container]:
            container.width = container.expand = None

        # 构建控件列表
        new_controls, visible_containers = [], []

        if self.explorer_visible:
            visible_containers.append(self.explorer_container)
            new_controls.append(self.explorer_container)

        if self.explorer_visible and self.viewer_visible:
            new_controls.append(self.splitter_ex_vi)
            self.splitter_ex_vi.visible = True
        else:
            self.splitter_ex_vi.visible = False

        if self.viewer_visible:
            visible_containers.append(self.viewer_container)
            new_controls.append(self.viewer_container)

        if (self.explorer_visible or self.viewer_visible) and self.editor_visible:
            new_controls.append(self.splitter_vi_ed)
            self.splitter_vi_ed.visible = True
        else:
            self.splitter_vi_ed.visible = False

        if self.editor_visible:
            visible_containers.append(self.editor_container)
            new_controls.append(self.editor_container)

        # 设置宽度和扩展
        if len(visible_containers) == 1:
            visible_containers[0].expand = True
        elif len(visible_containers) > 1:
            for container in visible_containers[:-1]:
                if container == self.explorer_container:
                    container.width = self.explorer_width
                elif container == self.viewer_container:
                    container.width = self.viewer_width
            visible_containers[-1].expand = True

        if not new_controls:
            new_controls.append(ft.Container(
                content=ft.Text("请点击上方按钮显示面板", color="#9ca3af"),
                alignment=ft.alignment.center, expand=True, bgcolor="#111827"
            ))

        self.content_row.controls = new_controls
        try:
            self.content_row.update()
            self.layout_controls.update()
            self.main_page.update()
        except Exception:
            pass

    def create_main_container(self):
        """创建主容器"""
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Text("文件管理", size=12, color="#9ca3af", weight="bold"),
                        ft.Container(expand=True),
                        self.layout_controls
                    ]), padding=ft.padding.symmetric(horizontal=10, vertical=6), bgcolor="#1f2937", border_radius=6
                ),
                self.content_row
            ], expand=True, spacing=0),
            expand=True, bgcolor="#111827", padding=0
        )

    def create_file_manager_tab(self):
        return self.main_container

    def refresh_files(self, page=None):
        if self._refresh_in_progress: return
        try:
            self._refresh_in_progress = True
            self.file_explorer.refresh_files(page)
        finally:
            self._refresh_in_progress = False

    def save_current_file(self, e=None):
        was_dirty = self.file_editor.is_dirty
        self.file_editor.save_current_file()
        if was_dirty and not self.file_editor.is_dirty and self.file_editor.current_file:
            self.file_explorer.set_file_modified(self.file_editor.current_file, False)