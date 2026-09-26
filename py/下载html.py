# -*- coding: utf-8 -*-
import os
import sys
import json
import re
import time
import threading
from requests import Session
from base.spider import Spider

sys.path.append("..")

class Spider(Spider):
    
    # 内置配置
    DEFAULT_SAVE_DIR = "/storage/emulated/0/网页源/"
    BUILTIN_LINKS = {
        "宝宝_AV": "https://av-9du.pages.dev/",
        "宝宝_B站": "https://bili-1k4.pages.dev/",
        "宝宝_盘链": "https://pl-d8z.pages.dev/",
        "宝宝_Eclipse": "https://vvee.ccwu.cc/",
        "宝宝_nostr筛选": "https://nostr.aws.dpdns.org/",
        "宝宝_nostr移动端": "https://noir-cmp.pages.dev/",
        "宝宝_nostrTV端": "https://nostrtv.aws.dpdns.org/",
        "宝宝_玩偶聚合": "https://wo.vivas.cc.cd",
        "宝宝_直播聚合": "https://live-a3r.pages.dev/",
        "宝宝_pomo": "https://pomo.920410.xyz/",
        "宝宝_现在就听": "https://am-4u2.pages.dev/",
        "宝宝_听书": "https://ts-agk.pages.dev/",
        "宝宝_pomo赛博": "https://cyber.920410.xyz/",
        "宝宝_油管": "https://yt-cas.pages.dev/",
        "宝宝_qq音乐": "https://q-16a.pages.dev/",
    }
    
    # 动作指令标识
    CMD_INPUT_LINKS = "download::input_links"
    CMD_BUILTIN_LINKS = "download::builtin_links"
    
    def getName(self):
        return "网页源码下载工具"

    def init(self, extend=""):
        self.session = Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        })
        # 确保默认目录存在
        try:
            if not os.path.exists(self.DEFAULT_SAVE_DIR):
                os.makedirs(self.DEFAULT_SAVE_DIR)
        except Exception:
            pass

    # 首页分类
    def homeContent(self, filter):
        return {
            "class": [
                {"type_id": "download_tools", "type_name": "下载工具"}
            ],
            "filters": {}
        }

    # 分类列表
    def categoryContent(self, tid, pg, filter, extend):
        if tid == "download_tools":
            return {
                "list": [
                    {
                        "vod_id": self.CMD_INPUT_LINKS,
                        "vod_name": "输入链接下载源码",
                        "vod_pic": "",
                        "vod_remarks": "手动输入一个或多个链接(换行分隔)",
                        "action": self.CMD_INPUT_LINKS,
                        "style": {"type": "list", "ratio": 1.1}
                    },
                    {
                        "vod_id": self.CMD_BUILTIN_LINKS,
                        "vod_name": "下载内置链接源码",
                        "vod_pic": "",
                        "vod_remarks": f"共 {len(self.BUILTIN_LINKS)} 个预设链接",
                        "action": self.CMD_BUILTIN_LINKS,
                        "style": {"type": "list", "ratio": 1.1}
                    }
                ],
                "page": 1,
                "pagecount": 1
            }
        return {"list": [], "page": 1, "pagecount": 1}

    # ====================== Action 动作路由 ======================
    def action(self, action_str):
        if action_str == self.CMD_INPUT_LINKS:
            self._input_links_dialog()
        elif action_str == self.CMD_BUILTIN_LINKS:
            self._download_builtin_links()
        return json.dumps({"msg": "ok"}, ensure_ascii=False)

    def detailContent(self, ids):
        return {"list": []}

    def playerContent(self, flag, id, vipFlags):
        return {"parse": 0, "playUrl": "", "url": "about:blank", "header": {}}

    # ====================== 核心逻辑 ======================
    
    def _download_single(self, url, save_path, session):
        """
        下载单个链接源码
        返回: (success: bool, message: str, file_path: str)
        """
        url = url.strip()
        if not url:
            return False, "链接为空", ""
        
        try:
            resp = session.get(url, timeout=30, allow_redirects=True)
            resp.raise_for_status()
            
            # 尝试检测编码，优先 utf-8
            encoding = resp.encoding
            if not encoding or encoding == 'ISO-8859-1':
                # 尝试从 content-type 获取
                ct = resp.headers.get('Content-Type', '')
                if 'charset=' in ct:
                    encoding = ct.split('charset=')[-1].strip().strip('"').strip("'")
            if not encoding or encoding == 'ISO-8859-1':
                encoding = 'utf-8'
                
            content = resp.text
            
            # 确保目录存在
            d = os.path.dirname(save_path)
            if d and not os.path.exists(d):
                os.makedirs(d)
            
            # 写入文件
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return True, f"成功 ({len(content)} 字节)", save_path
            
        except Exception as e:
            # 失败时不保存文件
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except:
                    pass
            return False, f"失败: {str(e)}", ""

    def _build_log(self, results):
        """构建详细日志"""
        lines = []
        success_count = 0
        fail_count = 0
        
        for r in results:
            status = "✅" if r['success'] else "❌"
            lines.append(f"{status} {r['name']}: {r['message']}")
            if r['success']:
                lines.append(f"   保存至: {r['path']}")
                success_count += 1
            else:
                fail_count += 1
        
        lines.insert(0, "=" * 40)
        lines.insert(0, "下载结果汇总:")
        lines.append("")
        lines.append(f"总计: {len(results)} | 成功: {success_count} | 失败: {fail_count}")
        lines.append("=" * 40)
        
        return "\n".join(lines)

    # ====================== UI 方法 ======================
    
    def _input_links_dialog(self):
        """弹窗输入链接"""
        dialog_ref = [None]  # 保存弹窗引用
        
        def on_ui(act, Builder, EditText, TextView, LinearLayout, LP, InputType, Click, Toast):
            root = LinearLayout(act)
            root.setOrientation(LinearLayout.VERTICAL)
            root.setPadding(36, 12, 36, 0)
            
            tip = TextView(act)
            tip.setText("请输入要下载的链接(每行一个):\n例如:\nhttps://example.com\nhttps://test.com")
            tip.setTextSize(14.0)
            root.addView(tip, LP(-1, -2))
            
            edit = EditText(act)
            edit.setSingleLine(False)
            edit.setMinLines(6)
            edit.setHint("https://example.com")
            edit.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS)
            root.addView(edit, LP(-1, -2))
            
            def do_download():
                raw = str(edit.getText().toString()).strip()
                if not raw:
                    Toast.makeText(act, "请输入至少一个链接", 0).show()
                    return
                
                links = [l.strip() for l in raw.split("\n") if l.strip()]
                if not links:
                    Toast.makeText(act, "请输入至少一个链接", 0).show()
                    return
                
                # 关闭输入弹窗
                if dialog_ref[0]:
                    dialog_ref[0].dismiss()
                
                # 执行下载并实时更新日志
                self._download_with_live_log(links, "input_links")
            
            # 创建并保存弹窗引用
            dialog = Builder(act).setTitle("输入链接下载源码").setView(root).setNegativeButton("取消", None).setPositiveButton("开始下载", Click(do_download)).create()
            dialog_ref[0] = dialog
            dialog.show()
        
        self._run_on_ui(on_ui)

    def _download_builtin_links(self):
        """下载内置链接"""
        links = list(self.BUILTIN_LINKS.items())  # [(name, url), ...]
        self._download_with_live_log(links, "builtin")

    def _build_html_log(self, log_entries):
        """构建 HTML 格式的日志"""
        html_parts = [
            '<!DOCTYPE html><html><head><meta charset="utf-8">',
            '<style>',
            'body { font-family: monospace; font-size: 13px; padding: 12px; background: #fafafa; color: #333; margin: 0; }',
            '.info { color: #1976D2; }',
            '.success { color: #2E7D32; font-weight: bold; }',
            '.fail { color: #C62828; font-weight: bold; }',
            '.path { color: #666; font-size: 12px; padding-left: 12px; }',
            '.separator { border-top: 1px solid #ddd; margin: 8px 0; padding-top: 8px; }',
            '.header { font-size: 15px; font-weight: bold; color: #333; border-bottom: 2px solid #1976D2; padding-bottom: 6px; margin-bottom: 10px; }',
            '.progress { background: #E3F2FD; padding: 6px 10px; border-radius: 4px; margin: 4px 0; color: #1565C0; }',
            '</style></head><body>',
        ]
        for entry in log_entries:
            entry = entry.replace("&", "&").replace("<", "<").replace(">", ">")
            if entry.startswith("✅"):
                html_parts.append(f'<div class="success">{entry}</div>')
            elif entry.startswith("❌"):
                html_parts.append(f'<div class="fail">{entry}</div>')
            elif entry.startswith("["):
                html_parts.append(f'<div class="info">{entry}</div>')
            elif entry.startswith("进度:") or entry.startswith("总计:") or entry.startswith("下载完成"):
                html_parts.append(f'<div class="progress">{entry}</div>')
            elif entry.startswith("保存至:") or entry.startswith("  保存至:"):
                html_parts.append(f'<div class="path">{entry}</div>')
            elif "====" in entry or "----" in entry:
                html_parts.append(f'<div class="separator"></div>')
            else:
                html_parts.append(f'<div>{entry}</div>')
        html_parts.append('</body></html>')
        return "\n".join(html_parts)

    def _download_with_live_log(self, links, mode):
        """下载链接并实时累积显示日志弹窗"""
        try:
            from java import jclass, dynamic_proxy
            from java.lang import Runnable

            act = self._activity()
            if not act:
                return

            spider_self = self
            total = len(links)

            # 共享状态
            log_entries_ref = [["下载任务启动", "=" * 40]]
            success_ref = [0]
            fail_ref = [0]
            webview_ref = [None]

            Builder = jclass("android.app.AlertDialog$Builder")
            WebView = jclass("android.webkit.WebView")
            LinearLayout = jclass("android.widget.LinearLayout")
            LP = jclass("android.widget.LinearLayout$LayoutParams")

            def refresh_webview():
                """刷新 WebView 内容，并滚动到底部"""
                class RefreshRun(dynamic_proxy(Runnable)):
                    def run(self):
                        if webview_ref[0]:
                            html = spider_self._build_html_log(log_entries_ref[0])
                            webview_ref[0].loadDataWithBaseURL(None, html, "text/html", "utf-8", None)
                            
                            class ScrollBottom(dynamic_proxy(Runnable)):
                                def run(self):
                                    webview_ref[0].evaluateJavascript(
                                        "window.scrollTo(0, document.body.scrollHeight);", None
                                    )
                            webview_ref[0].postDelayed(ScrollBottom(), 100)
                act.getWindow().getDecorView().post(RefreshRun())

            # 第一步：立即在 UI 线程创建并弹窗（显示准备中）
            class CreateLogWindow(dynamic_proxy(Runnable)):
                def run(self):
                    root = LinearLayout(act)
                    root.setOrientation(LinearLayout.VERTICAL)
                    root.setPadding(0, 0, 0, 0)

                    web_view = WebView(act)
                    settings = web_view.getSettings()
                    settings.setJavaScriptEnabled(True)
                    settings.setDomStorageEnabled(True)
                    
                    # 初始显示准备中提示
                    preparing_html = (
                        '<!DOCTYPE html><html><head><meta charset="utf-8">'
                        '<style>body{font-family:monospace;font-size:14px;padding:20px;'
                        'background:#fafafa;color:#333;margin:0;text-align:center;'
                        'display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:200px;}'
                        '.loading{color:#1976D2;font-size:16px;font-weight:bold;}</style>'
                        '</head><body>'
                        f'<div class="loading">⏳ 正在准备下载...</div>'
                        f'<div style="color:#999;margin-top:10px;">共 {total} 个链接</div>'
                        '</body></html>'
                    )
                    web_view.loadDataWithBaseURL(None, preparing_html, "text/html", "utf-8", None)

                    webview_ref[0] = web_view
                    root.addView(web_view, LP(-1, 1200))

                    dialog = Builder(act).setTitle("下载进度").setView(root).setPositiveButton("关闭", None).create()
                    dialog.setCancelable(True)
                    dialog.show()

            # 立即抛到主线程显示弹窗
            act.getWindow().getDecorView().post(CreateLogWindow())

            # 第二步：开启 Python 子线程执行下载，防止卡死 UI 线程
            def worker():
                time.sleep(0.3)  # 给 UI 弹窗渲染预留足够时间
                
                # 初始化日志
                log_entries_ref[0] = ["下载任务启动", "=" * 40]
                refresh_webview()
                
                # 开始循环下载
                for i, item in enumerate(links, 1):
                    if mode == "input_links":
                        url = item
                        name = url[:40] + ("..." if len(url) > 40 else "")
                        filename = f"html_{i}.html"
                    else:
                        name, url = item
                        filename = f"{name}.html"
                    
                    save_path = os.path.join(spider_self.DEFAULT_SAVE_DIR, filename)
                    
                    # 添加"正在下载"日志并即时刷新
                    log_entries_ref[0].append(f"[{i}/{total}] 正在下载: {name}")
                    refresh_webview()
                    
                    # 耗时网络请求（在子线程中运行，不会卡顿 UI）
                    success, msg, path = spider_self._download_single(url, save_path, spider_self.session)
                    
                    # 更新结果日志
                    if success:
                        log_entries_ref[0].append(f"✅ {name}: 成功 ({msg})")
                        log_entries_ref[0].append(f"   保存至: {path}")
                        success_ref[0] += 1
                    else:
                        log_entries_ref[0].append(f"❌ {name}: {msg}")
                        fail_ref[0] += 1
                    
                    log_entries_ref[0].append(f"进度: {i}/{total} | 成功: {success_ref[0]} | 失败: {fail_ref[0]}")
                    log_entries_ref[0].append("-" * 20)
                    
                    # 刷新显示
                    refresh_webview()
                    time.sleep(0.1)
                
                # 最终汇总
                log_entries_ref[0].append("")
                log_entries_ref[0].append("=" * 40)
                log_entries_ref[0].append("下载完成")
                log_entries_ref[0].append(f"总计: {total} | 成功: {success_ref[0]} | 失败: {fail_ref[0]}")
                refresh_webview()

            # 启动线程
            threading.Thread(target=worker, daemon=True).start()

        except Exception as e:
            try:
                from java import jclass, dynamic_proxy
                from java.lang import Runnable
                act = self._activity()
                if act:
                    Builder = jclass("android.app.AlertDialog$Builder")
                    class ShowError(dynamic_proxy(Runnable)):
                        def run(self):
                            Builder(act).setTitle("错误").setMessage(str(e)).setPositiveButton("确定", None).show()
                    act.getWindow().getDecorView().post(ShowError())
            except:
                pass


    # ====================== 通用 UI 工具 ======================
    
    def _run_on_ui(self, ui_builder_fn):
        try:
            from java import jclass, dynamic_proxy
            from java.lang import Runnable

            act = self._activity()
            if not act:
                return

            Builder = jclass("android.app.AlertDialog$Builder")
            EditText = jclass("android.widget.EditText")
            TextView = jclass("android.widget.TextView")
            LinearLayout = jclass("android.widget.LinearLayout")
            LP = jclass("android.widget.LinearLayout$LayoutParams")
            InputType = jclass("android.text.InputType")
            DialogClick = jclass("android.content.DialogInterface$OnClickListener")
            Toast = jclass("android.widget.Toast")

            class Run(dynamic_proxy(Runnable)):
                def run(self):
                    ui_builder_fn(act, Builder, EditText, TextView, LinearLayout, LP, InputType, Click, Toast)

            class Click(dynamic_proxy(DialogClick)):
                def __init__(self, fn):
                    super().__init__()
                    self.fn = fn

                def onClick(self, dialog, which):
                    if self.fn:
                        self.fn()

            act.getWindow().getDecorView().post(Run())
        except Exception as e:
            pass

    def _activity(self):
        try:
            from java import jclass
            JClass = jclass("java.lang.Class")
            AT = JClass.forName("android.app.ActivityThread")
            cur = AT.getMethod("currentActivityThread").invoke(None)
            f = AT.getDeclaredField("mActivities")
            f.setAccessible(True)
            for r in f.get(cur).values().toArray():
                rc = r.getClass()
                pf = rc.getDeclaredField("paused")
                pf.setAccessible(True)
                if not pf.getBoolean(r):
                    af = rc.getDeclaredField("activity")
                    af.setAccessible(True)
                    return af.get(r)
        except Exception:
            pass
        return None

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass
