#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import flet as ft
import datetime
from pathlib import Path
import threading
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

# 常量定义
COLOR_BG_HOVER, COLOR_TEXT_NORMAL, COLOR_ICON_NORMAL = "#374151", "#e5e7eb", "#9ca3af"
COLOR_DIR_NORMAL, COLOR_MODIFIED = "#fbbf24", "#f59e0b"
DIR_BG_COLORS = [ft.Colors.with_opacity(0.05, ft.Colors.BLUE_GREY_500),
                 ft.Colors.with_opacity(0.15, ft.Colors.BLUE_GREY_500)]
LARGE_ICON_SIZE, LARGE_BUTTON_ICON_SIZE, RENAME_BUTTON_ICON_SIZE = 16, 16, 24
TEXT_SIZE_NORMAL, TEXT_SIZE_SMALL = 12, 10


class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, file_explorer): self.file_explorer = file_explorer

    def on_any_event(self, event):
        if not (
                self.file_explorer.current_operation or self.file_explorer.renaming_path or self.file_explorer.switching_dir):
            self.file_explorer.schedule_refresh()


class FileExplorer:
    def __init__(self, main_page, on_file_select=None, root_path: Path = None):  # 👈 1. 接受 root_path 参数
        self.main_page, self.on_file_select = main_page, on_file_select
        self.file_explorer_list = ft.Column(expand=True, spacing=0)
        # 状态初始化
        # 确定 current_directory
        self.current_directory = root_path.resolve() if root_path else Path(".").resolve()

        # 初始化展开目录列表，确保起始目录是展开的
        self.expanded_dirs = {str(self.current_directory)}  # 👈 3. 使用确定的根目录

        self.auto_refresh_timer = None
        self.observer, self.file_structure_cache = None, {}
        self.config_mode, self.items_to_remove, self.renaming_path = False, {}, None
        self.current_operation, self.switching_dir, self.target_parent_directory = None, False, None
        self.modified_files = set()  # self.current_directory 已设置，此处移除重复赋值

        # UI组件
        self.path_input_field = self._create_text_field("输入新目录路径", self.confirm_switch_directory)
        self.config_mode_button = self._create_icon_button(ft.Icons.SETTINGS, self.toggle_config_mode, "设置/管理文件")
        self.new_input_field = self._create_text_field("", self.confirm_create)
        self.confirm_button = self._create_icon_button(ft.Icons.CHECK, self.confirm_create, "确认创建", "#10b981",
                                                       RENAME_BUTTON_ICON_SIZE)
        self.cancel_button = self._create_icon_button(ft.Icons.CLOSE, self.cancel_create, "取消", "#ef4444",
                                                      RENAME_BUTTON_ICON_SIZE)

        self.new_operation_container = ft.Container(
            content=ft.Row([self.new_input_field, self.confirm_button, self.cancel_button], spacing=2),
            padding=8, bgcolor="#1a1f2e", border_radius=4, margin=ft.margin.only(bottom=5), visible=False
        )
        self.start_file_monitoring()

    def _create_text_field(self, hint_text, on_submit):
        return ft.TextField(hint_text=hint_text, height=30, text_size=TEXT_SIZE_NORMAL, content_padding=5,
                            border_color="#4b5563", focused_border_color="#3b82f6", expand=True, on_submit=on_submit)

    def _create_icon_button(self, icon, on_click, tooltip, color=COLOR_ICON_NORMAL, size=LARGE_BUTTON_ICON_SIZE):
        return ft.IconButton(icon=icon, icon_color=color, icon_size=size, tooltip=tooltip,
                             on_click=on_click, style=ft.ButtonStyle(padding=1))

    def set_file_modified(self, file_path, is_modified):
        """设置文件的修改状态"""
        file_path = Path(file_path).resolve()
        if is_modified:
            self.modified_files.add(file_path)
        else:
            self.modified_files.discard(file_path)
        self.refresh_files()

    def is_file_modified(self, file_path):
        return Path(file_path).resolve() in self.modified_files

    def clear_all_modified_marks(self):
        self.modified_files.clear(); self.refresh_files()

    def create_component(self):
        top_bar_content = ft.Container(
            content=ft.Row([ft.Container(expand=True), self.config_mode_button]),
            padding=8, bgcolor="#1f2937",
            border_radius=ft.BorderRadius(top_left=6, top_right=6, bottom_left=0, bottom_right=0)
        )
        return ft.Container(
            content=ft.Column([
                top_bar_content, self.new_operation_container,
                ft.Container(content=ft.ListView([self.file_explorer_list], expand=True, spacing=0), expand=True,
                             padding=ft.padding.only(left=5, right=5, top=0, bottom=5), bgcolor="#1f2937",
                             border_radius=ft.BorderRadius(top_left=0, top_right=0, bottom_left=6, bottom_right=6))
            ], spacing=0), expand=True, bgcolor="#111827", padding=5
        )

    def cancel_all_operations(self):
        is_op_active = any([self.current_operation, self.renaming_path, self.items_to_remove, self.switching_dir])
        if self.current_operation: self.hide_input_fields(); self.target_parent_directory = None
        if self.renaming_path or self.items_to_remove or self.switching_dir:
            self.renaming_path, self.items_to_clear, self.switching_dir = None, {}, False
        if is_op_active: self.show_snackbar("操作已取消"); self.refresh_files()
        return is_op_active

    def cancel_create(self, e):
        self.cancel_all_operations()

    def start_switch_directory(self, e):
        self.cancel_all_operations(); self.switching_dir = True; self.path_input_field.value = str(
            self.current_directory); self.refresh_files()

    def confirm_switch_directory(self, e):
        new_path_str = self.path_input_field.value.strip()
        if not new_path_str: self.show_snackbar("请输入一个路径"); return
        try:
            new_path = Path(new_path_str).resolve()
            if not new_path.is_dir(): self.show_snackbar(f"路径无效或不是目录: {new_path_str}"); return
            self._set_current_directory(new_path);
            self.switching_dir = False
            self.show_snackbar(f"目录已切换到: {new_path_str}");
            self.refresh_files()
        except Exception as ex:
            self.show_snackbar(f"无法切换目录: {str(ex)}")

    def set_as_current_root(self, e, new_path: Path):
        if self.cancel_all_operations(): return
        self._set_current_directory(new_path);
        self.show_snackbar(f"根目录已设置为: {new_path.name}");
        self.refresh_files()

    def go_to_parent_directory(self, e):
        if self.cancel_all_operations(): return
        new_path = self.current_directory.parent.resolve()
        if new_path == self.current_directory: self.show_snackbar("已在系统根目录，无法继续向上"); return
        self._set_current_directory(new_path);
        self.show_snackbar(f"已退回至: {new_path.name}");
        self.refresh_files()

    def _set_current_directory(self, new_path: Path):
        self.current_directory = new_path.resolve();
        self.expanded_dirs = {str(self.current_directory)};
        self.file_structure_cache = {}

    def start_create_op(self, directory: Path, field_type: str):
        if self.renaming_path or self.items_to_remove or self.switching_dir: self.cancel_all_operations()
        self.target_parent_directory = directory;
        self.show_input_field(field_type)

    def show_input_field(self, field_type):
        if self.target_parent_directory is None: self.show_snackbar("新建目标目录未设置，请重试"); return
        self.current_operation = field_type
        target_name = self._get_target_display_name()
        self.new_input_field.hint_text = f"在 [{target_name}] 中创建{'文件' if field_type == 'file' else '文件夹'}"
        for control in [self.new_input_field, self.confirm_button, self.cancel_button, self.new_operation_container]:
            control.visible = True
        self.new_input_field.value = "";
        self.new_input_field.focus();
        self.main_page.update()

    def _get_target_display_name(self):
        try:
            target_rel_path = self.target_parent_directory.relative_to(self.current_directory)
            return str(target_rel_path) if str(target_rel_path) != "." else "当前根目录"
        except ValueError:
            return self.target_parent_directory.name

    def hide_input_fields(self):
        for control in [self.new_input_field, self.confirm_button, self.cancel_button, self.new_operation_container]:
            control.visible = False
        self.current_operation, self.new_input_field.value, self.target_parent_directory = None, "", None

    def confirm_create(self, e):
        name = self.new_input_field.value.strip()
        if not name: self.show_snackbar("请输入名称"); return
        if self.target_parent_directory is None: self.show_snackbar(
            "创建失败：目标目录丢失"); self.hide_input_fields(); self.refresh_files(); return
        try:
            if self.current_operation == 'file':
                (self.target_parent_directory / name).touch()
            else:
                (self.target_parent_directory / name).mkdir(exist_ok=True)
            self.hide_input_fields();
            self.show_snackbar(f"{'文件' if self.current_operation == 'file' else '文件夹'}创建成功: {name}")
            self.file_structure_cache = {};
            self.refresh_files()
        except Exception as ex:
            self.show_snackbar(f"创建失败: {str(ex)}")

    def create_directory_item(self, dir_name, dir_data, parent_indent, current_depth, is_virtual_root=False):
        dir_path_str = str(dir_data["path"])
        is_expanded = dir_path_str in self.expanded_dirs or is_virtual_root

        if dir_data["path"] == self.renaming_path:
            return self.create_rename_input_row({"path": dir_data["path"], "name": dir_name, "is_dir": True},
                                                parent_indent)

        if self.switching_dir and is_virtual_root:
            return self._create_switch_directory_input()

        # 显示内容设置
        if is_virtual_root:
            display_name = f"当前目录: {self.current_directory.name}" if self.current_directory.name != "" else f"当前根目录: {self.current_directory.resolve()}"
            dir_color = COLOR_DIR_NORMAL
        else:
            display_name, dir_color = dir_name, self.get_folder_color(dir_name)

        bg_color = DIR_BG_COLORS[min(current_depth, len(DIR_BG_COLORS) - 1)]
        buttons = self._create_directory_buttons(dir_data, is_virtual_root)

        dir_title_row = ft.Row([
            ft.Container(width=parent_indent),
            ft.Icon(
                name=ft.Icons.KEYBOARD_ARROW_DOWN if is_expanded and not is_virtual_root else ft.Icons.KEYBOARD_ARROW_RIGHT,
                color=dir_color, size=LARGE_ICON_SIZE, visible=not is_virtual_root),
            ft.Icon(name="folder_open" if is_expanded or is_virtual_root else "folder", color=dir_color,
                    size=LARGE_ICON_SIZE),
            ft.Text(display_name, size=TEXT_SIZE_NORMAL, color=dir_color, weight="bold", expand=True), *buttons
        ], spacing=2)

        dir_title = ft.Container(content=dir_title_row, bgcolor=None, padding=ft.padding.only(top=2, bottom=2, right=5),
                                 on_click=lambda e: self.toggle_directory(
                                     dir_path_str) if not is_virtual_root else None,
                                 data={"default_bg": None}, on_hover=self._on_hover_change, border_radius=3)

        dir_content_column = ft.Column(spacing=0)
        if is_expanded or is_virtual_root:
            self._render_directory_contents(dir_data, dir_content_column, parent_indent, current_depth)

        return ft.Container(content=ft.Column([dir_title, dir_content_column], spacing=0), bgcolor=bg_color,
                            margin=ft.margin.only(bottom=5) if is_virtual_root else None, border_radius=5)
    def _create_directory_buttons(self, dir_data, is_virtual_root):
        buttons = []
        if self.config_mode:
            if is_virtual_root:
                buttons.append(
                    self._create_icon_button(ft.Icons.COMPARE_ARROWS, self.start_switch_directory, "切换当前目录",
                                             "#3b82f6"))
                if self.current_directory.parent.resolve() != self.current_directory.resolve():
                    buttons.append(
                        self._create_icon_button(ft.Icons.ARROW_UPWARD, self.go_to_parent_directory, "退回至上一级目录",
                                                 "#f59e0b"))
            else:
                buttons.extend([
                    self._create_icon_button(ft.Icons.FOLDER_OPEN,
                                             lambda e, path=dir_data["path"]: self.set_as_current_root(e, path),
                                             "设置为当前根目录", "#10b981"),
                    self._create_icon_button(ft.Icons.EDIT_SQUARE, lambda e, path=dir_data["path"],
                                                                          name=dir_data["name"]: self.start_rename_mode(
                        path, name), "重命名"),
                    self._create_icon_button(ft.Icons.REMOVE_CIRCLE_OUTLINE, lambda e, info={"path": dir_data["path"],
                                                                                             "name": dir_data[
                                                                                                 "name"]}: self.show_remove_confirmation(
                        info), "删除此文件夹", "#ef4444")
                ])
        return buttons

    def _create_switch_directory_input(self):
        return ft.Container(content=ft.Row([
            ft.Icon(name=ft.Icons.FOLDER_OPEN, color="#3b82f6", size=LARGE_ICON_SIZE), self.path_input_field,
            self._create_icon_button(ft.Icons.CHECK, self.confirm_switch_directory, "确认切换", "#10b981",
                                     RENAME_BUTTON_ICON_SIZE),
            self._create_icon_button(ft.Icons.CLOSE, self.cancel_create, "取消", "#ef4444", RENAME_BUTTON_ICON_SIZE)
        ], spacing=2), padding=ft.padding.all(5), bgcolor="#1f2937", border_radius=3, margin=ft.margin.only(bottom=5))

    def toggle_config_mode(self, e):
        if self.cancel_all_operations(): return
        self.config_mode = not self.config_mode
        self.config_mode_button.icon_color = "#3b82f6" if self.config_mode else COLOR_ICON_NORMAL
        self.refresh_files()

    def start_rename_mode(self, original_path: Path, original_name: str):
        self.cancel_all_operations();
        self.renaming_path = original_path;
        self.refresh_files()

    def toggle_directory(self, dir_path_str):
        if self.cancel_all_operations(): return
        if dir_path_str in self.expanded_dirs:
            self.expanded_dirs.remove(dir_path_str)
        else:
            self.expanded_dirs.add(dir_path_str)
        self.refresh_files()

    def on_file_selected(self, file_info):
        if self.cancel_all_operations(): return
        if self.on_file_select: self.on_file_select(file_info)

    def show_remove_confirmation(self, file_info):
        if file_info["path"] not in self.items_to_remove: self.cancel_all_operations()
        self.items_to_remove[file_info["path"]] = file_info;
        self.refresh_files()

    def hide_remove_confirmation(self, filepath):
        self.items_to_remove.pop(filepath, None); self.refresh_files()

    def _rename_item(self, new_name):
        if not self.renaming_path: self.show_snackbar(
            "重命名路径丢失"); self.renaming_path = None; self.refresh_files(); return
        old_path, new_path = self.renaming_path, self.renaming_path.parent / new_name
        if new_path.exists(): self.show_snackbar(f"新名称已存在: {new_name}"); return
        try:
            old_path.rename(new_path)
            if old_path.resolve() in self.modified_files:
                self.modified_files.remove(old_path.resolve());
                self.modified_files.add(new_path.resolve())
            self.show_snackbar(f"重命名成功: {old_path.name} -> {new_name}");
            self.renaming_path = None
            self.file_structure_cache = {};
            self.refresh_files()
        except Exception as ex:
            self.show_snackbar(f"重命名失败: {str(ex)}"); self.renaming_path = None; self.refresh_files()

    def create_rename_input_row(self, file_info, indent):
        rename_input = ft.TextField(value=file_info["name"], height=30, text_size=TEXT_SIZE_NORMAL, content_padding=5,
                                    border_color="#3b82f6", focused_border_color="#3b82f6", autofocus=True, expand=True)
        return ft.Container(content=ft.Row([
            ft.Container(width=indent),
            ft.Icon(name=ft.Icons.FOLDER if file_info["is_dir"] else ft.Icons.INSERT_DRIVE_FILE, color="#3b82f6",
                    size=LARGE_ICON_SIZE),
            rename_input,
            self._create_icon_button(ft.Icons.CHECK, lambda e: self._rename_item(rename_input.value.strip()),
                                     "确认重命名", "#10b981", RENAME_BUTTON_ICON_SIZE),
            self._create_icon_button(ft.Icons.CLOSE, self.cancel_create, "取消", "#ef4444", RENAME_BUTTON_ICON_SIZE)
        ], spacing=2), padding=ft.padding.only(top=1, bottom=1, right=5), bgcolor="#1f2937", border_radius=3)

    def create_file_item(self, file_info, indent=10):
        if file_info["path"] == self.renaming_path:
            return self.create_rename_input_row(file_info, indent)

        # 修复这里：分别获取文件图标和颜色
        file_icon_data = self.get_file_icon(file_info["extension"])
        file_icon = file_icon_data[0]  # 图标名称
        icon_color = file_icon_data[1]  # 图标颜色
        is_modified = self.is_file_modified(file_info["path"])

        config_buttons = []
        if self.config_mode:
            config_buttons.extend([
                self._create_icon_button(ft.Icons.EDIT_SQUARE,
                                         lambda e, path=file_info["path"],
                                                name=file_info["name"]: self.start_rename_mode(path, name),
                                         "重命名"),
                self._create_icon_button(ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                         lambda e, info=file_info: self.show_remove_confirmation(info),
                                         "删除此文件", "#ef4444")
            ])

        file_row = ft.Row([
            ft.Container(width=indent),
            ft.Icon(name=file_icon, color=icon_color, size=LARGE_ICON_SIZE),
            ft.Text(file_info["name"], size=TEXT_SIZE_NORMAL,
                    color=COLOR_MODIFIED if is_modified else COLOR_TEXT_NORMAL,
                    weight="bold" if is_modified else "normal", expand=True),
            ft.Icon(name=ft.Icons.CIRCLE, color=COLOR_MODIFIED, size=8,
                    visible=is_modified, tooltip="已修改未保存"),
            ft.Text(self.format_size(file_info["size"]), size=TEXT_SIZE_SMALL,
                    color=COLOR_MODIFIED if is_modified else "#6b7280"),
            *config_buttons
        ], spacing=2)

        return ft.Container(content=file_row, bgcolor=None, padding=ft.padding.only(top=1, bottom=1, right=5),
                            on_click=lambda e: self.on_file_selected(file_info), data={"default_bg": None},
                            on_hover=self._on_hover_change, border_radius=3)
    def add_new_buttons_to_column(self, directory, indent, column):
        if any([self.renaming_path, self.config_mode, self.switching_dir, self.current_operation]): return
        column.controls.append(ft.Container(content=ft.Row([
            ft.Container(width=indent),
            self._create_icon_button(ft.Icons.ADD, lambda e, d=directory: self.start_create_op(d, 'file'),
                                     f"在 '{directory.name}' 中新建文件", "#10b981"),
            self._create_icon_button(ft.Icons.CREATE_NEW_FOLDER,
                                     lambda e, d=directory: self.start_create_op(d, 'folder'),
                                     f"在 '{directory.name}' 中新建文件夹", "#f59e0b"),
            ft.Text("新建...", size=TEXT_SIZE_SMALL, color="#6b7280")
        ], spacing=2), padding=ft.padding.only(top=1, bottom=1)))

    def create_remove_confirmation(self, file_info, indent=10):
        return ft.Container(content=ft.Row([
            ft.Container(width=indent), ft.Icon(ft.Icons.WARNING_AMBER, color="#f59e0b", size=LARGE_ICON_SIZE),
            ft.Text(f"删除 '{file_info['name']}'?", size=TEXT_SIZE_NORMAL, color="#f59e0b", expand=True),
            self._create_icon_button(ft.Icons.CHECK, lambda e: self.confirm_remove(file_info), "确认删除", "#10b981",
                                     RENAME_BUTTON_ICON_SIZE),
            self._create_icon_button(ft.Icons.CLOSE, lambda e: self.hide_remove_confirmation(file_info["path"]),
                                     "取消删除", "#ef4444", RENAME_BUTTON_ICON_SIZE)
        ]), padding=8, bgcolor="#7f1d1d", border_radius=4, margin=ft.margin.only(bottom=2))

    def confirm_remove(self, file_info):
        try:
            filepath = file_info["path"]
            if filepath.resolve() in self.modified_files: self.modified_files.remove(filepath.resolve())
            if filepath.is_file():
                filepath.unlink()
            else:
                shutil.rmtree(filepath)
            self.show_snackbar(f"删除成功: {file_info['name']}");
            self.hide_remove_confirmation(filepath)
            self.file_structure_cache = {};
            self.refresh_files()
        except Exception as ex:
            self.show_snackbar(f"删除失败: {str(ex)}"); self.hide_remove_confirmation(filepath)

    def _on_hover_change(self, e):
        container = e.control
        if e.data == "true":
            container.data["default_bg"], container.bgcolor = container.bgcolor, COLOR_BG_HOVER
        else:
            container.bgcolor = container.data.get("default_bg", None)
        if self.main_page and hasattr(self.main_page, 'update'):
            (self.main_page.page.run_thread if self.main_page.page else lambda f: f())(self.main_page.update)

    def start_file_monitoring(self):
        try:
            if self.observer: self.observer.stop(); self.observer.join()
            self.observer = Observer();
            self.observer.schedule(FileChangeHandler(self), str(self.current_directory), recursive=True)
            self.observer.start()
        except Exception as e:
            print(f"文件监控启动失败: {e}")

    def schedule_refresh(self):
        if self.auto_refresh_timer: self.auto_refresh_timer.cancel()
        self.auto_refresh_timer = threading.Timer(0.3, self.refresh_files);
        self.auto_refresh_timer.start()

    def refresh_files(self, page=None):
        def update_ui():
            self.file_explorer_list.controls.clear()
            try:
                if not self.file_structure_cache or self.file_structure_cache[
                    "path"].resolve() != self.current_directory.resolve():
                    self.file_structure_cache = self.get_directory_structure(self.current_directory)
                virtual_root_data = {"name": str(self.current_directory.name), "path": self.current_directory,
                                     "files": self.file_structure_cache.get("files", []),
                                     "subdirs": self.file_structure_cache.get("subdirs", {})}
                self.file_explorer_list.controls.append(
                    self.create_directory_item(dir_name=virtual_root_data["name"], dir_data=virtual_root_data,
                                               parent_indent=0, current_depth=0, is_virtual_root=True))
            except Exception as e:
                self.file_explorer_list.controls.append(
                    ft.Container(content=ft.Text(f"读取错误: {str(e)}", size=12, color="#ef4444"),
                                 padding=20, alignment=ft.alignment.center))
            self.main_page.update()

        (self.main_page.page.run_thread if self.main_page.page else lambda f: f())(update_ui)

    def get_directory_structure(self, directory):
        directory, structure = directory.resolve(), {"name": directory.name, "path": directory, "files": [],
                                                     "subdirs": {}}
        try:
            items = [item for item in directory.iterdir() if
                     not item.name.startswith('.') and item.name != '__pycache__']
            for item in items:
                if item.is_file():
                    stat = item.stat()
                    structure["files"].append({"path": item.resolve(), "name": item.name, "size": stat.st_size,
                                               "modified": datetime.datetime.fromtimestamp(stat.st_mtime),
                                               "extension": item.suffix.lower(), "is_dir": False})
                else:
                    structure["subdirs"][item.name] = {"name": item.name, "path": item.resolve(), "files": [],
                                                       "subdirs": {}, "is_dir": True}
        except Exception as e:
            print(f"读取目录错误 {directory}: {e}")
        structure["files"].sort(key=lambda x: x["name"]);
        structure["subdirs"] = dict(sorted(structure["subdirs"].items()))
        return structure

    def _render_directory_contents(self, dir_data, parent_column, current_indent, current_depth):
        current_path, next_indent = dir_data["path"], current_indent + 10
        should_render_content = (current_depth == 0) or (str(current_path) in self.expanded_dirs)
        if should_render_content:
            self.add_new_buttons_to_column(current_path, next_indent, parent_column)
            for file_info in dir_data["files"]:
                if file_info["path"] in self.items_to_remove:
                    parent_column.controls.append(self.create_remove_confirmation(file_info, next_indent))
                else:
                    parent_column.controls.append(self.create_file_item(file_info, next_indent))
            for subdir_name, subdir_data in dir_data["subdirs"].items():
                if str(subdir_data["path"]) in self.expanded_dirs: subdir_data = self.get_directory_structure(
                    subdir_data["path"])
                subdir_path_resolved = subdir_data["path"].resolve()
                if subdir_path_resolved in self.items_to_remove:
                    parent_column.controls.append(
                        self.create_remove_confirmation({"path": subdir_path_resolved, "name": subdir_name},
                                                        next_indent))
                else:
                    parent_column.controls.append(
                        self.create_directory_item(subdir_name, subdir_data, next_indent, current_depth + 1))

    def format_size(self, size):
        for unit in ['B', 'K', 'M']:
            if size < 1024: return f"{size:.0f}{unit}"
            size /= 1024
        return f"{size:.1f}G"

    def get_file_icon(self, file_extension):
        """更全面的文件类型图标映射"""
        icon_map = {
            # 编程语言文件
            ".py": ("code", "#3776ab"),  # Python - 蓝色
            ".js": ("javascript", "#f7df1e"),  # JavaScript - 黄色
            ".ts": ("javascript", "#3178c6"),  # TypeScript - 蓝色
            ".jsx": ("react", "#61dafb"),  # React JSX - 青色
            ".tsx": ("react", "#3178c6"),  # React TSX - 蓝色
            ".java": ("code", "#ed8b00"),  # Java - 橙色
            ".cpp": ("code", "#00599c"),  # C++ - 蓝色
            ".c": ("code", "#a8b9cc"),  # C - 浅蓝
            ".cs": ("code", "#68217a"),  # C# - 紫色
            ".go": ("code", "#00add8"),  # Go - 青色
            ".rs": ("code", "#dea584"),  # Rust - 橙色
            ".php": ("code", "#777bb4"),  # PHP - 紫色
            ".rb": ("code", "#cc342d"),  # Ruby - 红色

            # 标记语言
            ".html": ("html", "#e34f26"),  # HTML - 橙色
            ".css": ("css", "#1572b6"),  # CSS - 蓝色
            ".scss": ("css", "#cd6799"),  # SCSS - 粉色
            ".sass": ("css", "#cd6799"),  # SASS - 粉色
            ".xml": ("code", "#f0ad4e"),  # XML - 黄色
            ".yaml": ("code", "#cb171e"),  # YAML - 红色
            ".yml": ("code", "#cb171e"),  # YAML - 红色

            # 配置文件
            ".json": ("data_object", "#ffffff"),  # JSON - 白色
            ".toml": ("settings", "#9c4221"),  # TOML - 棕色
            ".ini": ("settings", "#cccccc"),  # INI - 灰色
            ".conf": ("settings", "#4caf50"),  # CONF - 绿色
            ".config": ("settings", "#4caf50"),  # CONFIG - 绿色

            # 文档文件
            ".md": ("article", "#ffffff"),  # Markdown - 白色
            ".txt": ("description", "#9ca3af"),  # 文本文件 - 灰色
            ".doc": ("description", "#2b579a"),  # Word - 蓝色
            ".docx": ("description", "#2b579a"),  # Word - 蓝色
            ".pdf": ("picture_as_pdf", "#f40f02"),  # PDF - 红色

            # 数据文件
            ".csv": ("table_chart", "#4caf50"),  # CSV - 绿色
            ".xlsx": ("table_chart", "#217346"),  # Excel - 深绿
            ".db": ("storage", "#ff9800"),  # 数据库 - 橙色
            ".sql": ("storage", "#ff9800"),  # SQL - 橙色

            # 图片文件
            ".png": ("image", "#4caf50"),  # PNG - 绿色
            ".jpg": ("image", "#f44336"),  # JPG - 红色
            ".jpeg": ("image", "#f44336"),  # JPEG - 红色
            ".gif": ("gif", "#ff4081"),  # GIF - 粉色
            ".svg": ("image", "#ffb300"),  # SVG - 黄色
            ".ico": ("image", "#ff9800"),  # ICO - 橙色

            # 媒体文件
            ".mp4": ("movie", "#ff5722"),  # MP4 - 深橙
            ".avi": ("movie", "#ff5722"),  # AVI - 深橙
            ".mov": ("movie", "#007aff"),  # MOV - 蓝色
            ".mp3": ("music_note", "#e91e63"),  # MP3 - 粉色
            ".wav": ("music_note", "#9c27b0"),  # WAV - 紫色

            # 压缩文件
            ".zip": ("folder_zip", "#ff9800"),  # ZIP - 橙色
            ".rar": ("folder_zip", "#f44336"),  # RAR - 红色
            ".tar": ("folder_zip", "#673ab7"),  # TAR - 深紫
            ".gz": ("folder_zip", "#009688"),  # GZ - 青色

            # 可执行文件
            ".exe": ("apps", "#4caf50"),  # EXE - 绿色
            ".app": ("apps", "#2196f3"),  # APP - 蓝色
            ".sh": ("terminal", "#4caf50"),  # Shell - 绿色
            ".bat": ("terminal", "#607d8b"),  # Batch - 蓝灰
        }

        return icon_map.get(file_extension.lower(), ("insert_drive_file", "#9ca3af"))

    def get_folder_color(self, folder_name):
        """更智能的文件夹颜色映射"""
        color_map = {
            # 源码目录
            "src": "#22c55e", "source": "#22c55e", "sources": "#22c55e",
            "app": "#22c55e", "apps": "#22c55e", "application": "#22c55e",

            # 库和组件
            "lib": "#3b82f6", "library": "#3b82f6", "libraries": "#3b82f6",
            "components": "#3b82f6", "component": "#3b82f6", "widgets": "#3b82f6",
            "modules": "#3b82f6", "module": "#3b82f6",

            # 测试相关
            "test": "#f97316", "tests": "#f97316", "testing": "#f97316",
            "spec": "#f97316", "__tests__": "#f97316",

            # 配置相关
            "config": "#a855f7", "configuration": "#a855f7", "conf": "#a855f7",
            "settings": "#a855f7", ".config": "#a855f7",

            # 文档
            "docs": "#14b8a6", "doc": "#14b8a6", "documentation": "#14b8a6",
            "readme": "#14b8a6",

            # 数据
            "data": "#ef4444", "database": "#ef4444", "db": "#ef4444",
            "storage": "#ef4444",

            # 静态资源
            "public": "#f59e0b", "static": "#f59e0b", "assets": "#f59e0b",
            "resources": "#f59e0b", "resource": "#f59e0b",

            # 构建相关
            "build": "#8b5cf6", "dist": "#8b5cf6", "output": "#8b5cf6",
            "target": "#8b5cf6", "out": "#8b5cf6",

            # 工具脚本
            "scripts": "#06b6d4", "script": "#06b6d4", "tools": "#06b6d4",
            "utils": "#06b6d4", "utilities": "#06b6d4",

            # 环境相关
            "env": "#10b981", "environment": "#10b981", ".env": "#10b981",
            "venv": "#10b981", "virtualenv": "#10b981",

            # 临时文件
            "temp": "#6b7280", "tmp": "#6b7280", "cache": "#6b7280",
            ".cache": "#6b7280", "__pycache__": "#6b7280",
        }

        return color_map.get(folder_name.lower(), COLOR_DIR_NORMAL)

    def show_snackbar(self, message):
        def show():
            self.main_page.snack_bar = ft.SnackBar(content=ft.Text(message))
            self.main_page.snack_bar.open = True;
            self.main_page.update()

        (self.main_page.page.run_thread if self.main_page.page else lambda f: f())(show)

    def __del__(self):
        if self.observer: self.observer.stop(); self.observer.join()