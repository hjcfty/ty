# -*- coding: utf-8 -*-
# 开心影院 kxyytv.com —— TVBox/FongMi base.spider 采集源
# 站点形态：仿 MacCMS v10 伪静态站（vodshow/voddetail/vodplay）
# 播放直链：vodplay 页顶层 player_data.url 字段（m3u8）
# 分类：tid=1电影/2电视剧/3综艺/4动漫/26短剧/24纪录片
import re, json, time, ssl
from base.spider import Spider
import requests

try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass


class Spider(Spider):
    _cached_host = None          # 固定域名，缓存仅作防御（类属性跨实例共享）
    _cached_time = 0

    def getName(self):
        return "开心影院"

    def init(self, extend=""):
        self.ua = ("Mozilla/5.0 (Linux; Android 16; 2510DRK44C Build/BP2A.250605.031.A3) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/143.0.7499.192 Mobile Safari/537.36")
        self.host = "https://www.kxyytv.com/"
        self.headers = {
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": self.host,
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # 分类：tid=1电影/2电视剧/3综艺/4动漫/26短剧/24纪录片
        self.classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "4", "type_name": "动漫"},
            {"type_id": "26", "type_name": "短剧"},
            {"type_id": "24", "type_name": "纪录片"},
        ]
        # 筛选：排序/类型/地区（URL 模板均已实测）
        common_sort = [
            {"key": "by", "name": "排序",
             "value": [{"n": "更新时间", "v": "time"},
                       {"n": "近期热门", "v": "hits_week"},
                       {"n": "豆瓣评分", "v": "douban_score"}]},
        ]
        # 类型筛选（各分类通用，来自站点筛选面板）
        common_cls = [
            {"key": "cls", "name": "类型",
             "value": [{"n": "全部", "v": ""},
                       {"n": "动作", "v": "动作"}, {"n": "剧情", "v": "剧情"},
                       {"n": "科幻", "v": "科幻"}, {"n": "爱情", "v": "爱情"},
                       {"n": "喜剧", "v": "喜剧"}, {"n": "悬疑", "v": "悬疑"},
                       {"n": "惊悚", "v": "惊悚"}, {"n": "犯罪", "v": "犯罪"},
                       {"n": "冒险", "v": "冒险"}, {"n": "古装", "v": "古装"},
                       {"n": "历史", "v": "历史"}, {"n": "战争", "v": "战争"},
                       {"n": "奇幻", "v": "奇幻"}, {"n": "家庭", "v": "家庭"},
                       {"n": "青春", "v": "青春"}, {"n": "动画", "v": "动画"},
                       {"n": "综艺", "v": "综艺"}, {"n": "纪录", "v": "纪录"}]},
        ]
        common_area = [
            {"key": "area", "name": "地区",
             "value": [{"n": "全部", "v": ""},
                       {"n": "中国大陆", "v": "中国大陆"}, {"n": "中国香港", "v": "中国香港"},
                       {"n": "中国台湾", "v": "中国台湾"}, {"n": "美国", "v": "美国"},
                       {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"},
                       {"n": "泰国", "v": "泰国"}, {"n": "英国", "v": "英国"},
                       {"n": "法国", "v": "法国"}, {"n": "德国", "v": "德国"},
                       {"n": "意大利", "v": "意大利"}, {"n": "印度", "v": "印度"}]},
        ]
        filters = {}
        for c in self.classes:
            filters[c["type_id"]] = common_sort + common_cls + common_area
        self.filters = filters

    # ============ 基础请求 ============
    def _req(self, url):
        try:
            r = self.session.get(url, timeout=15, verify=False)
            if r.status_code == 200:
                return r.text
        except Exception:
            pass
        return ""

    def _clean(self, s):
        return re.sub(r"<[^>]+>", "", s or "").replace("&nbsp;", " ").strip()

    def homeContent(self, filter):
        return {"class": self.classes, "filters": self.filters, "list": []}

    def homeVideoContent(self):
        """首页推荐：轮播（src 直出）+ 各栏目 lozad 卡（data-src 懒加载）"""
        html = self._req(self.host)
        items = []
        seen = set()
        # 轮播卡：<a href="/voddetail/xx.html" class="carousel-item..."><img src=... alt=...>
        for href, img in re.findall(r'<a[^>]+href="(/voddetail/\d+\.html)"[^>]*>(.*?)</a>', html, re.S):
            if len(img) > 600 or "carousel" not in img and "card-img-top" not in img:
                continue
            m = re.search(r'<img[^>]*?(?:data-src|src)="([^"]+)"[^>]*>', img)
            title = (re.search(r'alt="([^"]*)"', img) or re.search(r'<h3[^>]*>([^<]+)</h3>', img))
            if not m:
                continue
            name = title.group(1).strip() if title else ""
            if not name or href in seen:
                continue
            seen.add(href)
            items.append({"vod_id": href, "vod_name": name, "vod_pic": m.group(1),
                          "vod_remarks": ""})
            if len(items) >= 40:
                break
        return {"list": items}

    def categoryContent(self, cid, pg, filter, ext):
        pg = int(pg) if str(pg).isdigit() else 1
        by = ""
        area = ""
        cls = ""
        # TVBox/FongMi 框架：filter 是 bool，筛选条件在 ext（dict）里
        ext_dict = ext if isinstance(ext, dict) else {}
        for k, v in ext_dict.items():
            if k == "by" and v:
                by = v
            elif k == "area" and v:
                area = v
            elif k == "cls" and v:
                cls = v
        # 构造 vodshow URL（实测站点分页模板，横线位置按字段前缀不同）：
        #   无筛选     {cid}--------{pg}---.html（8 横线）
        #   类型       {cid}---{cls}-----{pg}---.html（cls 后 5 横线）
        #   排序       {cid}--{by}------{pg}---.html（by 后 6 横线）
        #   地区       {cid}-{area}-------{pg}---.html（area 后 7 横线）
        #   类型+排序  {cid}--{by}-{cls}-----{pg}---.html（by后1横+cls后5横）
        #   地区+排序  {cid}-{area}-{by}------{pg}---.html
        #   地区+类型  {cid}-{area}-{cls}------{pg}---.html
        if cls and by:
            url = f"{self.host}vodshow/{cid}--{by}-{cls}-----{pg}---.html"
        elif cls and area:
            url = f"{self.host}vodshow/{cid}-{area}-{cls}------{pg}---.html"
        elif cls:
            url = f"{self.host}vodshow/{cid}---{cls}-----{pg}---.html"
        elif by and area:
            url = f"{self.host}vodshow/{cid}-{area}-{by}------{pg}---.html"
        elif by:
            url = f"{self.host}vodshow/{cid}--{by}------{pg}---.html"
        elif area:
            url = f"{self.host}vodshow/{cid}-{area}-------{pg}---.html"
        else:
            url = f"{self.host}vodshow/{cid}--------{pg}---.html"
        html = self._req(url)
        items = []
        # 列表卡：<a href=/voddetail/xx.html class="...cover2"><img src=...><span class="badge...">备注</span></a>
        #         <h3 class="...card-title...">标题</h3><p class="text-muted">日期</p>
        for href, body in re.findall(r'<a[^>]+href="(/voddetail/\d+\.html)"[^>]*>(.*?)</a>', html, re.S):
            if "cover2" not in body and "card-img-top" not in body:
                continue
            m = re.search(r'<img[^>]*?(?:data-src|src)="([^"]+)"[^>]*>', body)
            badge = re.search(r'<span[^>]*class="[^"]*badge[^"]*"[^>]*>([^<]+)</span>', body)
            if not m:
                continue
            items.append({"vod_id": href, "vod_name": "", "vod_pic": m.group(1),
                          "vod_remarks": self._clean(badge.group(1)) if badge else ""})
        # 补标题：同一列表 HTML 中 card-body 的 h3 紧随其后
        if items:
            bodies = re.findall(r'<div class="card-body p-2">.*?</div>', html, re.S)
            for i, vod in enumerate(items):
                if i < len(bodies):
                    t = re.search(r'<h3[^>]*>([^<]+)</h3>', bodies[i])
                    if t:
                        vod["vod_name"] = t.group(1).strip()
        # 分页：page-link 链接里提取最大页码（兼容 {cid}--------{pg} / {cid}---{cls}-----{pg} 等模板）
        pages = []
        for m in re.finditer(r'page-link" href="/vodshow/[^"]*?--(\d+)---\.html"', html):
            pages.append(int(m.group(1)))
        maxpg = max(pages) if pages else pg
        return {"list": items, "page": pg, "pagecount": max(99 if len(items) == 0 else maxpg, pg),
                "limit": 24, "total": maxpg * 24}

    def detailContent(self, ids):
        raw_id = ids[0] if ids else ""
        if raw_id.startswith("http"):
            url = raw_id
        else:
            url = self.host + raw_id.lstrip("/")
        html = self._req(url)
        vod = {"vod_id": raw_id, "vod_name": "", "vod_pic": "",
               "vod_actor": "", "vod_director": "", "vod_content": "",
               "vod_year": "", "vod_area": "", "vod_type": "",
               "vod_remarks": "", "vod_play_from": "", "vod_play_url": ""}
        if not html:
            return {"list": [vod]}
        # 标题：h1 "片名 (2026)"
        h1 = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        if h1:
            name = h1.group(1).strip()
            m_year = re.search(r"\((20\d{2})\)", name)
            if m_year:
                vod["vod_name"] = name[:name.rfind("(")].strip()
                vod["vod_year"] = m_year.group(1)
            else:
                vod["vod_name"] = name
        # 封面 og:image
        og = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if og:
            vod["vod_pic"] = og.group(1)
        # 简介 og:description
        desc = re.search(r'<meta property="og:description" content="([^"]*)"', html)
        if desc:
            vod["vod_content"] = desc.group(1)
        # 导演/主演/类型：<strong>导演：</strong><a...>xxx</a>
        cast = {"导演": "vod_director", "主演": "vod_actor", "类型": "vod_type"}
        for label, field in cast.items():
            for m in re.finditer(re.escape(label) + r"：</strong>(.*?)</p>", html, re.S):
                names = re.findall(r"<a[^>]*>([^<]+)</a>", m.group(1))
                if names:
                    vod[field] = ",".join(x.strip() for x in names if x.strip())
                break
        # 地区/语言（详情信息内联文本）
        area = re.search(r"地区[：:]\s*</strong>\s*([^<]{1,20})", html)
        if not area:
            area = re.search(r">([中国大陆香港台湾美国日本韩国泰国英国法国德国意大利印度][^<]{0,12})<", html)
        if area:
            vod["vod_area"] = area.group(1).strip()
        # ===== 播放区：tab 导航线路名 + tab-pane 集数按钮 =====
        # 线路名：<li class="nav-item"><a href="#tabs-home-5" ...>YX源 &nbsp;</a></li>
        tab_maps = {}   # id -> 线路名
        for tid, name in re.findall(r'<a href="#(tabs-home-\d+)"[^>]*>(.*?)</a>', html, re.S):
            nm = self._clean(name)
            if nm:
                tab_maps[tid] = nm
        # 集数：<div class="tab-pane ..." id="tabs-home-5"> <a class="btn..." href="/vodplay/xx-5-1.html">1080P</a>
        pane_eps = {}   # id -> [(href, epname)]
        for pid, body in re.findall(r'<div class="tab-pane[^"]*" id="(tabs-home-\d+)">(.*?)</div>\s*</div>', html, re.S):
            eps = re.findall(r'<a[^>]*href="(/vodplay/[^"]+)"[^>]*>([^<]+)</a>', body)
            if eps:
                pane_eps[pid] = [(h, self._clean(n)) for h, n in eps]
        play_from, play_url = [], []
        for pid, from_name in tab_maps.items():
            eps = pane_eps.get(pid, [])
            if not eps:
                continue
            play_from.append(from_name)
            play_url.append("#".join(f"{n}${self.host + h.lstrip('/')}" for h, n in eps))
        vod["vod_play_from"] = "$$$".join(play_from)
        vod["vod_play_url"] = "$$$".join(play_url)
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        # /index.php/ajax/suggest?mid=1&wd={key}&limit=30 返回 JSON（忽略 page，一次尽量多取）
        url = f"{self.host}index.php/ajax/suggest?mid=1&wd={requests.utils.quote(str(key))}&limit=30"
        html = self._req(url)
        items = []
        try:
            data = json.loads(html)
            for it in (data.get("list") or []):
                nid = it.get("id")
                name = it.get("name") or ""
                pic = it.get("pic") or ""
                if not nid or not name:
                    continue
                items.append({"vod_id": f"/voddetail/{nid}.html", "vod_name": name,
                              "vod_pic": pic, "vod_remarks": ""})
        except Exception:
            pass
        return {"list": items, "page": 1, "pagecount": 1, "limit": 30, "total": len(items)}

    def playerContent(self, flag, id, vipFlags):
        if not id.startswith("http"):
            id = self.host + id.lstrip("/")
        html = self._req(id)
        headers = {"User-Agent": self.ua, "Referer": self.host, "Origin": self.host.rstrip("/")}
        # player_data JSON：顶层 url 字段即 m3u8 直链
        m = re.search(r"player_data\s*=\s*(\{.*?\})\s*;?\s*(?:</script>|$)", html, re.S)
        if m:
            try:
                pd = json.loads(m.group(1))
                url = (pd.get("url") or "").strip()
                if url and url.startswith("http"):
                    return {"parse": 0, "url": url, "header": headers}
            except Exception:
                pass
            # JSON 解析失败时直接抓 url 字段
            u = re.search(r'"url"\s*:\s*"([^"]+)"', m.group(1))
            if u and u.group(1).startswith("http"):
                return {"parse": 0, "url": u.group(1), "header": headers}
        # 未解析到直链：交壳端嗅探
        return {"parse": 1, "url": id, "header": headers}

    def isVideoFormat(self, url):
        if not url:
            return False
        return bool(re.search(r"\.(m3u8|mp4|m4v|ts|flv)(\?|$)", str(url), re.I))

    def localProxy(self, param):
        return [404, "text/plain", "", ""]

    def destroy(self):
        if hasattr(self, "session"):
            try:
                self.session.close()
            except Exception:
                pass