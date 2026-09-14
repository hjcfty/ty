# -*- coding: utf-8 -*-
"""
金帝影视 (jdmv.net) —— 自动注册 / 自动登录版
自研 Nuxt SPA + apibase.01233.xyz/api

【破解要点 2026-09-14 实测】
  ① 注册接口 POST /auth/register {phone, password} —— ★ 不要短信验证码！
  ② 登录 POST /auth/login-password {phone, password} → data.token.access_token
  ③ 播放 POST /parse {url, from} 带 Authorization: Bearer <token> → data.url 真实 m3u8
  ④ 账号字段 child_daily_limit=40（每日 40 次）

【ext 填法】
  写法 A：手机号,密码          （用你自己的号，最稳）
  写法 B：{"phone":"...","password":"...","host":"..."}
  留空：★ 源自动注册一个随机号，存到本地文件，下次复用

【账号持久化】
  存到 SPIDER_ROOT（壳端 workdir）下的 jdmv_account.json
"""
import json
import os
import re
import time
import random
import string
import requests
from base.spider import Spider


class Spider(Spider):

    LINE_NAME = {
        "co": "智能线路1",
        "qq": "智能线路2",
        "iqiyi": "智能线路3",
        "youku": "智能线路4",
        "bilibili": "智能线路5",
    }

    ACC_FILE = "jdmv_account.json"

    def getName(self):
        return "金帝影视"

    # ================= 初始化 =================
    def init(self, extend=""):
        self.name = "金帝影视"
        self.host = "https://www.jdmv.net"
        self.api = "https://apibase.01233.xyz/api"
        self.phone = ""
        self.password = ""
        self.token = ""
        self._cats = None
        self._relogin_tried = False
        self._acc_path = self._acc_file_path()

        # ---------- 解析 ext ----------
        raw = extend if isinstance(extend, str) else (json.dumps(extend) if extend else "")
        raw = (raw or "").strip()
        if raw.startswith("{"):
            try:
                cfg = json.loads(raw)
                self.phone = str(cfg.get("phone") or cfg.get("user") or "").strip()
                self.password = str(cfg.get("password") or cfg.get("pass") or cfg.get("pwd") or "").strip()
                h = str(cfg.get("host") or "").strip()
                if h.startswith("http"):
                    self.host = h.rstrip("/")
            except Exception:
                pass
        elif "," in raw:
            a, _, b = raw.partition(",")
            self.phone, self.password = a.strip(), b.strip()
        elif raw.startswith("http"):
            self.host = raw.rstrip("/")

        # ---------- session ----------
        self.device_id = self._new_device_id()
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Referer": self.host + "/",
            "Accept": "application/json, text/plain, */*",
            "X-Device-Type": "mobile",
            "X-Device-ID": self.device_id,
            "X-Device-Name": "Android",
            "X-Device-Model": "Chrome",
        }
        self.session.headers.update(self.headers)

        # ---------- 账号：ext 为空时读本地存档 ----------
        if not self.phone:
            acc = self._load_account()
            if acc:
                self.phone = acc.get("phone", "")
                self.password = acc.get("password", "")

        # ---------- 登录（失败则自动注册）----------
        if self.phone and self.password:
            if not self._login():
                # 存档的号失效 → 清掉重注册
                if not (raw.startswith("{") or "," in raw):
                    self._clear_account()
                    self.phone = self.password = ""
        if not self.phone:
            self._auto_register()

    # ================= 账号存取 =================
    def _acc_file_path(self):
        cands = []
        env = os.environ.get("SPIDER_ROOT")
        if env:
            cands.append(env)
        cands += ["/sdcard/Download", "/storage/emulated/0/Download", os.getcwd(), "/tmp"]
        for d in cands:
            try:
                if d and os.path.isdir(d):
                    return os.path.join(d, self.ACC_FILE)
            except Exception:
                continue
        return self.ACC_FILE

    def _load_account(self):
        try:
            if os.path.exists(self._acc_path):
                with open(self._acc_path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                if isinstance(d, dict) and d.get("phone"):
                    return d
        except Exception:
            pass
        return {}

    def _save_account(self, phone, password):
        try:
            with open(self._acc_path, "w", encoding="utf-8") as f:
                json.dump({"phone": phone, "password": password,
                           "ts": int(time.time())}, f, ensure_ascii=False)
            return True
        except Exception:
            return False

    def _clear_account(self):
        try:
            if os.path.exists(self._acc_path):
                os.remove(self._acc_path)
        except Exception:
            pass

    # ================= 设备 =================
    @staticmethod
    def _new_device_id():
        r = "".join(random.choice(string.ascii_lowercase + string.digits) for _ in range(14))
        return "web_" + r + format(int(time.time()), "x")

    @staticmethod
    def _rand_phone():
        # 1 开头 11 位；用不常见的号段，降低撞号概率
        seg = random.choice(["355", "356", "357", "358", "359", "370", "371", "372",
                             "373", "374", "375", "376", "377", "378", "379"])
        return "1" + seg + "".join(random.choice(string.digits) for _ in range(7))

    @staticmethod
    def _rand_pwd():
        return "Ab" + "".join(random.choice(string.ascii_letters + string.digits) for _ in range(12))

    # ================= 注册 / 登录 =================
    def _auto_register(self):
        """自动注册：随机手机号 + 随机密码，成功即存本地"""
        for i in range(3):
            phone = self._rand_phone()
            pwd = self._rand_pwd()
            try:
                # 每次换设备 ID，降低「操作过于频繁」概率
                self.device_id = self._new_device_id()
                self.headers["X-Device-ID"] = self.device_id
                self.session.headers.update({"X-Device-ID": self.device_id})
                r = self.session.post(self.api + "/auth/register",
                                      json={"phone": phone, "password": pwd, "nickname": "u" + phone[-4:]},
                                      headers=self.headers, timeout=(8, 18), verify=False)
                d = r.json()
                code = d.get("code")
                if code == 0:
                    self.phone, self.password = phone, pwd
                    self._save_account(phone, pwd)
                    tk = ((d.get("data") or {}).get("token") or {}).get("access_token")
                    if tk:
                        self.token = str(tk).strip()
                        self.session.headers.update({"Authorization": "Bearer " + self.token})
                        return True
                    return self._login()
                msg = str(d.get("message") or "")
                if "过于频繁" in msg or "频繁" in msg:
                    time.sleep(2 + i * 3)
                    continue
                if "已注册" in msg:
                    continue
            except Exception:
                time.sleep(1.5 + i * 2)
        return False

    def _login(self):
        try:
            r = self.session.post(self.api + "/auth/login-password",
                                  json={"phone": self.phone, "password": self.password},
                                  headers=self.headers, timeout=(8, 18), verify=False)
            d = r.json()
            if d.get("code") != 0:
                return False
            tk = ((d.get("data") or {}).get("token") or {}).get("access_token") or ""
            self.token = str(tk).strip()
            if self.token:
                self.session.headers.update({"Authorization": "Bearer " + self.token})
                return True
        except Exception:
            pass
        return False

    def _relogin(self):
        """token 失效 → 重登一次（失败则重注册）"""
        if self._relogin_tried:
            return False
        self._relogin_tried = True
        self.token = ""
        try:
            self.session.headers.pop("Authorization", None)
        except Exception:
            pass
        if self.phone and self.password and self._login():
            return True
        # 存档号废了 → 清掉重注册
        self._clear_account()
        self.phone = self.password = ""
        return self._auto_register()

    # ================= 请求 =================
    def _auth_headers(self):
        h = dict(self.headers)
        if self.token:
            h["Authorization"] = "Bearer " + self.token
        return h

    def _get(self, path, params=None, retry=True):
        for _ in range(2):
            try:
                r = self.session.get(self.api + path, params=params or {},
                                     headers=self._auth_headers(), timeout=(6, 14), verify=False)
                if r.status_code != 200:
                    continue
                d = r.json()
                if d.get("code") == 40110 and retry and self._relogin():
                    return self._get(path, params, retry=False)
                if d.get("code") == 0:
                    return d.get("data") or {}
                return {}
            except Exception:
                continue
        return {}

    def _post(self, path, body, retry=True):
        try:
            r = self.session.post(self.api + path, json=body,
                                  headers=self._auth_headers(), timeout=(8, 22), verify=False)
            d = r.json()
            if d.get("code") == 40110 and retry and self._relogin():
                return self._post(path, body, retry=False)
            return d
        except Exception:
            return {}

    # ================= 工具 =================
    def _fix(self, url):
        url = str(url or "").strip().replace("\\/", "/")
        if not url:
            return ""
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("http"):
            return url
        if url.startswith("/"):
            return self.host + url
        return self.host + "/" + url

    def _clean(self, s):
        return str(s or "").replace("#", " ").replace("$", " ").strip()

    def _item(self, v):
        remark = str(v.get("vod_remarks") or "").strip()
        if remark and re.search(r"(广告|推广|加群|下载)", remark):
            remark = ""
        sub = str(v.get("vod_sub") or "").strip()
        if not remark and sub:
            remark = self._clean(sub)[:18]
        return {
            "vod_id": str(v.get("vod_id") or ""),
            "vod_name": str(v.get("vod_name") or "").strip(),
            "vod_pic": self._fix(v.get("vod_pic") or ""),
            "vod_remarks": remark,
        }

    # ================= 分类 =================
    def _categories(self):
        if self._cats is not None:
            return self._cats
        data = self._get("/categories")
        rows = data if isinstance(data, list) else []
        cats = []
        for c in rows:
            if not isinstance(c, dict):
                continue
            try:
                if int(c.get("type_pid") or 0) != 0:
                    continue
            except Exception:
                pass
            name = str(c.get("type_name") or "").strip()
            tid = str(c.get("type_id") or "").strip()
            if name and tid:
                cats.append({"type_id": tid, "type_name": name})
        self._cats = cats
        return cats

    def homeContent(self, filter):
        classes = [dict(c) for c in self._categories()]
        filters = {}
        opts = [{"n": "全部", "v": ""}]
        for c in classes:
            filters[c["type_id"]] = [{"key": "sort", "name": "排序", "value": opts}]
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        data = self._get("/videos", {"page": 1, "limit": 36})
        rows = data.get("list") or [] if isinstance(data, dict) else []
        return {"list": [self._item(v) for v in rows]}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        params = {"page": pg, "limit": 24}
        tid = str(tid or "").strip()
        if tid.isdigit() and int(tid) > 0:
            params["t"] = tid
        data = self._get("/videos", params)
        if not isinstance(data, dict):
            data = {}
        rows = data.get("list") or []
        try:
            total = int(data.get("total") or 0)
        except Exception:
            total = 0
        try:
            limit = int(data.get("page_size") or 24) or 24
        except Exception:
            limit = 24
        pagecount = (total + limit - 1) // limit if total > 0 else pg
        return {"page": pg, "pagecount": pagecount, "limit": limit, "total": total,
                "list": [self._item(v) for v in rows]}

    # ================= 详情 =================
    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) and ids else ids
        vid = str(vid or "").strip()
        if not vid:
            return {"list": []}
        d = self._get("/videos/" + vid)
        if not isinstance(d, dict) or not d:
            return {"list": []}

        play_from, play_url = [], []

        plist = d.get("play_list")
        if isinstance(plist, list):
            for line in plist:
                if not isinstance(line, dict):
                    continue
                frm = str(line.get("from") or "").strip()
                eps = line.get("episodes")
                if not frm or not isinstance(eps, list) or not eps:
                    continue
                items = []
                for i, ep in enumerate(eps):
                    if not isinstance(ep, dict):
                        continue
                    u = str(ep.get("url") or "").strip()
                    if not u:
                        continue
                    nm = self._clean(ep.get("name")) or ("第%d集" % (i + 1))
                    if nm.isdigit():
                        nm = "第%s集" % nm
                    items.append(nm + "$" + u)
                if items:
                    play_from.append(self.LINE_NAME.get(frm, frm))
                    play_url.append("#".join(items))

        if not play_from:
            fraw = str(d.get("vod_play_from") or "")
            uraw = str(d.get("vod_play_url") or "")
            if fraw and uraw:
                fs, us = fraw.split("$$$"), uraw.split("$$$")
                for i, f in enumerate(fs):
                    if i >= len(us) or not us[i].strip():
                        continue
                    items = []
                    for seg in us[i].split("#"):
                        if "$" not in seg:
                            continue
                        nm, _, u = seg.partition("$")
                        items.append((self._clean(nm) or "正片") + "$" + u.strip())
                    if items:
                        play_from.append(self.LINE_NAME.get(f.strip(), f.strip()))
                        play_url.append("#".join(items))

        content = re.sub(r"<[^>]+>", "", str(d.get("vod_content") or "")).strip()
        tag = str(d.get("vod_class") or d.get("vod_tag") or "").strip()
        vod = {
            "vod_id": vid,
            "vod_name": str(d.get("vod_name") or ""),
            "vod_pic": self._fix(d.get("vod_pic") or ""),
            "vod_content": content,
            "vod_remarks": tag or str(d.get("vod_remarks") or ""),
            "vod_year": str(d.get("vod_year") or ""),
            "vod_area": str(d.get("vod_area") or ""),
            "vod_play_from": "$$$".join(play_from),
            "vod_play_url": "$$$".join(play_url),
        }
        return {"list": [vod]}

    # ================= 搜索 =================
    def searchContent(self, key, quick, pg="1"):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if pg < 1:
            pg = 1
        kw = str(key or "").strip()
        if not kw:
            return {"page": pg, "pagecount": pg, "limit": 20, "total": 0, "list": []}
        data = self._get("/search", {"wd": kw, "page": pg})
        if not isinstance(data, dict):
            data = {}
        rows = data.get("list") or []
        try:
            total = int(data.get("total") or 0)
        except Exception:
            total = 0
        try:
            limit = int(data.get("page_size") or 20) or 20
        except Exception:
            limit = 20
        pagecount = (total + limit - 1) // limit if total > 0 else pg
        return {"page": pg, "pagecount": pagecount, "limit": limit, "total": total,
                "list": [self._item(v) for v in rows]}

    def searchContentPage(self, key, quick, page):
        return self.searchContent(key, quick, page)

    # ================= 播放 =================
    def playerContent(self, flag, id, vipFlags=None):
        raw = str(id or "").strip()
        if not raw:
            return {"parse": 1, "playUrl": "", "url": "", "header": ""}
        hdr = json.dumps(self._auth_headers())

        if raw.startswith("http://") or raw.startswith("https://"):
            return {"parse": 0, "url": raw, "playUrl": raw, "header": hdr}

        frm = raw.split("_")[0] if "_" in raw else ""

        # 账号还没拿到 → 现注册一次
        if not self.token:
            if not self._relogin():
                return {"parse": 1, "playUrl": "", "url": "", "header": hdr}
            hdr = json.dumps(self._auth_headers())

        d = self._post("/parse", {"url": raw, "from": frm})
        if d.get("code") == 0 and isinstance(d.get("data"), dict):
            dd = d["data"]
            u = str(dd.get("url") or "").strip()
            if u:
                if self.isVideoFormat(u):
                    return {"parse": 0, "url": u, "playUrl": u, "header": hdr}
                if dd.get("player_type") == 1:
                    return {"parse": 0, "url": u, "playUrl": u, "header": hdr}
                return {"parse": 1, "playUrl": u, "url": u, "header": hdr}
        return {"parse": 1, "playUrl": "", "url": "", "header": hdr}

    def isVideoFormat(self, url):
        u = str(url or "").lower()
        return any(f in u for f in (".m3u8", ".mp4", ".flv", ".ts"))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        try:
            d = json.loads(param) if isinstance(param, str) else dict(param or {})
            url = str(d.get("url") or "")
            if not url.startswith("http"):
                return [404, "text/plain", b""]
            r = self.session.get(url, headers={
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/"}, timeout=(6, 18), verify=False)
            if r.status_code != 200:
                return [404, "text/plain", b""]
            ct = r.headers.get("Content-Type") or "application/octet-stream"
            return [200, ct, r.content]
        except Exception:
            return [404, "text/plain", b""]

    def destroy(self):
        try:
            self.session.close()
        except Exception:
            pass
