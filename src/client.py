#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests, json, datetime, threading, re, time, queue
from pathlib import Path


class DeepSeekClient:
    def __init__(self):
        self.api_key = ""
        self.api_base_url = "https://api.deepseek.com/v1"
        self.base_url = "https://api.deepseek.com/chat/completions"
        self.model = "deepseek-chat"
        self.max_tokens = 2048
        self.temperature = 0.7
        self.top_p = 0.9
        self.frequency_penalty = 0.0
        self.presence_penalty = 0.0
        self.system_content = "你是一个有用的AI助手"
        self.auto_save = self.streaming = self.auto_scroll = self.markdown_render = True
        self.theme = "dark"
        self.font_size = 14
        self.send_shortcut = "Enter"
        self.history = []

        # 消息队列和状态管理
        self.message_queue = queue.Queue()
        self.is_processing = False
        self.current_streaming = False
        self.current_processing_thread = None
        self.stop_requested = False  # 新增：专门的停止请求标志

        self.config_file = Path("./deepseek_config.json")
        self.conversations_dir = Path("./conversations")
        self.current_conversation_file = None
        self.conversations_dir.mkdir(exist_ok=True)
        self.load_config()

    def load_config(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for key, value in config.items():
                        if hasattr(self, key):
                            if key in ['max_tokens', 'font_size']:
                                try:
                                    setattr(self, key, int(value))
                                except:
                                    pass
                            elif key in ['temperature', 'top_p', 'frequency_penalty', 'presence_penalty']:
                                try:
                                    setattr(self, key, float(value))
                                except:
                                    pass
                            elif key in ['auto_save', 'streaming', 'auto_scroll', 'markdown_render']:
                                setattr(self, key, bool(value))
                            else:
                                setattr(self, key, value)
            except Exception as e:
                print(f"加载配置失败: {e}")

    def save_config(self):
        try:
            config = {
                'api_key': self.api_key,
                'api_base_url': self.api_base_url,
                'model': self.model,
                'max_tokens': self.max_tokens,
                'temperature': self.temperature,
                'top_p': self.top_p,
                'frequency_penalty': self.frequency_penalty,
                'presence_penalty': self.presence_penalty,
                'system_content': self.system_content,
                'auto_save': self.auto_save,
                'streaming': self.streaming,
                'auto_scroll': self.auto_scroll,
                'markdown_render': self.markdown_render,
                'theme': self.theme,
                'font_size': self.font_size,
                'send_shortcut': self.send_shortcut
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def _sanitize_filename(self, name):
        """清理名称，使其适合作为文件名"""
        cleaned_name = re.sub(r'[\\/:*?"<>|]', '', name).strip()
        cleaned_name = cleaned_name.replace(' ', '_')
        if len(cleaned_name) > 30:
            cleaned_name = cleaned_name[:30]
        return cleaned_name if cleaned_name else "新对话"

    def generate_conversation_summary(self, history):
        if not self.api_key or len(history) < 2:
            return self.generate_fallback_name(history)

        summary_messages = [
            {
                "role": "system",
                "content": "为对话生成中文标题 限15字内 简洁无标点"
            },
            {
                "role": "user",
                "content": f"请总结以下对话：\n\n{self._format_history_for_summary(history)}"
            }
        ]

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        request_body = {
            "model": self.model,
            "messages": summary_messages,
            "max_tokens": 50,
            "temperature": 0.3,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty
        }

        for attempt in range(3):
            try:
                response = requests.post(self.base_url, headers=headers, json=request_body, timeout=15)
                if response.status_code == 200:
                    summary = response.json()["choices"][0]["message"]["content"].strip()
                    summary = re.sub(r'["""\'。，！？]', '', summary)
                    if len(summary) > 15:
                        summary = summary[:15] + "..."
                    return summary
                elif attempt < 2:
                    time.sleep(1)
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                if attempt < 2:
                    time.sleep(2)
                    continue
            except:
                break
        return self.generate_fallback_name(history)

    def _format_history_for_summary(self, history):
        formatted = []
        for role, content in history[-6:]:
            prefix = "用户" if role == "user" else "助手"
            formatted.append(f"{prefix}: {content[:100]}")
        return "\n".join(formatted)

    def generate_fallback_name(self, history):
        for role, content in reversed(history):
            if role == "user":
                content = content[:50]
                clean_content = re.sub(r'[^\w\u4e00-\u9fff\s]', '', content).strip()
                if len(clean_content) > 15:
                    clean_content = clean_content[:15] + "..."
                if not clean_content:
                    clean_content = "新对话"
                return clean_content
        return "新对话"

    def _rename_conversation_file(self, old_filepath, new_summary):
        """根据新的摘要重命名文件，并更新 current_conversation_file"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            sanitized_name = self._sanitize_filename(new_summary)
            new_filename = self.conversations_dir / f"{sanitized_name}_{timestamp}.json"

            if old_filepath.exists() and old_filepath != new_filename:
                old_filepath.rename(new_filename)
                self.current_conversation_file = new_filename

            return new_filename
        except Exception as e:
            print(f"重命名对话文件失败: {e}")
            return old_filepath

    def update_conversation_name(self, filepath, ui_update_callback=None):
        """异步更新对话名称"""
        try:
            new_summary = self.generate_conversation_summary(self.history)
            if not new_summary:
                return None

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            data["metadata"]["name"] = f"{new_summary} ({datetime.datetime.now().strftime('%m-%d %H:%M')})"
            data["metadata"]["updated_at"] = datetime.datetime.now().isoformat()

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self._rename_conversation_file(filepath, new_summary)

            if ui_update_callback:
                ui_update_callback(data["metadata"]["name"])
            return data["metadata"]["name"]
        except Exception as e:
            print(f"更新对话名称和重命名文件失败: {e}")
            return None

    def save_conversation(self, conversation_name=None):
        """保存对话到文件"""
        if not self.history:
            return

        is_new_conversation = self.current_conversation_file is None

        if conversation_name is None:
            pure_summary = self.generate_conversation_summary(self.history)
            conversation_name = f"{pure_summary} ({datetime.datetime.now().strftime('%m-%d %H:%M')})"
        else:
            if not is_new_conversation:
                try:
                    with open(self.current_conversation_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        conversation_name = data["metadata"].get("name", "新对话")
                except:
                    conversation_name = "新对话"

        if is_new_conversation:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_part = self._sanitize_filename(self.generate_fallback_name(self.history))
            filename = self.conversations_dir / f"{summary_part}_{timestamp}.json"
            self.current_conversation_file = filename

        conversation_data = {
            "metadata": {
                "name": conversation_name or "新对话",
                "created_at": datetime.datetime.now().isoformat(),
                "updated_at": datetime.datetime.now().isoformat(),
                "model": self.model,
                "system_content": self.system_content
            },
            "history": self.history
        }

        try:
            with open(self.current_conversation_file, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存对话失败: {e}")

    def auto_save_conversation(self):
        """异步自动保存对话"""
        if self.auto_save and self.history:
            threading.Thread(target=self.save_conversation, args=(None,), daemon=True).start()

    def chat_stream(self, prompt, callback=None, title_update_callback=None):
        """核心修改：使用消息队列处理连续对话"""
        # 检查是否正在停止状态
        if self.stop_requested:
            return

        # 将消息加入队列
        self.message_queue.put({
            'prompt': prompt,
            'callback': callback,
            'title_update_callback': title_update_callback
        })

        # 如果没有在处理消息，启动处理线程
        if not self.is_processing:
            self._start_processing_messages()

    def _start_processing_messages(self):
        """启动消息处理线程"""

        def process_messages():
            self.is_processing = True
            while not self.message_queue.empty() and not self.stop_requested:
                try:
                    # 从队列中获取下一个消息
                    message_data = self.message_queue.get_nowait()
                    self._process_single_message(
                        message_data['prompt'],
                        message_data['callback'],
                        message_data['title_update_callback']
                    )
                    self.message_queue.task_done()
                except queue.Empty:
                    break

            # 处理完成后重置状态
            self.is_processing = False
            # 只有在没有停止请求时才重置 streaming 状态
            if not self.stop_requested:
                self.current_streaming = False

        # 在后台线程中处理消息
        self.current_processing_thread = threading.Thread(target=process_messages, daemon=True)
        self.current_processing_thread.start()

    def _process_single_message(self, prompt, callback=None, title_update_callback=None):
        """处理单个消息的流式响应"""
        # 检查是否应该停止
        if self.stop_requested:
            return

        self.current_streaming = True
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

        # 构建消息历史
        messages = [{"role": "system", "content": self.system_content}]
        messages.extend([{"role": role, "content": content} for role, content in self.history])
        messages.append({"role": "user", "content": prompt})

        request_body = {
            "model": self.model,
            "messages": messages,
            "stream": self.streaming,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "frequency_penalty": self.frequency_penalty,
            "presence_penalty": self.presence_penalty
        }

        max_retries = 3
        full_response = ""

        for attempt in range(max_retries):
            try:
                # 检查是否应该停止
                if self.stop_requested:
                    break

                response = requests.post(self.base_url, headers=headers, json=request_body, stream=True, timeout=60)
                if response.status_code != 200:
                    if callback and not self.stop_requested:
                        callback(f"API错误: HTTP {response.status_code}", "error")
                    if attempt < max_retries - 1 and not self.stop_requested:
                        time.sleep(2)
                        continue
                    else:
                        break

                # 开始流式响应
                if callback and not self.stop_requested:
                    callback("", "start")

                for line in response.iter_lines():
                    # 检查是否应该停止流式响应
                    if self.stop_requested:
                        if callback:
                            callback("", "stopped")
                        break

                    if line:
                        line = line.decode('utf-8').strip()
                        if line.startswith('data: '):
                            data = line[6:]
                            if data == '[DONE]':
                                break
                            try:
                                content = json.loads(data).get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if content and callback and not self.stop_requested:
                                    callback(content, "stream")
                                    full_response += content
                            except:
                                pass

                # 如果被停止，不保存响应到历史
                if self.stop_requested:
                    if callback:
                        callback("", "cancelled")
                    break

                # 响应完成后立即更新历史并允许处理下一个消息
                if full_response and not self.stop_requested:
                    # 1. 立即更新历史记录
                    self.history.append(("user", prompt))
                    self.history.append(("assistant", full_response))

                    # 2. 立即通知UI响应完成
                    if callback:
                        callback(full_response, "complete")

                    # 3. 在后台进行文件保存操作
                    def background_save_operations():
                        if self.current_conversation_file is None:
                            # 新对话：先快速保存基础文件
                            self.save_conversation()
                            # 然后异步更新名称
                            if title_update_callback:
                                self.update_conversation_name(self.current_conversation_file, title_update_callback)
                        else:
                            # 现有对话：异步保存和更新
                            self.auto_save_conversation()
                            if title_update_callback:
                                self.update_conversation_name(self.current_conversation_file, title_update_callback)

                    threading.Thread(target=background_save_operations, daemon=True).start()

                break

            except requests.exceptions.Timeout:
                if callback and attempt < max_retries - 1 and not self.stop_requested:
                    callback(f"请求超时，第{attempt + 1}次重试...", "retry")
                    time.sleep(2)
                elif callback and not self.stop_requested:
                    callback("连接超时，请检查网络后重试", "error")
                    break
            except requests.exceptions.ConnectionError:
                if callback and attempt < max_retries - 1 and not self.stop_requested:
                    callback(f"连接错误，第{attempt + 1}次重试...", "retry")
                    time.sleep(2)
                elif callback and not self.stop_requested:
                    callback("网络连接失败，请检查网络设置", "error")
                    break
            except Exception as e:
                if callback and not self.stop_requested:
                    callback(f"发生错误: {str(e)}", "error")
                break

    def stop_streaming(self):
        """停止当前流式响应和所有待处理消息"""
        # 设置停止请求标志
        self.stop_requested = True

        # 清空消息队列
        self.clear_queue()

        # 等待当前处理线程结束（如果有）
        if self.current_processing_thread and self.current_processing_thread.is_alive():
            self.current_processing_thread.join(timeout=1.0)

        # 重置停止标志，允许新的输入
        self.stop_requested = False
        self.current_streaming = False
        self.is_processing = False

    def clear_queue(self):
        """清空消息队列"""
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
                self.message_queue.task_done()
            except queue.Empty:
                break

    def new_conversation(self):
        """开始新对话并清空队列"""
        self.stop_streaming()  # 先停止任何正在进行的流式响应
        self.history.clear()
        self.current_conversation_file = None

    def load_conversation(self, filename):
        """加载对话并清空队列"""
        self.stop_streaming()  # 先停止任何正在进行的流式响应
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.history = data.get("history", [])
                self.current_conversation_file = filename
                return data["metadata"].get("name", "未命名对话"), True
        except Exception as e:
            print(f"加载对话失败: {e}")
            return "新对话", False

    def delete_conversation(self, filename):
        try:
            filepath = Path(filename)
            if filepath.exists():
                filepath.unlink()
                return True
        except Exception as e:
            print(f"删除对话失败: {e}")
        return False

    def get_conversation_list(self):
        conversations = []
        for file in self.conversations_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    metadata = data.get("metadata", {})
                    conversations.append({
                        "filename": file.name,
                        "path": file,
                        "name": metadata.get("name", "未命名对话"),
                        "created_at": metadata.get("created_at", ""),
                        "updated_at": metadata.get("updated_at", ""),
                        "message_count": len(data.get("history", [])),
                        "preview": self.get_conversation_preview(data.get("history", []))
                    })
            except Exception as e:
                print(f"读取对话文件失败 {file}: {e}")
                continue

        try:
            conversations.sort(key=lambda x: x["updated_at"], reverse=True)
        except:
            pass

        return conversations

    def get_conversation_preview(self, history):
        for role, content in reversed(history):
            if role == "user":
                return content[:50] + "..." if len(content) > 50 else content
        return "空对话"

    def test_connection(self):
        if not self.api_key:
            return False, "API Key 未设置"

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        request_body = {
            "model": self.model,
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 5
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=request_body, timeout=10)
            if response.status_code == 200:
                return True, "连接成功"
            else:
                return False, f"API错误: HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "连接超时"
        except requests.exceptions.ConnectionError:
            return False, "网络连接失败"
        except Exception as e:
            return False, f"连接测试失败: {str(e)}"