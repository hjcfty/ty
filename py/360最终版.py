# -*- coding: utf-8 -*-
"""
360影视 - AppleCMS/羊壳 Python Spider 源（纯片单版）
数据接口：api.web.360kan.com（列表/详情）
用法说明：本源只做片单展示（分类筛选/详情），不承担搜索与播放；
      点击影片后请在播放器（OK影视/蜂蜜影视等 TVBox 系壳子）内"换源"，
      由壳内其他已配置影视源按片名接管播放。
说明：360kan 无直链播放，playlinksdetail.default_url 为外站播放页（爱奇艺/腾讯等），
      本源附带该链接仅供线路展示与换源参考。
"""
import json
import re
import ssl
import time
import requests
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "360影视"

    def init(self, extend=""):
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.headers = {
            "User-Agent": self.ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Referer": "https://www.360kan.com/",
        }
        self.session = requests.Session()
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
        except Exception:
            pass
        self.api_list = "https://api.web.360kan.com/v1/filter/list"
        self.api_detail = "https://api.web.360kan.com/v1/detail"
        # 频道映射：catid -> 名称
        self.cat_names = {
            "1": "电影",
            "2": "电视剧",
            "3": "综艺",
            "4": "动漫",
        }
        # 平台站点 -> 中文名
        self.site_names = {
            "qiyi": "爱奇艺",
            "qq": "腾讯视频",
            "youku": "优酷",
            "imgo": "芒果TV",
            "sohu": "搜狐",
            "bilibili1": "哔哩哔哩",
            "douyin": "抖音",
            "xigua": "西瓜视频",
            "m1905": "1905电影网",
            "cntv": "央视网",
            "renren": "人人视频",
            "leshi": "乐视",
            "levp": "乐视",
            "huanxi": "欢喜首映",
            "pptv": "聚力视频",
        }
        # 年份列表（电影/电视剧/动漫共用；动漫接口 year 无效故不上该维度）
        years = []
        for y in range(2026, 2006, -1):
            years.append({"n": str(y), "v": str(y)})
        years.append({"n": "更早", "v": "lt_year"})
        self.year_options = years

        self.classes = [
            {"type_id": "1", "type_name": "电影"},
            {"type_id": "2", "type_name": "电视剧"},
            {"type_id": "3", "type_name": "综艺"},
            {"type_id": "4", "type_name": "动漫"},
        ]
        self.filters = {
            "1": [
                {"key": "cat", "name": "题材", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "喜剧", "v": "喜剧"}, {"n": "爱情", "v": "爱情"},
                    {"n": "动作", "v": "动作"}, {"n": "恐怖", "v": "恐怖"},
                    {"n": "科幻", "v": "科幻"}, {"n": "剧情", "v": "剧情"},
                    {"n": "犯罪", "v": "犯罪"}, {"n": "奇幻", "v": "奇幻"},
                    {"n": "战争", "v": "战争"}, {"n": "悬疑", "v": "悬疑"},
                    {"n": "动画", "v": "动画"}, {"n": "文艺", "v": "文艺"},
                    {"n": "纪录", "v": "纪录"}, {"n": "传记", "v": "传记"},
                    {"n": "歌舞", "v": "歌舞"}, {"n": "古装", "v": "古装"},
                    {"n": "历史", "v": "历史"}, {"n": "惊悚", "v": "惊悚"},
                    {"n": "伦理", "v": "伦理"}, {"n": "其他", "v": "其他"},
                ]},
                {"key": "year", "name": "年份", "value": [{"n": "全部", "v": ""}] + self.year_options},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "内地", "v": "大陆"}, {"n": "中国香港", "v": "香港"},
                    {"n": "中国台湾", "v": "台湾"}, {"n": "泰国", "v": "泰国"},
                    {"n": "美国", "v": "美国"}, {"n": "韩国", "v": "韩国"},
                    {"n": "日本", "v": "日本"}, {"n": "法国", "v": "法国"},
                    {"n": "英国", "v": "英国"}, {"n": "德国", "v": "德国"},
                    {"n": "印度", "v": "印度"}, {"n": "其他", "v": "其他"},
                ]},
                {"key": "act", "name": "明星", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "成龙", "v": "成龙"}, {"n": "周星驰", "v": "周星驰"},
                    {"n": "李连杰", "v": "李连杰"}, {"n": "林正英", "v": "林正英"},
                    {"n": "吴京", "v": "吴京"}, {"n": "徐峥", "v": "徐峥"},
                    {"n": "黄渤", "v": "黄渤"}, {"n": "王宝强", "v": "王宝强"},
                    {"n": "姜文", "v": "姜文"}, {"n": "沈腾", "v": "沈腾"},
                    {"n": "邓超", "v": "邓超"}, {"n": "巩俐", "v": "巩俐"},
                    {"n": "马丽", "v": "马丽"}, {"n": "周冬雨", "v": "周冬雨"},
                    {"n": "汤唯", "v": "汤唯"}, {"n": "舒淇", "v": "舒淇"},
                ]},
                {"key": "rank", "name": "排序", "value": [
                    {"n": "最近热映", "v": "rankhot"},
                    {"n": "最近上映", "v": "ranklatest"},
                    {"n": "最受好评", "v": "rankpoint"},
                ]},
            ],
            "2": [
                {"key": "cat", "name": "题材", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "言情", "v": "言情"}, {"n": "剧情", "v": "剧情"},
                    {"n": "伦理", "v": "伦理"}, {"n": "喜剧", "v": "喜剧"},
                    {"n": "悬疑", "v": "悬疑"}, {"n": "都市", "v": "都市"},
                    {"n": "偶像", "v": "偶像"}, {"n": "古装", "v": "古装"},
                    {"n": "军事", "v": "军事"}, {"n": "警匪", "v": "警匪"},
                    {"n": "历史", "v": "历史"}, {"n": "励志", "v": "励志"},
                    {"n": "神话", "v": "神话"}, {"n": "谍战", "v": "谍战"},
                    {"n": "青春", "v": "青春"}, {"n": "家庭", "v": "家庭"},
                    {"n": "动作", "v": "动作"}, {"n": "情景", "v": "情景"},
                    {"n": "武侠", "v": "武侠"}, {"n": "科幻", "v": "科幻"},
                    {"n": "其他", "v": "其他"},
                ]},
                {"key": "year", "name": "年份", "value": [{"n": "全部", "v": ""}] + self.year_options},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "内地", "v": "内地"}, {"n": "中国香港", "v": "香港"},
                    {"n": "中国台湾", "v": "台湾"}, {"n": "泰国", "v": "泰国"},
                    {"n": "日本", "v": "日本"}, {"n": "韩国", "v": "韩国"},
                    {"n": "美国", "v": "美国"}, {"n": "英国", "v": "英国"},
                    {"n": "新加坡", "v": "新加坡"},
                ]},
                {"key": "act", "name": "明星", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "杨幂", "v": "杨幂"}, {"n": "迪丽热巴", "v": "迪丽热巴"},
                    {"n": "张嘉译", "v": "张嘉译"}, {"n": "赵丽颖", "v": "赵丽颖"},
                    {"n": "胡歌", "v": "胡歌"}, {"n": "孙俪", "v": "孙俪"},
                    {"n": "周迅", "v": "周迅"}, {"n": "陈坤", "v": "陈坤"},
                    {"n": "刘亦菲", "v": "刘亦菲"}, {"n": "唐嫣", "v": "唐嫣"},
                    {"n": "周冬雨", "v": "周冬雨"}, {"n": "任嘉伦", "v": "任嘉伦"},
                    {"n": "杨紫", "v": "杨紫"}, {"n": "李易峰", "v": "李易峰"},
                    {"n": "雷佳音", "v": "雷佳音"},
                ]},
                {"key": "rank", "name": "排序", "value": [
                    {"n": "最近热映", "v": "rankhot"},
                    {"n": "最近上映", "v": "ranklatest"},
                    {"n": "最受好评", "v": "rankpoint"},
                ]},
            ],
            "3": [
                {"key": "cat", "name": "题材", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "脱口秀", "v": "脱口秀"}, {"n": "真人秀", "v": "真人秀"},
                    {"n": "搞笑", "v": "搞笑"}, {"n": "选秀", "v": "选秀"},
                    {"n": "访谈", "v": "访谈"}, {"n": "情感", "v": "情感"},
                    {"n": "生活", "v": "生活"}, {"n": "晚会", "v": "晚会"},
                    {"n": "音乐", "v": "音乐"}, {"n": "美食", "v": "美食"},
                    {"n": "时尚", "v": "时尚"}, {"n": "游戏", "v": "游戏"},
                    {"n": "少儿", "v": "少儿"}, {"n": "体育", "v": "体育"},
                    {"n": "纪实", "v": "纪实"}, {"n": "科教", "v": "科教"},
                    {"n": "曲艺", "v": "曲艺"}, {"n": "歌舞", "v": "歌舞"},
                    {"n": "其他", "v": "其他"},
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "内地", "v": "大陆"}, {"n": "中国香港", "v": "香港"},
                    {"n": "中国台湾", "v": "台湾"}, {"n": "日本", "v": "日本"},
                    {"n": "欧美", "v": "欧美"},
                ]},
                {"key": "act", "name": "明星", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "邓超", "v": "邓超"}, {"n": "陈赫", "v": "陈赫"},
                    {"n": "何炅", "v": "何炅"}, {"n": "汪涵", "v": "汪涵"},
                    {"n": "王俊凯", "v": "王俊凯"}, {"n": "黄磊", "v": "黄磊"},
                    {"n": "谢娜", "v": "谢娜"}, {"n": "黄渤", "v": "黄渤"},
                    {"n": "周杰伦", "v": "周杰伦"}, {"n": "薛之谦", "v": "薛之谦"},
                    {"n": "易烊千玺", "v": "易烊千玺"}, {"n": "沈腾", "v": "沈腾"},
                    {"n": "贾玲", "v": "贾玲"}, {"n": "撒贝宁", "v": "撒贝宁"},
                    {"n": "Angelababy", "v": "Angelababy"},
                ]},
                {"key": "rank", "name": "排序", "value": [
                    {"n": "最近热映", "v": "rankhot"},
                    {"n": "最近上映", "v": "ranklatest"},
                ]},
            ],
            "4": [
                {"key": "cat", "name": "题材", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "热血", "v": "热血"}, {"n": "科幻", "v": "科幻"},
                    {"n": "美少女", "v": "美少女"}, {"n": "魔幻", "v": "魔幻"},
                    {"n": "经典", "v": "经典"}, {"n": "励志", "v": "励志"},
                    {"n": "少儿", "v": "少儿"}, {"n": "冒险", "v": "冒险"},
                    {"n": "搞笑", "v": "搞笑"}, {"n": "推理", "v": "推理"},
                    {"n": "恋爱", "v": "恋爱"}, {"n": "治愈", "v": "治愈"},
                    {"n": "幻想", "v": "幻想"}, {"n": "校园", "v": "校园"},
                    {"n": "机战", "v": "机战"}, {"n": "亲子", "v": "亲子"},
                    {"n": "悬疑", "v": "悬疑"}, {"n": "战争", "v": "战争"},
                    {"n": "青春", "v": "青春"}, {"n": "竞技", "v": "竞技"},
                    {"n": "动作", "v": "动作"}, {"n": "友情", "v": "友情"},
                    {"n": "TV版", "v": "TV版"}, {"n": "新番动画", "v": "新番动画"},
                    {"n": "完结动画", "v": "完结动画"}, {"n": "其他", "v": "其他"},
                ]},
                {"key": "area", "name": "地区", "value": [
                    {"n": "全部", "v": ""},
                    {"n": "内地", "v": "大陆"}, {"n": "日本", "v": "日本"},
                    {"n": "美国", "v": "美国"},
                ]},
                {"key": "rank", "name": "排序", "value": [
                    {"n": "最近热映", "v": "rankhot"},
                    {"n": "最近上映", "v": "ranklatest"},
                ]},
            ],
        }

    def _req_json(self, url, referer=None, timeout=15):
        headers = dict(self.headers)
        if referer:
            headers["Referer"] = referer
        try:
            r = self.session.get(url, headers=headers, timeout=timeout, verify=False)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print("[360kan] req error: " + str(e))
        return None

    def _clean_title(self, title):
        # 去掉括号及内部内容（普通话、粤语、HD、国语版等常见后缀）
        if not title:
            return ""
        t = str(title).strip()
        # 去掉各种括号包裹的后缀：中文括号、英文括号、全角括号
        t = re.sub(r"（[^）]*）", "", t)
        t = re.sub(r"\([^)]*\)", "", t)
        t = re.sub(r"【[^】]*】", "", t)
        t = re.sub(r"\[[^\]]*\]", "", t)
        t = re.sub(r"〔[^〕]*〕", "", t)
        # 去掉常见尾部后缀（保留中英文/数字/空格）
        t = re.sub(r"(HD|BD|高清|超清|蓝光|国语|粤语|普通话|中文字幕|双语|抢先版|TC|TS|DVD|VCD|MP4|mkv|avi)(?![a-zA-Z0-9\u4e00-\u9fff])", "", t, flags=re.I)
        t = re.sub(r"\s{2,}", " ", t)
        return t.strip()

    def _fix_url(self, url):
        if not url:
            return ""
        url = str(url).strip()
        if url.startswith("//"):
            return "https:" + url
        return url

    def _join_list(self, arr):
        if not arr:
            return ""
        if isinstance(arr, (list, tuple)):
            return "/".join(str(x) for x in arr if x)
        return str(arr)

    def _parse_ext(self, ext):
        if not ext:
            return {}
        if isinstance(ext, dict):
            return ext
        if isinstance(ext, str):
            ext = ext.strip()
            if not ext or ext in ("{}", "null", "undefined"):
                return {}
            try:
                return json.loads(ext)
            except Exception:
                result = {}
                for part in ext.split("&"):
                    if "=" in part:
                        k, v = part.split("=", 1)
                        result[k] = v
                return result
        return {}

    def _build_list_url(self, catid, pg, f):
        params = ["pageno=" + str(pg), "size=36", "catid=" + str(catid)]
        rank = f.get("rank", "")
        cat = f.get("cat", "")
        year = f.get("year", "")
        area = f.get("area", "")
        act = f.get("act", "")
        if rank:
            params.append("rank=" + rank)
        if cat:
            params.append("cat=" + self._enc(cat))
        if year and year != "lt_year":
            params.append("year=" + year)
        if area:
            params.append("area=" + self._enc(area))
        if act:
            params.append("act=" + self._enc(act))
        return self.api_list + "?" + "&".join(params)

    def _enc(self, text):
        try:
            from urllib.parse import quote
            return quote(str(text))
        except Exception:
            return str(text)

    def _parse_movies(self, catid, data):
        result = []
        payload = (data or {}).get("data") or {}
        movies = payload.get("movies") or []
        for m in movies:
            if not m or not m.get("id"):
                continue
            pic = self._fix_url(m.get("cdncover") or m.get("cover") or "")
            remarks = ""
            pubdate = m.get("pubdate") or ""
            if pubdate:
                remarks = str(pubdate)[:4] + "年"
            result.append({
                "vod_id": str(catid) + "|" + str(m.get("id")),
                "vod_name": self._clean_title(m.get("title", "")),
                "vod_pic": pic,
                "vod_remarks": remarks,
                "vod_score": str(m.get("doubanscore") or m.get("score") or ""),
                "vod_actor": self._join_list(m.get("actor")),
                "vod_year": str(pubdate)[:4] if pubdate else "",
            })
        return result

    def homeContent(self, filter):
        # 首页推荐：电影频道热门
        url = self._build_list_url("1", 1, {"rank": "rankhot"})
        data = self._req_json(url)
        vods = self._parse_movies("1", data)
        return {
            "class": self.classes,
            "list": vods[:20],
            "filters": self.filters,
        }

    def homeVideoContent(self):
        # 首页最新：四大频道各取最新几条合并
        result = []
        for catid in ("1", "2", "3", "4"):
            url = self._build_list_url(catid, 1, {"rank": "ranklatest"})
            data = self._req_json(url)
            result.extend(self._parse_movies(catid, data))
            if len(result) >= 40:
                break
        return {"list": result[:40]}

    def categoryContent(self, cid, pg, filter, ext):
        pg = int(pg) if str(pg).isdigit() else 1
        cid = str(cid)
        f = self._parse_ext(filter) or self._parse_ext(ext) or {}
        # rank 缺省时给热门排序，保证有内容
        if not f.get("rank"):
            f["rank"] = "rankhot"
        url = self._build_list_url(cid, pg, f)
        data = self._req_json(url)
        vods = self._parse_movies(cid, data)
        total = (((data or {}).get("data") or {}).get("total") or 0) if data else 0
        limit = 36
        pc = max(1, -(-total // limit)) if total else 1
        return {
            "list": vods,
            "page": pg,
            "pagecount": pc,
            "limit": limit,
            "total": total,
        }

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vid = str(ids[0])
        if "|" in vid:
            catid, ent_id = vid.split("|", 1)
        else:
            # 兼容外部传入纯 id（默认按电影处理）
            catid, ent_id = "1", vid
        url = self.api_detail + "?cat=" + catid + "&id=" + self._enc(ent_id)
        data = self._req_json(url)
        if not data or not data.get("data"):
            return {"list": []}
        d = data["data"]
        title = d.get("title", "")
        pic = self._fix_url(d.get("cdncover") or "")
        desc = d.get("description") or ""
        pubdate = d.get("pubdate") or ""
        # 收集平台列表用于备注展示（让用户知道哪些外站有片）
        platform_list = []
        pld = d.get("playlinksdetail") or {}
        for site, info in pld.items():
            if not isinstance(info, dict):
                continue
            default_url = info.get("default_url") or ""
            if default_url:
                platform_list.append(self.site_names.get(site, site))
        if not platform_list:
            for site in (d.get("playlinks") or {}).keys():
                platform_list.append(self.site_names.get(site, site))
        # 本源为纯片单展示源，不返回任何播放线路，详情页只展示影片信息
        # 想看片请在壳子内手动"换源"切换到其他已配置影视源
        play_from = ""
        play_url = ""
        vod = {
            "vod_id": vid,
            "vod_name": self._clean_title(title),
            "vod_pic": pic,
            "vod_content": desc,
            "vod_play_from": play_from,
            "vod_play_url": play_url,
            "vod_director": self._join_list(d.get("director")),
            "vod_actor": self._join_list(d.get("actor")),
            "vod_area": self._join_list(d.get("area")),
            "vod_year": str(pubdate)[:4] if pubdate else "",
            "vod_score": str(d.get("doubanscore") or ""),
            "vod_remarks": "/".join(platform_list) if platform_list else "",
            "type_name": self.cat_names.get(catid, ""),
        }
        return {"list": [vod]}

    def searchContent(self, key, quick, pg="1"):
        # 本源为纯片单源，不提供搜索：搜索由壳内其他已配置影视源接管
        return {"page": 1, "pagecount": 1, "limit": 0, "total": 0, "list": []}

    def playerContent(self, flag, id, vipFlags):
        # 返回空地址，壳子播放器初始化瞬间报错，零等待触发自动换源
        return {
            "parse": 0,
            "url": "",
            "header": "",
        }