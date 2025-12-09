#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import flet as ft
from pathlib import Path
import os


# =========================================================================
# 辅助类：SyntaxHighlighter
# =========================================================================

class SyntaxHighlighter:
    """语言检测器和显示名称工具类"""

    @staticmethod
    def get_language_name(filepath):
        ext = Path(filepath).suffix.lower()
        language_map = {
            '.py': 'python', '.js': 'javascript', '.java': 'java',
            '.cpp': 'cpp', '.c': 'c', '.h': 'c', '.html': 'html',
            '.css': 'css', '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
            '.md': 'markdown', '.sql': 'sql', '.xml': 'xml', '.txt': 'text',
        }
        return language_map.get(ext, 'text')

    @staticmethod
    def get_display_name(filepath):
        ext = Path(filepath).suffix.lower()
        language_map = {
            '.py': 'Python', '.js': 'JavaScript', '.java': 'Java',
            '.cpp': 'C++', '.c': 'C', '.h': 'C Header', '.html': 'HTML',
            '.css': 'CSS', '.json': 'JSON', '.yaml': 'YAML', '.yml': 'YAML',
            '.md': 'Markdown', '.sql': 'SQL', '.xml': 'XML', '.txt': 'Text',
        }
        return language_map.get(ext, 'Text')


# ====================================================================
# 基础面板 - 负责公共 UI 逻辑 (BaseFilePanel)
# ====================================================================

class BaseFilePanel:
    """所有文件面板的基类，提供公共的UI布局和文件加载/保存逻辑"""

    def __init__(self, main_page):
        self.main_page = main_page
        self.current_file_path = ft.Text("未选择文件", size=11, color="#9ca3af")
        self.current_file = None
        self.encoding = "utf-8"
        self.language_tag = ft.Text("Text", size=11, color="#9ca3af")
        self.encoding_info = ft.Text("UTF-8", size=11, color="#9ca3af")

    def create_component(self):
        # 必须由子类重写
        raise NotImplementedError("Subclasses must implement create_component()")

    def open_file(self, file_info):
        # 必须由子类重写
        raise NotImplementedError("Subclasses must implement open_file()")

    def save_current_file(self, e=None):
        # 必须由子类重写
        raise NotImplementedError("Subclasses must implement save_current_file()")

    def _read_file_content(self, filepath: Path):
        """
        尝试使用多种编码读取文件内容，增加文件大小限制判断。
        """
        if not filepath.exists():
            self.encoding = "Error: Not Found"
            return None

        if filepath.is_dir():
            self.encoding = "Error: Directory"
            return None

        if os.path.getsize(filepath) > 1024 * 1024 * 1:
            self.encoding = "Error: Too Large (>1MB)"
            return None

        self.encoding = "utf-8"

        for encoding in ['utf-8', 'gbk', 'latin-1']:
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    content = f.read()
                self.encoding = encoding
                return content
            except UnicodeDecodeError:
                continue
            except Exception:
                self.encoding = "Error: Read Failed"
                return None

        self.encoding = "Error: Unsupported Encoding"
        return None

    def _create_base_layout(self, content):
        """创建基础布局模板 - 移除了标题栏"""
        return ft.Container(
            content=ft.Column([
                # 代码块头部/状态栏
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(ft.Icons.CODE, size=14, color="#9ca3af"),
                                self.language_tag,
                            ], spacing=4),
                            bgcolor="#374151",
                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            border_radius=3,
                        ),
                        ft.Container(expand=True),
                        # 文件路径信息
                        ft.Row([
                            ft.Icon(ft.Icons.FILE_OPEN, size=14, color="#9ca3af"),
                            self.current_file_path,
                        ], spacing=4),
                        # 编码信息
                        ft.Row([
                            ft.Icon(ft.Icons.LANGUAGE, size=14, color="#9ca3af"),
                            self.encoding_info,
                        ], spacing=4),
                    ]),
                    padding=ft.padding.symmetric(horizontal=15, vertical=6),
                    bgcolor="#252526",
                    border_radius=ft.border_radius.only(top_left=6, top_right=6),
                ),
                content,
            ], expand=True, spacing=0),
            expand=True,
            bgcolor="#111827",
            padding=8,
            border=ft.border.only(left=ft.BorderSide(1, "#374151")),
            border_radius=0,
        )

    def show_snackbar(self, message, success=True):
        """显示提示消息"""
        color = ft.Colors.GREEN_700 if success else ft.Colors.RED_700
        snackbar = ft.SnackBar(
            content=ft.Row([
                ft.Icon(ft.Icons.CHECK_CIRCLE if success else ft.Icons.ERROR, color=ft.Colors.WHITE),
                ft.Text(message, color=ft.Colors.WHITE),
            ]),
            bgcolor=color,
            duration=2000,
        )
        self.main_page.snack_bar = snackbar
        self.main_page.update()


# ====================================================================
# 1. FileViewer (只读 Markdown 高亮)
# ====================================================================

class FileViewer(BaseFilePanel):
    """只读文件查看器，使用 Markdown 进行代码高亮和实时预览"""

    def __init__(self, main_page):
        super().__init__(main_page)
        self._last_content = ""  # 添加内容跟踪，避免重复更新

        self.file_content_markdown = ft.Markdown(
            value="请在左侧文件列表中选择一个文件查看。",
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            code_theme="atom-one-dark",
            selectable=True,
            expand=True,
        )
        self.content_container = ft.Container(
            content=ft.ListView(
                controls=[self.file_content_markdown],
                expand=True,
                padding=ft.padding.all(15)
            ),
            expand=True,
            bgcolor="#1e1e1e",
            border_radius=ft.border_radius.only(bottom_left=6, bottom_right=6),
        )

    def create_component(self):
        """创建组件"""
        return self._create_base_layout(content=self.content_container)

    def _update_ui(self, filepath: Path, content: str):
        """通用 UI 更新逻辑"""
        markdown_lang = SyntaxHighlighter.get_language_name(filepath)
        display_lang = SyntaxHighlighter.get_display_name(filepath)

        markdown_content = f"```{markdown_lang}\n{content}\n```\n"
        self.file_content_markdown.value = markdown_content
        self.current_file_path.value = filepath.name
        self.language_tag.value = display_lang
        self.encoding_info.value = self.encoding.upper()

    def set_content_for_realtime_update(self, content: str, file_path: Path):
        """
        用于接收来自 FileEditor 的实时内容更新。
        添加重复内容检查避免不必要的更新。
        """
        if not file_path or content == self._last_content:
            return

        self._last_content = content
        self._update_ui(file_path, content)

        try:
            self.file_content_markdown.update()
            self.language_tag.update()
        except AssertionError:
            pass

    def open_file(self, file_info):
        """
        打开文件并以 Markdown 代码块形式显示。
        """
        filepath = Path(file_info["path"])
        self.current_file = filepath
        content = self._read_file_content(filepath)

        if content is None:
            file_name = filepath.name
            error_map = {
                "Error: Not Found": f"文件不存在: {file_name}",
                "Error: Directory": f"这是一个目录，无法查看: {file_name}",
                "Error: Too Large (>1MB)": f"文件过大，已阻止查看 (> 1MB): {file_name}",
                "Error: Unsupported Encoding": f"无法以文本形式解码此文件，可能是二进制文件: {file_name}",
                "Error: Read Failed": f"读取文件时发生权限或IO错误: {file_name}",
            }
            error_message = error_map.get(self.encoding, f"读取文件失败: {self.encoding}")

            self.current_file_path.value = f"加载失败: {file_name}"
            self.language_tag.value = "ERROR"
            self.encoding_info.value = self.encoding.upper()
            markdown_content = f"```text\n{error_message}\n```\n"
            self.file_content_markdown.value = markdown_content
            self._last_content = markdown_content
        else:
            self._update_ui(filepath, content)
            self._last_content = content

        try:
            self.current_file_path.update()
            self.language_tag.update()
            self.encoding_info.update()
            self.file_content_markdown.update()
        except AssertionError:
            pass

    def save_current_file(self, e=None):
        """只读模式下不实现保存"""
        self.show_snackbar("当前处于只读模式，无法保存文件。", success=False)


# ====================================================================
# 2. FileEditor (可编辑的 TextField) - 修复重复字符问题
# ====================================================================

class FileEditor(BaseFilePanel):
    """可编辑的文件编辑器 (使用 TextField) - 修复重复字符和光标问题"""

    def __init__(self, main_page, on_content_change=None):
        super().__init__(main_page)
        self.is_dirty = False
        self.on_content_change = on_content_change

        # 修复：使用线性事件处理确保每次变化只处理一次
        self._last_processed_content = ""  # 上次处理的内容
        self._update_in_progress = False  # 防止重入

        # 只缓存修改过的文件
        self.dirty_files_cache = {}
        # 当前文件路径
        self.current_cache_key = None

        self.input_editor = ft.TextField(
            multiline=True,
            expand=True,
            border_color="transparent",
            focused_border_color="transparent",
            text_size=13,
            min_lines=1,
            max_lines=None,
            on_change=self._on_editor_change_linear,  # 使用线性处理版本
            color=ft.Colors.WHITE,
            cursor_color="#60a5fa",
            content_padding=ft.padding.all(15),
            bgcolor=ft.Colors.TRANSPARENT,
            selection_color="#3b82f633",
            text_style=ft.TextStyle(font_family="monospace")
        )

        self.content_container = ft.Container(
            content=self.input_editor,
            expand=True,
            bgcolor="#1e1e1e",
            border_radius=ft.border_radius.only(bottom_left=6, bottom_right=6),
        )

    def create_component(self):
        """创建组件 - 使用 TextField 内容容器"""
        return self._create_base_layout(content=self.content_container)

    def _on_editor_change_linear(self, e):
        """
        线性事件处理 - 确保每次变化只处理一次
        解决非线性事件导致的重复字符问题
        """
        # 防止重入 - 如果正在处理事件，直接返回
        if self._update_in_progress:
            return

        current_content = self.input_editor.value

        # 如果内容没有实际变化，忽略
        if current_content == self._last_processed_content:
            return

        try:
            self._update_in_progress = True

            # 更新状态
            self.is_dirty = True
            self._last_processed_content = current_content

            # 更新缓存
            if self.current_cache_key:
                self.dirty_files_cache[self.current_cache_key] = current_content

            # 更新 UI 状态
            file_name = Path(self.current_file).name if self.current_file else "新文件"
            self.current_file_path.value = f"{file_name}{' •' if self.is_dirty else ''}"
            self.current_file_path.update()

            # 触发实时内容同步回调
            if self.on_content_change and self.current_file:
                self.on_content_change(current_content, Path(self.current_file))

        finally:
            self._update_in_progress = False

    def _get_cache_key(self, filepath):
        """获取文件的缓存键"""
        return str(filepath.absolute())

    def open_file(self, file_info):
        """
        加载文件内容到 TextField，优先使用缓存。
        """
        try:
            filepath = Path(file_info["path"])
            cache_key = self._get_cache_key(filepath)

            # 保存当前文件的编辑状态到缓存（只有修改过的文件）
            if self.current_file and self.is_dirty:
                current_cache_key = self._get_cache_key(Path(self.current_file))
                self.dirty_files_cache[current_cache_key] = self.input_editor.value

            # 重置事件处理状态
            self._last_processed_content = ""
            self._update_in_progress = False

            # 设置新文件
            self.current_file = filepath
            self.current_cache_key = cache_key

            # 检查是否有缓存的修改版本
            if cache_key in self.dirty_files_cache:
                # 从缓存加载修改的版本
                cached_content = self.dirty_files_cache[cache_key]
                self.input_editor.value = cached_content
                self.input_editor.disabled = False
                self.is_dirty = True
                self.current_file_path.value = f"{filepath.name} •"
                self.language_tag.value = SyntaxHighlighter.get_display_name(filepath)
                self.encoding_info.value = "MODIFIED"
                self._last_processed_content = cached_content

                # 触发同步
                if self.on_content_change:
                    self.on_content_change(cached_content, filepath)

            else:
                # 从文件系统加载原始版本
                content = self._read_file_content(filepath)

                if content is None:
                    # 读取失败
                    file_name = filepath.name
                    error_map = {
                        "Error: Not Found": f"文件不存在: {file_name}",
                        "Error: Directory": f"这是一个目录，无法编辑: {file_name}",
                        "Error: Too Large (>1MB)": f"文件过大，已阻止编辑 (> 1MB): {file_name}",
                        "Error: Unsupported Encoding": f"无法以文本形式解码此文件，可能是二进制文件，无法编辑: {file_name}",
                        "Error: Read Failed": f"读取文件时发生权限或IO错误，无法编辑: {file_name}",
                    }
                    error_message = error_map.get(self.encoding, f"读取文件失败: {self.encoding}")

                    self.input_editor.value = error_message
                    self.input_editor.disabled = True
                    self.current_file_path.value = f"加载失败: {file_name}"
                    self.language_tag.value = "ERROR"
                    self.encoding_info.value = self.encoding.upper()
                    self._last_processed_content = error_message
                else:
                    # 成功加载原始文件
                    display_lang = SyntaxHighlighter.get_display_name(filepath)
                    self.input_editor.value = content
                    self.input_editor.disabled = False
                    self.is_dirty = False
                    self.current_file_path.value = filepath.name
                    self.language_tag.value = display_lang
                    self.encoding_info.value = self.encoding.upper()
                    self._last_processed_content = content

                    # 触发同步
                    if self.on_content_change:
                        self.on_content_change(content, filepath)

            self.main_page.update()

        except Exception as e:
            self.input_editor.value = f"加载文件时发生意外错误: {e}"
            self.input_editor.disabled = True
            self.current_file_path.value = "意外错误"
            self._last_processed_content = self.input_editor.value
            self.main_page.update()

    def save_current_file(self, e=None):
        """保存当前编辑的文件到磁盘"""
        if not self.current_file or self.input_editor.disabled:
            self.show_snackbar("没有打开的文件或文件无法保存。", success=False)
            return

        if not self.is_dirty:
            self.show_snackbar("文件没有修改，无需保存。", success=False)
            return

        try:
            content = self.input_editor.value or ""
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(content)

            # 从缓存中移除（因为已经保存到磁盘）
            cache_key = self._get_cache_key(Path(self.current_file))
            if cache_key in self.dirty_files_cache:
                del self.dirty_files_cache[cache_key]

            self.is_dirty = False
            self.encoding = 'utf-8'
            self.current_file_path.value = Path(self.current_file).name
            self.encoding_info.value = 'UTF-8'
            self._last_processed_content = content  # 更新最后内容

            self.show_snackbar("✅ 保存成功", success=True)
            self.current_file_path.update()

        except Exception as e:
            self.show_snackbar(f"❌ 保存失败: {str(e)}", success=False)

    def clear_cache(self):
        """清空文件缓存"""
        self.dirty_files_cache.clear()

    def get_cached_files_count(self):
        """获取缓存的文件数量"""
        return len(self.dirty_files_cache)


# 确保别名指向正确的类
SimpleFileEditor = FileEditor