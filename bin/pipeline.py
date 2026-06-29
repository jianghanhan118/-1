#!/usr/bin/env python3
# 昆仑洞天 v6 - bin/pipeline.py
# Phase 3: 感知管线补全 + 三元深度化 + Phase 4 三层世界模型自动化

import sys, os, json, argparse, sqlite3, uuid, threading

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORKSPACE)

# 弹药箱信息总线 — 跨模块信息流转强制通道
from 弹药箱.ammo_box import put as ammo_put

from diting import build_factcrystal, build_staging_factcrystal
from taiyi.operators import run_all_operators
from taiyi.model_synthesizer import ModelSynthesizer
from taiyi.selfcheck import check_cognitive_cube
from tiangong.render import render_report
from tiangong.quality import QualityChecker, compute_quality_score, persist_quality


# ═══════ 三层优先级(全局默认值,运行时可由 _detect_missing_bridges 动态覆盖)═══════
_LAYER_PRIORITY = {
    "value": {"Q08","Q09","Q10","Q11"},
    "cognitive": {"Q05","Q06","Q07"},
    "physical": {"Q01","Q02","Q03","Q04"},
}

# ═══════ 工具函数 ═══════

def _auto_search_fill(query: str) -> list[dict]:
    """
    谛听搜索--L0内部三渠道 → L1-L4外部渠道(通过镇熵统一调度)

    【权限打值集成 v1.0】
    每次搜索前先过镇岳权限检查,拒绝超阈值的信源。

    L0: FTS5/图谱/归藏(实时可用 + 权限检查)
    L1-L4: orchestrator.orchestrate() → xiaoyi/tavily/金融/baidu/bing
    """
    # ── L0: 权限检查 ──
    from zhenshang.permission_scorer import IntegratedPermissionManager
    pm = IntegratedPermissionManager(governor=None)
    pm_init_ok = True
    try:
        pm.scorer.register_default_sources()
    except Exception:
        pm_init_ok = False

    # ── L0: 内部渠道 ──
    conn = None
    internal_results = []
    try:
        conn = sqlite3.connect(f'{WORKSPACE}/kunlun.db')
        # 权限检查
        if pm_init_ok:
            allowed, detail = pm.allow_internal()
            if not allowed:
                print(f"    [镇岳] 内部知识库权限受限: {detail['total']}分")
            else:
                from zhenshang.orchestrator import UnifiedSearch
                us = UnifiedSearch(conn)
                results = us.search(query, max_results=30)
                if results:
                    internal_results = results
                    internal_count = sum(1 for r in results if r.get('source') in ('fts5','knowledge_graph','guicang_memory'))
                    if internal_count > 0:
                        print(f"    [谛听·内部] FTS5/图谱/归藏 → {internal_count} 条匹配")
                    external_count = len(results) - internal_count
                    if external_count > 0:
                        print(f"    [谛听·外部] Web搜索 → {external_count} 条结果")
        else:
            from zhenshang.orchestrator import UnifiedSearch
            us = UnifiedSearch(conn)
            results = us.search(query, max_results=30)
            internal_results = results
    except Exception:
        pass

    # ── v7.1增强: 集成EnhancedSearchRouter (L1/L2/L3/L4) ──
    try:
        from diting.enhanced_search import EnhancedSearchRouter
        er = EnhancedSearchRouter(conn)
        enhanced_results = er.search(query, max_results=30, enable_oppose=True)
        if enhanced_results:
            seen_keys = set()
            for r in enhanced_results:
                key = r.get("card_id") or r.get("title", "")[:60]
                if key not in seen_keys:
                    seen_keys.add(key)
                    internal_results.append(r)
    except Exception:
        pass
    
    # ── 来源诊断：排查到底什么源回来了 ──
    try:
        from collections import Counter
        diag = Counter(r.get("source","unknown") for r in internal_results)
        src_str = " · ".join(f"{s}={c}" for s,c in sorted(diag.items(), key=lambda x:-x[1]))
        print(f"    [谛听] 源分布: {src_str} 共{len(internal_results)}条")
    except Exception:
        pass
    
    # ── L1-L4: 多引擎并发搜索 ──
    if pm_init_ok and len([r for r in internal_results if r.get('source') not in ('fts5','fts','knowledge_graph','guicang_memory')]) < 5:
        try:
            import threading
            external_all = []
            external_lock = threading.Lock()

            def _search_thread(source_name: str, search_fn, allowed_check: bool = True):
                if allowed_check and pm_init_ok:
                    allowed, _ = pm.allow_search(source_name)
                    if not allowed:
                        return
                try:
                    r = search_fn()
                    if r:
                        with external_lock:
                            external_all.extend(r)
                except Exception:
                    pass

            threads = []

            # 引擎注册表: 补充orchestrator的source_registry未覆盖的源
            # source_registry已覆盖: xiaoyi, tavily, alphaear, sina7x24, ima, ifind, web_fetch
            # 补充: baidu(独立key)
            engine_registry = [
                ("baidu-search", lambda q=query: _baidu_search(q)),
                # 🆕 华为小艺搜索——华为云AI搜索，零额外配置
                ("xiaoyi-search", lambda q=query: _xiaoyi_web_search(q)),
                # 🆕 零Key聚合搜索(3引擎)——360+搜狗微信+Bing
                ("zero-key-search", lambda q=query: _zero_key_search(q)),
                # 🆕 微博热搜——实时热点舆情，零Key
                ("weibo-hot", lambda q=query: _weibo_hot_search(q)),
                # 🆕 36氪快讯——科技商业第一手资讯，零Key
                ("36kr-news", lambda q=query: _36kr_news_search(q)),
                # 🆕 arXiv论文——学术前沿，零Key
                ("arxiv-papers", lambda q=query: _arxiv_search(q)),
                # 🆕 多引擎聚合——web_fetch爬百度+360，零Key兜底
                ("multi-engine", lambda q=query: _multi_engine_search(q)),
            ]

            for name, fn in engine_registry:
                t = threading.Thread(target=_search_thread, args=(name, fn))
                t.start()
                threads.append(t)

            for t in threads:
                t.join(timeout=20)

            # 合并去重
            seen_titles = set()
            for r in internal_results:
                seen_titles.add(r.get("title", "")[:60])
            for r in external_all:
                key = r.get("title", "")[:60]
                if key and key not in seen_titles:
                    internal_results.append(r)
                    seen_titles.add(key)

            if external_all:
                print(f"    [谛听·并发] 多引擎搜索 → +{len(external_all)} 条结果")
            # 来源汇总:始终打印,展示多源融合实况
            try:
                from collections import Counter
                all_sources = Counter(r.get("source", "unknown") for r in internal_results)
                src_line = "    [谛听·来源] " + " · ".join(
                    f"{src}={cnt}" for src, cnt in sorted(all_sources.items(), key=lambda x:-x[1]))
                print(src_line)
            except Exception:
                pass
        except Exception:
            pass

    try:
        if conn: conn.close()
    except Exception:
        pass

    # 降阶兜底
    if not internal_results or len(internal_results) < 3:
        try:
            from diting.external_search_adapter import search_with_webfetch
            fallback = search_with_webfetch(query, max_results=8)
            if fallback:
                return fallback
        except Exception:
            pass

    return internal_results[:80]


def _tavily_search(query: str, max_results: int = 8) -> list[dict]:
    """Tavily搜索封装"""
    import urllib.request as _ur
    key = __import__('os').environ.get("TAVILY_API_KEY", "")
    if not key:
        import os as _os2
        tavily_env = _os2.path.expanduser("~/.openclaw/workspace/skills/tavily/.env")
        if _os2.path.isfile(tavily_env):
            with open(tavily_env) as _ef:
                for _line in _ef:
                    _line = _line.strip()
                    if _line.startswith("TAVILY_API_KEY"):
                        _parts = _line.split("=", 1)
                        if len(_parts) == 2:
                            key = _parts[1].strip().strip("'").strip('"')
                            break
    if not key:
        return []
    try:
        req = _ur.Request("https://api.tavily.com/search",
            data=json.dumps({"query": query, "max_results": max_results}).encode(),
            headers={"Content-Type":"application/json", "Authorization": f"Bearer {key}"})
        resp = _ur.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        items = data.get("results", [])
        return [{"title": r.get("title",""), "content": r.get("content","")[:500],
                 "source": "tavily", "url": r.get("url",""), "relevance": 0.95}
                for r in items[:max_results]]
    except Exception:
        return []


def _baidu_search(query: str, max_results: int = 5) -> list[dict]:
    """百度搜索封装"""
    import urllib.request as _ur
    key = __import__('os').environ.get("BAIDU_API_KEY", "")
    if not key:
        import os as _os2
        baidu_env = _os2.path.expanduser("~/.openclaw/workspace/skills/baidu-search/.env")
        if _os2.path.isfile(baidu_env):
            with open(baidu_env) as _ef:
                for _line in _ef:
                    _line = _line.strip()
                    if _line.startswith("BAIDU_API_KEY"):
                        _parts = _line.split("=", 1)
                        if len(_parts) == 2:
                            key = _parts[1].strip().strip("'").strip('"')
                            break
    if not key:
        return []
    try:
        req = _ur.Request("https://qianfan.baidubce.com/v2/ai_search/web_search",
            data=json.dumps({"query": query, "count": max_results}).encode(),
            headers={"Content-Type":"application/json", "Authorization": f"Bearer {key}"})
        resp = _ur.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        refs = data.get("references", [])
        return [{"title": r.get("title",""), "content": r.get("content","")[:500],
                 "source": "baidu", "url": r.get("url",""), "relevance": 0.9}
                for r in refs[:max_results]]
    except Exception:
        return []


def _bing_search(query: str, max_results: int = 8) -> list[dict]:
    """Bing搜索封装"""
    try:
        from diting.external_search_adapter import search_with_webfetch
        return search_with_webfetch(query, max_results)
    except Exception:
        return []


def _web_fetch_search(query: str, max_results: int = 3) -> list[dict]:
    """兜底web_fetch"""
    try:
        from urllib.parse import quote
        from urllib.request import Request, urlopen
        url = f"https://cn.bing.com/search?q={quote(query)}&format=nonjs"
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urlopen(req, timeout=8)
        html = resp.read().decode('utf-8', errors='ignore')
        import re
        results = []
        for m in re.finditer(r'<li class="b_algo"[^>]*>(.*?)</li>', html, re.S | re.I):
            block = m.group(1)
            title_m = re.search(r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', block, re.S)
            if not title_m: continue
            url_text = title_m.group(1)
            title = re.sub(r'<[^>]+>', '', title_m.group(2)).strip()
            snippet_m = re.search(r'<p[^>]*>(.*?)</p>', block, re.S)
            snippet = re.sub(r'<[^>]+>', '', snippet_m.group(1)).strip() if snippet_m else ''
            title = re.sub(r'\s+', ' ', title).strip()
            snippet = re.sub(r'\s+', ' ', snippet).strip()
            if title and len(title) > 5:
                results.append({"title": title[:100], "content": snippet[:500],
                    "url": url_text[:200], "source": "bing", "relevance": 0.7})
            if len(results) >= max_results: break
        return results
    except Exception:
        return []


def _xiaoyi_web_search(query: str, max_results: int = 8) -> list[dict]:
    """小艺联网搜索(华为云API)--中文搜索主力,补Tavily中文短板"""
    import os, subprocess, json
    try:
        xiaoyi_script = os.path.expanduser(
            "~/.openclaw/workspace/skills/xiaoyi-web-search/scripts/search.js")
        if not os.path.isfile(xiaoyi_script):
            return []
        result = subprocess.run(
            ["node", xiaoyi_script, query, "-n", str(max_results)],
            capture_output=True, text=True, timeout=15, cwd=os.path.dirname(xiaoyi_script))
        out = result.stdout
        # 解析输出:找每个 result block
        items = []
        for block in out.split("\n---\n"):
            title = ""
            url = ""
            content = ""
            source = ""
            for line in block.split("\n"):
                if line.startswith("📌"):
                    title = line.split(". ", 1)[-1] if ". " in line else line[3:]
                elif line.startswith("🔗"):
                    url = line[2:].strip()
                elif line.startswith("📝"):
                    content = line[3:].strip()
                elif line.startswith("🏷️"):
                    source = line[3:].strip()
            if title:
                items.append({"title": title[:100], "content": content[:500],
                    "url": url[:200], "source": "xiaoyi", "site": source, "relevance": 0.85})
        return items[:max_results]
    except Exception:
        return []


def _zero_key_search(query: str, max_results: int = 8) -> list[dict]:
    """零Key聚合搜索——多引擎并行，无需任何API Key
    引擎: 360(最优) + 搜狗微信(公众号) + Bing CN(碰运气)
    (不含: 搜狗web反爬、百度验证码、头条JS渲染、DDG包bug、Yandex空结果)
    """
    import urllib.request
    from urllib.parse import quote
    import re
    import threading

    all_results = []
    lock = threading.Lock()

    def _scrape_raw(name: str, url_template: str, headers: dict,
                    html_filter, timeout_s=8):
        try:
            url = url_template.format(q=quote(query))
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=timeout_s)
            html = resp.read().decode('utf-8', errors='ignore')

            parsed = html_filter(html)
            if parsed:
                with lock:
                    for p in parsed[:max_results]:
                        all_results.append({
                            "title": p["title"][:120],
                            "content": p.get("content", "")[:500],
                            "source": f"zk-{name}",
                            "url": p.get("url", "")[:200],
                            "relevance": 0.7
                        })
        except Exception:
            pass

    threads = []

    # ───── 1. 360搜索（最稳定，带摘要）─────
    def _parse_360(html):
        items = []
        for m in re.finditer(
            r'<h3[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL):
            title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            title = re.sub(r'\s+', ' ', title)
            if len(title) > 5 and '其他人还搜了' not in title:
                items.append({"title": title, "url": m.group(1)})
        snippets = re.findall(r'<p class="res-desc[^"]*"[^>]*>(.*?)</p>', html, re.DOTALL)
        for i, s in enumerate(snippets):
            if i < len(items):
                items[i]["content"] = re.sub(r'<[^>]+>', '', s).strip()[:300]
        return items

    t = threading.Thread(target=_scrape_raw,
        args=("360", "https://www.so.com/s?q={q}",
              {"User-Agent": "Mozilla/5.0"}, _parse_360))
    threads.append(t); t.start()

    # ───── 2. 搜狗微信（公众号文章，独特内容源）─────
    def _parse_wxsogou(html):
        items = []
        for m in re.finditer(
            r'<h3[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL):
            title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
            title = re.sub(r'\s+', ' ', title)
            if len(title) > 5:
                url = m.group(1)
                if url.startswith('/'):
                    url = 'https://wx.sogou.com' + url
                items.append({"title": title, "url": url})
        return items

    t = threading.Thread(target=_scrape_raw,
        args=("wxsogou", "https://wx.sogou.com/weixin?type=2&query={q}",
              {"User-Agent": "Mozilla/5.0"}, _parse_wxsogou))
    threads.append(t); t.start()

    # ───── 3. Bing CN（碰运气，容器IP只返回导航站，偶尔有好结果）─────
    def _parse_bing(html):
        items = []
        for block in re.finditer(
            r'<li class="b_algo"[^>]*>(.*?)</li>', html, re.DOTALL):
            blk = block.group(1)
            a_m = re.search(r'<a[^>]*href="(https?://[^"]+)"[^>]*>(.*?)</a>',
                            blk, re.DOTALL)
            if not a_m:
                continue
            title = re.sub(r'<[^>]+>', '', a_m.group(2)).strip()
            title = re.sub(r'\s+', ' ', title)
            url = a_m.group(1)
            ul = url.lower()
            if (len(title) > 3
                and not any(x in ul for x in ['bing','microsoft','msn','live.com'])
                and not any(x in title[:40] for x in ['www.','http','baidu.com'])):
                item = {"title": title, "url": url, "content": ""}
                p_m = re.search(r'<p[^>]*>(.*?)</p>', blk, re.DOTALL)
                if p_m:
                    item["content"] = re.sub(r'<[^>]+>', '', p_m.group(1)).strip()[:300]
                items.append(item)
        return items

    t = threading.Thread(target=_scrape_raw,
        args=("bing", "https://cn.bing.com/search?q={q}&ensearch=0",
              {"User-Agent": "Mozilla/5.0"}, _parse_bing, 6))
    threads.append(t); t.start()

    for t in threads:
        t.join(timeout=10)

    # 去重
    seen = set()
    deduped = []
    for r in all_results:
        key = r["title"][:40]
        if key and key not in seen:
            seen.add(key)
            deduped.append(r)

    from collections import Counter
    dist = dict(Counter(r["source"] for r in deduped))
    print(f"    [零Key搜索] {len(deduped)}条 ({len(all_results)}原始) {dist}")
    return deduped[:max_results * 2]


def _weibo_hot_search(query: str = None, max_results: int = 10) -> list[dict]:
    """微博热搜——实时热点舆情，零Key
    query为None时取全局热搜，否则搜索关键词
    """
    import urllib.request, json, re
    try:
        url = 'https://weibo.com/ajax/side/hotSearch'
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://weibo.com/'})
        resp = urllib.request.urlopen(req, timeout=6)
        d = json.loads(resp.read())
        items = d.get('data', {}).get('realtime', [])
        results = []
        for item in items[:max_results]:
            word = item.get('word', item.get('title', ''))
            hot = item.get('raw_hot', 0)
            cat = item.get('category', '')
            # 构造热搜详情内容
            content = f"热搜 #{cat} 热度:{hot}" if hot else f"热搜 #{cat}"
            if word:
                results.append({
                    "title": word[:120],
                    "content": content[:500],
                    "source": "weibo-hot",
                    "url": f"https://s.weibo.com/weibo?q={word}",
                    "relevance": 0.8
                })
        if results:
            print(f"    [微博热搜] {len(results)}条")
        return results[:max_results]
    except Exception:
        return []


def _36kr_news_search(query: str = None, max_results: int = 5) -> list[dict]:
    """36氪快讯——科技商业第一手资讯，零Key"""
    import urllib.request, json
    try:
        url = 'https://36kr.com/api/newsflash?per_page=' + str(max_results)
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})
        resp = urllib.request.urlopen(req, timeout=6)
        d = json.loads(resp.read())
        items = d.get('data', {}).get('items', [])
        results = []
        for item in items[:max_results]:
            title = item.get('title', '')
            summary = item.get('summary', '') or item.get('content', '')
            # 去HTML标签
            import re
            summary = re.sub(r'<[^>]+>', '', summary).strip()[:200]
            if title:
                results.append({
                    "title": title[:120],
                    "content": summary[:500],
                    "source": "36kr",
                    "url": item.get('url', '') or f"https://36kr.com/newsflash/{item.get('id','')}",
                    "relevance": 0.8
                })
        if results:
            print(f"    [36氪快讯] {len(results)}条")
        return results[:max_results]
    except Exception:
        return []


def _arxiv_search(query: str, max_results: int = 5) -> list[dict]:
    """arXiv论文搜索——学术前沿，零Key（走HTTP端口）"""
    import urllib.request, xml.etree.ElementTree as ET
    from urllib.parse import quote
    try:
        url = f'http://export.arxiv.org/api/query?search_query=all:{quote(query)}&start=0&max_results={max_results}&sortBy=relevance'
        req = urllib.request.Request(url, headers={'User-Agent': 'RuntuBot/1.0'})
        resp = urllib.request.urlopen(req, timeout=10)
        ns = {'a': 'http://www.w3.org/2005/Atom'}
        root = ET.fromstring(resp.read())
        entries = root.findall('a:entry', ns)
        results = []
        for e in entries[:max_results]:
            title = e.find('a:title', ns).text.replace('\n', ' ').strip()
            summary = e.find('a:summary', ns).text.replace('\n', ' ').strip()[:300] if e.find('a:summary', ns) is not None else ''
            url = e.find('a:id', ns).text.strip() if e.find('a:id', ns) is not None else ''
            authors = []
            for auth in e.findall('a:author', ns):
                name = auth.find('a:name', ns)
                if name is not None:
                    authors.append(name.text)
            published = e.find('a:published', ns).text[:10] if e.find('a:published', ns) is not None else ''
            content = f"{published} | {'; '.join(authors[:3])} | {summary}" if authors else f"{published} | {summary}"
            if title:
                results.append({
                    "title": title[:120],
                    "content": content[:500],
                    "source": "arxiv",
                    "url": url[:200],
                    "relevance": 0.85
                })
        if results:
            print(f"    [arXiv论文] {len(results)}条")
        return results[:max_results]
    except Exception:
        return []


def _multi_engine_search(query: str, max_results: int = 4) -> list[dict]:
    """多引擎聚合——web_fetch爬百度+360，零Key，中文补位
    (保留为降级兜底，主力由 _zero_key_search 承担)
    """
    import urllib.request
    from urllib.parse import quote
    import re

    results = []
    seen_urls = set()

    # 360搜索
    try:
        url = f"https://www.so.com/s?q={quote(query)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        resp = urllib.request.urlopen(req, timeout=6)
        html = resp.read().decode('utf-8', errors='ignore')
        items_360 = re.findall(
            r'<h3[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?</h3>', html, re.DOTALL)
        for u, t in items_360[:max_results]:
            title = re.sub(r'<[^>]+>', '', t).strip()
            if title and len(title) > 5 and u not in seen_urls:
                seen_urls.add(u)
                results.append({"title": title[:100], "content": "",
                               "source": "multi-360", "url": u, "relevance": 0.65})
    except Exception:
        pass

    # 去重
    uniq = []
    seen_t = set()
    for r in results:
        k = r["title"]
        if k not in seen_t:
            seen_t.add(k)
            uniq.append(r)
    return uniq[:max_results * 2]


def _mark_blinds(conn, query: str, blinds: list[str], is_staging: bool):
    if not conn or not blinds: return 0
    count = 0
    for b in blinds[:3]:
        cid = f"BLIND-{abs(hash(f'{query}{b}'))%100000:05d}"
        try:
            conn.execute("INSERT OR IGNORE INTO knowledge_cards(card_id,bridge_id,card_type,title,content) VALUES(?,?,?,?,?)",
                         (cid, "Q04", "LC", f"盲点: {query[:40]}", f"query={query}\nblind_spot={b[:200]}\nstage={'staging' if is_staging else 'active'}"))
            if conn.total_changes > 0: count += 1
        except Exception: pass
    if count: conn.commit()
    return count


def _load_cards(conn) -> dict:
    """从凤口批量加载知识卡(替代直查 DB)"""
    cards = {"tools": [], "axioms": [], "learning": []}
    if not conn: return cards
    try:
        from bin.fengkou import get_all_cards_by_type
        loaded = get_all_cards_by_type(conn, ['AX', 'TC', 'SC'])
        for ax in loaded.get('axioms', []):
            cards['axioms'].append({"card_id": ax['card_id'], "title": ax['title'], "content": ax['content']})
        for tc in loaded.get('tools', []):
            cards['tools'].append({"card_id": tc['card_id'], "title": tc['title'], "content": tc['content'], "function": tc['content']})
        for sc in loaded.get('learning', []):
            cards['learning'].append({"card_id": sc['card_id'], "title": sc['title'], "content": sc['content'], "proposition": sc['content']})
    except Exception:
        # 兜底:直查
        for row in conn.execute("SELECT card_id,card_type,title,content FROM knowledge_cards WHERE card_type IN ('AX','TC','SC')").fetchall():
            entry = {"card_id": row[0], "title": row[2], "content": row[3] or ""}
            if row[1] == "AX": cards["axioms"].append(entry)
            elif row[1] == "TC":
                entry["function"] = entry["content"]; cards["tools"].append(entry)
            elif row[1] == "SC":
                entry["proposition"] = entry["content"]; cards["learning"].append(entry)
    return cards


def _get_layer_for_bridge(conn, bridge_id: str) -> str:
    """从凤口获取桥的三元世界模型归属"""
    try:
        from bin.fengkou import get_layer_for_bridge as fk_get_layer
        return fk_get_layer(conn, bridge_id)
    except Exception:
        if not conn: return 'physical'
        row = conn.execute("SELECT world_model FROM bridge_profiles WHERE bridge_id=?", (bridge_id,)).fetchone()
        return row[0] if row else 'physical'


def _compute_bridge_coverage(cube: dict) -> dict:
    """计算桥覆盖率--含每桥的 stance/reason(从事实晶体提取)"""
    assertions = cube.get("assertions", [])
    activated = cube.get("bridges", {}).get("activated",
        set(a.get("bridge","") for a in assertions if a.get("bridge")))
    opposing = cube.get("bridges", {}).get("opposing", [])

    # 从凤口动态获取三层桥分组
    try:
        from bin.fengkou import _conn, list_bridges
        conn = _conn()
        bridges = list_bridges(conn)
        layer_map = {"physical": set(), "cognitive": set(), "value": set()}
        bridge_names = {}
        for b in bridges:
            wm = b.get('world_model', 'physical')
            if wm in layer_map:
                layer_map[wm].add(b['bridge_id'])
            bridge_names[b['bridge_id']] = b.get('name', b['bridge_id'])
        conn.close()
    except Exception:
        layer_map = {"physical": {"Q01","Q02","Q03","Q04"}, "cognitive": {"Q05","Q06","Q07","Q12"}, "value": {"Q08","Q09","Q10","Q11","Q13"}}
        bridge_names = {}

    # 构造每桥的 stance 和 reason
    coverage = {}
    for b in activated:
        # 从断言汇总 stance
        related = [a for a in assertions if a.get("bridge") == b]
        stances = [a.get("stance", "0") for a in related]
        pos = stances.count("+1"); neg = stances.count("-1")
        if pos > neg: stance = "+1"
        elif neg > pos: stance = "-1"
        else: stance = "0"
        # 收集推理理由
        reasons = [a.get("text","")[:40] for a in related[:2] if a.get("text")]
        coverage[b] = {
            "stance": stance,
            "reason": "; ".join(reasons) if reasons else "无断言",
            "assertion_count": len(related),
        }

    # 层统计
    layer_counts = {"physical": 0, "cognitive": 0, "value": 0}
    for b in activated:
        for layer, bridges in layer_map.items():
            if b in bridges:
                layer_counts[layer] += 1
                break

    coverage["_meta"] = {
        "total": len(activated),
        **layer_counts,
        "bridge_names": bridge_names,
        "opposing_bridges": opposing,
    }
    return coverage


def _detect_layer_tension(assertions: list[dict], coverage: dict) -> list[dict]:
    tensions = []
    physical_bridges = _LAYER_PRIORITY.get("physical", {"Q01","Q02","Q03","Q04"})
    phys = [a for a in assertions if a.get("bridge") in physical_bridges]
    val = [a for a in assertions if a.get("bridge") in {"Q08","Q09","Q10","Q11"}]
    for pa in phys:
        for va in val:
            ps, vs = pa.get("stance","0"), va.get("stance","0")
            if ps != "0" and vs != "0" and ps != vs:
                tensions.append({
                    "bridge_a": pa.get("bridge","?"),
                    "bridge_b": va.get("bridge","?"),
                    "stance_a": ps,
                    "stance_b": vs,
                    "type": "layer_tension",
                    "description": f"物理层[{pa.get('bridge')}]={ps} vs 价值层[{va.get('bridge')}]={vs}",
                    "severity": 0.6,
                    "mitigation": "需交叉验证物理事实与价值判断的权重分配",
                })
    return tensions


def _compute_spatial_expression(cube: dict, coverage: dict, tensions: list[dict]) -> dict:
    assertions = cube.get("assertions", [])
    stances = {"+1":0,"0":0,"-1":0}
    for a in assertions:
        s = a.get("stance","0")
        if s in stances: stances[s] += 1
    pw = cube.get("model",{}).get("protracted_war",{}).get("primary",{})
    return {
        "dimensions": {
            "距距": len(assertions),
            "立场": stances,
            "趋势": pw.get("phase_label","未判定"),
            "关系": len(cube.get("model",{}).get("disagreements",[])),
            "因果": len(cube.get("model",{}).get("protracted_war",{}).get("interventions",[])),
            "桥覆盖": coverage,
        },
        "layer_distribution": coverage,
        "layer_tensions": len(tensions),
        "ternary_balance": stances,
        "world_model": {
            "physical":{"assertions":len([a for a in assertions if a.get("bridge","") in _LAYER_PRIORITY.get("physical",set())])},
            "cognitive":{"assertions":len([a for a in assertions if a.get("bridge","") in _LAYER_PRIORITY.get("cognitive",set())])},
            "value":{"assertions":len([a for a in assertions if a.get("bridge","") in _LAYER_PRIORITY.get("value",set())])},
        }
    }


# ═══════ Phase A: FC缺桥自动检测 ═══════

_RESONANCE_CACHE = None  # [(from_bridge, to_bridge, direction), ...]
_BRIDGE_PROFILE_CACHE = None  # {bridge_id: {name, entity_types}}


def _detect_missing_bridges(conn, activated_bridges: set, max_probes: int = 3) -> dict:
    """Phase A+C: 检测缺失桥并生成探针查询·三层优先推理"""
    # C-1: 价值层(Q08-Q11)优先→认知层(Q05-Q07)→物理层(Q01-Q04)
    if not conn:
        return {"missing": [], "probes": [], "bridge_states": {}}

    global _RESONANCE_CACHE, _BRIDGE_PROFILE_CACHE

    # 加载共振图
    if _RESONANCE_CACHE is None:
        _RESONANCE_CACHE = conn.execute(
            "SELECT from_bridge, to_bridge, direction FROM bridge_resonance WHERE direction='+1'"
        ).fetchall()
    # 加载桥profile
    if _BRIDGE_PROFILE_CACHE is None:
        rows = conn.execute(
            "SELECT bridge_id, name, entity_types FROM bridge_profiles"
        ).fetchall()
        _BRIDGE_PROFILE_CACHE = {}
        for r in rows:
            try:
                et = json.loads(r[2]) if isinstance(r[2], str) else (r[2] or [])
            except:
                et = []
            _BRIDGE_PROFILE_CACHE[r[0]] = {"name": r[1], "entity_types": et}

    all_bridges = set(_BRIDGE_PROFILE_CACHE.keys())  # Q01~Q13

    # 找出激活桥的共振桥
    resonant_bridges = set()
    for fb, tb, _ in _RESONANCE_CACHE:
        if fb in activated_bridges:
            resonant_bridges.add(tb)
        if tb in activated_bridges:
            resonant_bridges.add(fb)

    missing = resonant_bridges - activated_bridges  # 0态桥
    excluded = all_bridges - activated_bridges - missing  # -1态桥

    # C-1: 三层优先推理 + 探针生成
    # 更新全局 _LAYER_PRIORITY(不创建本地变量,供 _detect_layer_tension 等函数使用)
    global _LAYER_PRIORITY
    try:
        from bin.fengkou import list_bridges
        _LAYER_PRIORITY = {"value": set(), "cognitive": set(), "physical": set()}
        for b in list_bridges(conn):
            wm = b.get('world_model', 'physical')
            if wm in _LAYER_PRIORITY:
                _LAYER_PRIORITY[wm].add(b['bridge_id'])
    except Exception:
        _LAYER_PRIORITY = {"value": {"Q08","Q09","Q10","Q11"}, "cognitive": {"Q05","Q06","Q07"}, "physical": {"Q01","Q02","Q03","Q04"}}

    def _priority_score(bid: str) -> int:
        if bid in _LAYER_PRIORITY["value"]:
            return 3
        if bid in _LAYER_PRIORITY["cognitive"]:
            return 2
        if bid in _LAYER_PRIORITY["physical"]:
            return 1
        return 0

    def _layer_name(bid: str) -> str:
        for name, bridges in _LAYER_PRIORITY.items():
            if bid in bridges:
                return name
        return "unknown"

    probes = []
    for bridge_id in sorted(missing):
        profile = _BRIDGE_PROFILE_CACHE.get(bridge_id, {})
        bridge_name = profile.get("name", f"桥{bridge_id}")
        entity_types = profile.get("entity_types", [])

        keywords = [bridge_name]
        if entity_types:
            keywords.extend(entity_types[:3])
        probe = " · ".join(keywords)

        probes.append({
            "bridge_id": bridge_id,
            "bridge_name": bridge_name,
            "layer": _layer_name(bridge_id),
            "priority": _priority_score(bridge_id),
            "probe_query": probe,
            "reason": f"与{', '.join(sorted(activated_bridges))[:60]}有共振连接",
        })

    # 按优先级排序:价值层优先
    probes.sort(key=lambda p: (-p["priority"], p["bridge_id"]))
    if len(probes) > max_probes:
        probes = probes[:max_probes]

    bridge_states = {}
    for b in all_bridges:
        if b in activated_bridges:
            bridge_states[b] = "+1"
        elif b in missing:
            bridge_states[b] = "0"
        else:
            bridge_states[b] = "-1"

    return {
        "missing": sorted(missing),
        "probes": probes,
        "bridge_states": bridge_states,
        "summary": f"3态检测: +1={len(activated_bridges)}个桥激活, 0={len(missing)}个桥待探查, -1={len(excluded)}个桥无连接",
    }


# ═══════ P3: 物理AI可行性评估 ═══════

def _physical_ai_assessment(fc, cube: dict) -> dict:
    """物理AI分析标准化--物理可行性评估
    当分析涉及Q01(物理)/Q04(系统)/Q05(认知)时,
    自动评估物理AI落地的技术可行性。
    """
    # 统计各桥实体数
    bridge_entity_count = {}
    for e in fc.entities:
        for b in e.discovered_by:
            bid = b[:3]
            bridge_entity_count[bid] = bridge_entity_count.get(bid, 0) + 1

    q01_count = bridge_entity_count.get("Q01", 0)
    q04_count = bridge_entity_count.get("Q04", 0)
    q05_count = bridge_entity_count.get("Q05", 0)
    total = len(fc.entities)

    # 物理可行性分数(0-1):Q01实体占比越高→物理层面越成熟
    physical_ratio = q01_count / max(total, 1)
    system_ratio = q04_count / max(total, 1)
    cognitive_ratio = q05_count / max(total, 1)

    # 三级评估
    if physical_ratio >= 0.3:
        physical_maturity = "高"
        physical_detail = "核心零部件层实体充足,硬件路线清晰"
    elif physical_ratio >= 0.15:
        physical_maturity = "中"
        physical_detail = "部分硬件实体,但层不够深--可能缺传感器/电机/减速器中的某个环节"
    else:
        physical_maturity = "低"
        physical_detail = "物理层实体不足--分析偏软件或政策,缺少硬件基础"

    if system_ratio >= 0.3:
        system_maturity = "高"
    elif system_ratio >= 0.15:
        system_maturity = "中"
    else:
        system_maturity = "低"

    pw = cube.get("model", {}).get("protracted_war", {})
    phase = pw.get("label", "未知")

    # 综合评估
    scores = {"高": 3, "中": 2, "低": 1}
    composite = (scores.get(physical_maturity, 1) + scores.get(system_maturity, 1) + cognitive_ratio * 3) / 3
    overall = "可商用" if composite >= 2.5 else ("试点阶段" if composite >= 1.5 else "概念阶段")

    return {
        "physical_maturity": physical_maturity,
        "system_maturity": system_maturity,
        "physical_ratio": round(physical_ratio, 2),
        "system_ratio": round(system_ratio, 2),
        "cognitive_ratio": round(cognitive_ratio, 2),
        "overall": overall,
        "composite": round(composite, 1),
        "physical_detail": physical_detail,
        "q01_count": q01_count,
        "q04_count": q04_count,
        "q05_count": q05_count,
        "phase": phase,
        "bridges_activated": sorted(bridge_entity_count.keys()),
    }


# ═══════ Phase B: 缺桥自动激活 ═══════

def _execute_probes(probes: list[dict], query: str) -> list[dict]:
    """B-1: 对每个缺桥探针执行搜索"""
    results = []
    for p in probes[:3]:  # 最多3个探针
        try:
            sr = _auto_search_fill(p["probe_query"])
            if sr and len(sr) >= 2:
                # 提取摘要作为中-度证据
                snippet = sr[0].get("content", "")[:200] if sr else ""
                results.append({
                    "bridge_id": p["bridge_id"],
                    "bridge_name": p["bridge_name"],
                    "found": len(sr),
                    "snippet": snippet,
                })
            else:
                results.append({"bridge_id": p["bridge_id"], "bridge_name": p["bridge_name"], "found": 0})
        except Exception:
            results.append({"bridge_id": p["bridge_id"], "bridge_name": p["bridge_name"], "found": -1})
    return results


def _create_missing_assertions(probe_results: list[dict], query: str) -> list[dict]:
    """B-2: 从探针结果生成缺桥断言"""
    assertions = []
    aid = [100]
    for pr in probe_results:
        if pr.get("found", 0) >= 2:
            bridge_id = pr["bridge_id"]
            bridge_name = pr["bridge_name"]
            snippet = pr.get("snippet","")[:40]
            # 生成一个中立断言(stance=0,需要进一步分析才能确定方向)
            assertions.append({
                "id": aid[0],
                "text": f"{bridge_name}与{query[:20]}有结构关联(探针搜索发现)",
                "stance": "0",
                "bridge": bridge_id,
                "evidence_level": 1,
                "counterfactual_branch": None,
                "_probe_generated": True,
                "_probe_snippet": snippet,
            })
            aid[0] += 1
    return assertions


def _generate_sc_cards(conn, probe_results: list[dict]):
    """B-3+K1: 从探针结果生成SC卡--价值层桥自带阶段信号"""
    if not conn:
        return 0
    count = 0

    # K-1: 价值层自动生成带阶段信号的SC卡
    _VALUE_LAYER = {"Q08", "Q09", "Q10", "Q11"}
    _PHASE_TEMPLATES = {
        "defense": ["防御", "下行", "收缩"],
        "stalemate": ["相持", "震荡", "均衡"],
        "offensive": ["反攻", "扩张", "增长"],
    }

    for pr in probe_results:
        if pr.get("found", 0) < 2:
            continue
        bid = pr["bridge_id"]
        bname = pr["bridge_name"]
        snippet = pr.get("snippet", "")[:200]

        if bid in _VALUE_LAYER and snippet:
            # K-1: 为价值层桥分三阶段生成SC卡
            phase_descriptions = {
                "防御": f"{bname}·防御收缩信号:相关领域出现下行压力和收缩趋势。{snippet[:60]}",
                "相持": f"{bname}·相持均衡信号:相关领域进入震荡均衡格局。{snippet[:60]}",
                "反攻": f"{bname}·反攻扩张信号:相关领域出现增长和扩张迹象。{snippet[:60]}",
            }
            for phase, content in phase_descriptions.items():
                cid = f"SC-AUTO-{bid}-{phase}"
                try:
                    conn.execute(
                        "INSERT OR REPLACE INTO knowledge_cards(card_id,bridge_id,card_type,title,content) "
                        "VALUES(?,?,?,?,?)",
                        (cid, bid, "SC", f"自动-{bname}·{phase}阶段", content)
                    )
                    count += 1
                except Exception:
                    pass
        elif snippet:
            # 原有逻辑:非价值层桥用探针摘要
            cid = f"SC-PROBE-{bid}"
            content = f"探针发现: {snippet[:200]}\n数据源: 外部搜索"
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO knowledge_cards(card_id,bridge_id,card_type,title,content) "
                    "VALUES(?,?,?,?,?)",
                    (cid, bid, "SC", f"探针-{bname}·自动生成", content)
                )
                count += 1
            except Exception:
                pass

    if count:
        conn.commit()
    return count


# ═══════ 思维空间可视化 ═══════

def _render_six_dim_chart(spatial: dict, score: dict) -> str:
    """六维认知分布可视化(文本化雷达图)"""
    lines = []
    dims = spatial.get("dimensions", {})
    stances = dims.get("立场", {"+1":0,"0":0,"-1":0})

    lines.append("")
    lines.append("📊 六维认知空间")
    lines.append("")

    # 雷达图(文本化)
    dim_labels = [
        ("距距", dims.get("距距",0), "信息密度", 16),
        ("立场", stances.get("+1",0), "正向立场", 16),
        ("趋势", dims.get("趋势","未判"), "阶段判断", 16),
        ("关系", dims.get("关系",0), "矛盾识别", 16),
        ("因果", dims.get("因果",0), "干预分析", 16),
        ("桥覆盖", dims.get("桥覆盖",{}).get("total",0), "学科广度", 11),
    ]

    # 绘制六维条形图
    max_val = max((v for _, v, _, _ in dim_labels if isinstance(v, (int, float))), default=1)
    for name, value, desc, cap in dim_labels:
        if isinstance(value, (int, float)):
            ratio = min(value / max_val, 1.0)
            bar_len = int(ratio * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"  {name}({value}) {bar} {desc}")
        else:
            lines.append(f"  {name}({value}) 阶段")

    # 三元立场分布可视化
    pos = stances.get("+1",0)
    neg = stances.get("-1",0)
    neu = stances.get("0",0)
    total_stance = max(pos + neg + neu, 1)
    pos_bar = "🟢" * min(pos, 10)
    neg_bar = "🔴" * min(neg, 10)
    neu_bar = "⚪" * min(neu, 10)
    lines.append(f"")
    lines.append(f"  三元立场: {pos_bar}{neu_bar}{neg_bar}")
    lines.append(f"           支持{pos}·中立{neu}·反对{neg}")

    # 三层世界模型
    wm = spatial.get("world_model", {})
    lines.append(f"")
    lines.append(f"  三层世界模型:")
    for layer, info in wm.items():
        count = info.get("assertions", 0)
        bar = "██" * min(count, 10)
        icon = {"physical": "🔬", "cognitive": "🧠", "value": "🌍"}.get(layer, "📦")
        lines.append(f"    {icon} {layer}: {bar} ({count}条断言)")

    # 层间张力
    tensions = spatial.get("layer_tensions", 0)
    if tensions:
        lines.append(f"    ⚠️ 层间张力: {tensions}处")

    lines.append(f"")
    lines.append(f"  📈 分析健康度: {score.get('health',0)}/100 ({score.get('health_label','?')})")
    lines.append(f"  🌐 桥覆盖: {spatial.get('dimensions',{}).get('桥覆盖',{})}")

    return "\n".join(lines)
def _detect_stock_topic(query: str) -> bool:
    """检测查询是否涉及股票/金融主题，需要spawn株株"""
    stock_kw = ["股票", "a股", "大盘", "板块", "行情", "持仓", "金融", "投资",
                "盘前", "盘后", "复盘", "走势", "涨幅", "跌幅", "开盘", "收盘",
                "半导体", "消费电子", "新能源", "医药", "白酒", "涨跌",
                "上证", "深证", "创业板", "科创", "北向", "个股", "荐股",
                "指数", "量化", "选股", "回测"]
    q = query.lower()
    # 中英文混合匹配
    return any(kw in q for kw in stock_kw)


def _detect_agentic_needs(query: str, task_type: str) -> list[dict]:
    """智能体编排检测 — 判断需要spawn哪些子Agent
    
    受埃森哲报告「智能体三层级架构」启发：
    编排层检测任务类型 → 决定调用哪些功能型/超级智能体并行执行。
    """
    spawns = []
    
    # 股票/金融主题 → spawn zhuzhu（不限task_type，只要含股票关键词就触发）
    if _detect_stock_topic(query):
        spawns.append({
            "agent": "zhuzhu",
            "task": f"并行分析股票数据: {query[:150]}",
            "reason": "股票主题检测 → 需zhuzhu的A股技能集",
            "layer": "功能型智能体",
            "mode": "parallel",
        })
    
    # 读书/吸收主题 → spawn book-reader-agent（analysis或general类）
    book_kw = ["读书", "吸收", "精读", "阅读", "书籍", "白皮书", "报告", "看书", "学习"]
    if any(kw in query.lower() for kw in book_kw) and task_type in ("analysis", "general"):
        spawns.append({
            "agent": "book-reader-agent",
            "task": f"精读吸收: {query[:150]}",
            "reason": "读书/吸收检测 → 需book-reader-agent的精读流水线",
            "layer": "功能型智能体",
            "mode": "parallel",
        })
    
    return spawns


def _plan_pipeline(query: str) -> dict:
    """任务规划器 — 将用户目标拆解为子步骤管线
    
    受鸿蒙2030白皮书「自主规划」启发：用户只设目标，系统自主拆解。
    v2新增：智能体编排检测（埃森哲三层级架构）。
    返回结构化的执行计划。
    """
    from collections import OrderedDict
    
    # 查询类型识别
    q_lower = query.lower()
    
    # 分析类关键词
    if any(kw in q_lower for kw in ["分析", "对比", "研究", "review", "总结", "总结", "推荐", "建议"]):
        task_type = "analysis"
    elif any(kw in q_lower for kw in ["搜索", "查", "find", "search", "找"]):
        task_type = "search"
    elif any(kw in q_lower for kw in ["写", "生成", "创作", "create", "write", "generate"]):
        task_type = "generation"
    elif any(kw in q_lower for kw in ["配置", "安装", "设置", "setup", "install", "config"]):
        task_type = "operation"
    else:
        task_type = "general"
    
    # 智能体编排检测
    orchestration = _detect_agentic_needs(query, task_type)
    
    # 步骤模板
    plan_templates = {
        "analysis": [
            ("🔍 搜索", "多源检索相关信息", ["tavily", "fts5", "knowledge_graph"]),
            ("🧠 认知", "构建事实晶体 + 桥共振", ["taiyi", "resonator"]),
            ("📊 分析", "矛盾论推理 + 多维透视", ["taiyi", "operators"]),
            ("📝 报告", "渲染输出 + 质量检查", ["tiangong"]),
        ],
        "search": [
            ("🔍 搜索", "多源检索", ["tavily", "fts5", "cloud_knowledge"]),
            ("📋 整理", "去重排序 + 信度标注", ["taiyi"]),
            ("📝 输出", "格式化结果", ["tiangong"]),
        ],
        "generation": [
            ("🔍 检索", "获取相关素材和参考", ["tavily", "fts5"]),
            ("✍️ 创作", "基于素材生成内容", ["taiyi"]),
            ("✅ 质检", "质量检查 + 真话放大镜", ["tiangong", "verifier"]),
        ],
        "operation": [
            ("🔍 分析", "理解需求和环境", ["tavily", "fts5"]),
            ("🛠️ 执行", "分步操作", ["tools"]),
            ("✅ 验证", "确认结果正确", ["verifier"]),
        ],
        "general": [
            ("🔍 搜索", "多源信息检索", ["tavily", "fts5", "cloud_knowledge"]),
            ("🧠 推理", "认知分析", ["taiyi"]),
            ("📝 输出", "结果呈现", ["tiangong"]),
        ],
    }
    
    plan = {
        "trace_id": str(uuid.uuid4())[:12],
        "task_type": task_type,
        "steps": plan_templates.get(task_type, plan_templates["general"]),
        "est_complexity": "high" if task_type == "analysis" else "medium",
        "parallel_tracks": ["L（左脑逻辑）", "R（右脑直觉）"],
        "orchestration": orchestration,
    }
    
    return plan


def run_pipeline(query, output=None, staging=True, interactive=False):
    plan = _plan_pipeline(query)
    trace_id = plan["trace_id"]
    
    # 输出执行计划
    print(f"\n{'='*60}")
    print(f"  🧩 任务规划 (受鸿蒙2030自主规划启发)")
    print(f"{'='*60}")
    print(f"  目标: {query[:60]}")
    print(f"  类型: {plan['task_type']}")
    print(f"  并行: {' + '.join(plan['parallel_tracks'])}")
    print(f"")
    print(f"  执行步骤:")
    for i, (step_name, step_desc, _) in enumerate(plan['steps'], 1):
        print(f"    {i}. {step_name} — {step_desc}")
    
    # 智能体编排显示（埃森哲三层级架构）
    if plan['orchestration']:
        print(f"")
        print(f"  🏛️ 编排层 (受埃森哲智能体三层级架构启发)")
        for sub in plan['orchestration']:
            print(f"    • spawn {sub['agent']}（{sub['layer']}）")
            print(f"      任务: {sub['task'][:60]}")
            print(f"      原因: {sub['reason'][:60]}")
            print(f"      模式: {sub['mode']}")
    
    print(f"{'='*60}")
    
    # 意图校准（交互模式）
    if interactive and plan['task_type'] in ('analysis', 'operation'):
        print(f"\n  🤔 意图校准：我理解你的需求是「{query[:50]}」，将按以上{len(plan['steps'])}步执行。")
        try:
            confirm = input("  输入 y 确认执行 / n 取消 / 或修改需求: ").strip().lower()
            if confirm == 'n':
                print(f"  ⏹️ 已取消")
                ammo_put(f"管线取消(用户): {query[:50]}", category="pipeline_plan", ttl_level="realtime")
                return None
            elif confirm and confirm != 'y':
                # 用户修改了需求
                print(f"  🔄 需求更新为: {confirm[:100]}")
                ammo_put(f"管线需求更新: {query[:30]}→{confirm[:30]}", category="pipeline_plan", ttl_level="realtime")
                query = confirm
                plan = _plan_pipeline(query)
                trace_id = plan["trace_id"]
        except (EOFError, KeyboardInterrupt):
            pass  # 非交互环境,静默继续
    print()
    
    ammo_put(f"管线规划: {query[:50]} → 类型={plan['task_type']} 步骤={len(plan['steps'])}步",
             category="pipeline_plan", ttl_level="realtime",
             tags=["pipeline", "plan", plan['task_type']])
    
    # ─── 智能体编排执行（埃森哲三层级架构）───
    # 将编排指令写入临时文件，供主Agent读取后 spawn
    if plan['orchestration']:
        orch_file = f"/tmp/.pipeline_orch_{trace_id}.json"
        try:
            with open(orch_file, 'w') as f:
                json.dump({
                    "trace_id": trace_id,
                    "query": query[:200],
                    "orchestration": plan['orchestration'],
                    "task_type": plan['task_type'],
                }, f, ensure_ascii=False, indent=2)
            print(f"  → 📋 编排指令已写入 {orch_file}")
            print(f"  → 🏛️ 主Agent收到后将 spawn 对应子Agent并行执行")
        except Exception as e:
            print(f"  → ⚠️ 编排指令写入失败: {e}")
    
    print(f"[谛听] 构建事实晶体: {query}")

    # ─── 后台启动 R（右脑）管线 — 跟 L（左脑）并行跑 ───
    _r_future = None
    try:
        from scripts.resonator.right_brain import RightBrainPipeline
        _r_future = threading.Thread(
            target=lambda: setattr(threading.current_thread(), '_r_result',
                RightBrainPipeline(trace_id=trace_id).run(query)),
            daemon=True,
        )
        _r_future.start()
        print(f"  → 🎨 R管线已后台启动（与L管线并行）")
    except Exception as _r_err:
        print(f"  → 🎨 R管线后台启动失败: {_r_err}（将走串行兜底）")
        _r_future = None

    # 领域词表自动触发
    try:
        from bin.domain_loader import set_active_domain, get_domain, inject_domain_kw, _make_minimal_domain
        from diting.entity_extractor import BridgeAwareEntityExtractor
        topic = query[:10]
        domain = _make_minimal_domain(topic)
        set_active_domain(topic)
        inject_domain_kw(BridgeAwareEntityExtractor, domain)
        print(f"  [领域] 自动注入: {topic}")
    except Exception:
        pass

    search_results = _auto_search_fill(query)
    if search_results:
        src_counts = {}
        for r in search_results:
            s = r.get('source','unknown')
            src_counts[s] = src_counts.get(s, 0) + 1
        print(f"  → 外部搜索返回 {len(search_results)} 条结果")
        ammo_put(f"管线搜索: {query[:80]} → {len(search_results)}条 ({dict(src_counts)})",
                 category="pipeline_search", ttl_level="realtime", source="diting",
                 tags=["pipeline","search",query[:20]])
    else:
        ammo_put(f"管线搜索无结果: {query[:80]}",
                 category="pipeline_search", ttl_level="realtime", source="diting",
                 tags=["pipeline","search","empty",query[:20]])

    conn = None
    try:
        conn = sqlite3.connect(f'{WORKSPACE}/kunlun.db')
        from langhuan.db import init_db; init_db(conn)
        fc = build_factcrystal(query, conn=conn, search_results=search_results)
    except Exception:
        conn = None
        fc = build_staging_factcrystal(query)

    blinds = fc.completeness.get("blinds", [])
    is_staging = any("staging" in str(b).lower() or "降级" in str(b) for b in blinds)
    is_empty = len(fc.entities) < 2 and not fc.sources

    blind_count = _mark_blinds(conn, query, blinds, is_staging) if conn else 0
    if blind_count: print(f"  → 盲点标记: {blind_count} 条")

    if is_staging or is_empty:
        msg = f"⚠️ 知识库匹配度不足,管线跳过({len(blinds)}个盲点)。"
        fallback = f"📊 昆仑认知分析报告\n## {query}\n\n{msg}建议以直接推理替代管线输出。\n"
        print(f"  {msg}")
    # ── 📊 活性度记录：本次报告引用了哪些知识卡 ──
    try:
        cited = []
        for r in internal_results:
            title = r.get("title", "")
            if title and len(title) > 2:
                cited.append(title)
        if cited:
            import sys as _sys
            import os as _os
            _sys.path.insert(0, _os.path.join(_os.path.expanduser("~/.openclaw/workspace"), "scripts"))
            from knowledge_card_vitals import CardVitalsEngine
            v = CardVitalsEngine()
            v.record_citation(cited[:20], "pipeline")
    except Exception:
        pass

        if output: open(output,"w").write(fallback)
        return fallback

    print(f"  → {len(fc.entities)} entities, {len(fc.relations)} relations, {len(fc.temporal)} time windows")
    # F-2: 六层完整性检查
    if not is_staging and not is_empty:
        _check_six_layers(fc)
    from bin.bus_notify import publish; publish("diting","factcrystal.completed",trace_id)

    cards = _load_cards(conn) if conn else {"tools":[],"axioms":[],"learning":[]}
    print(f"  → 加载卡: AX={len(cards['axioms'])} TC={len(cards['tools'])} SC={len(cards['learning'])}")

    # 🆕 P0: 推理前归藏记忆检索注入——将相关记忆注入推理上下文
    _memories_for_reasoning = []
    if conn:
        try:
            from guicang.memory import MemoryEngine
            me = MemoryEngine(conn)
            _memories_for_reasoning = me.search_related_memories(query, top_k=5)
            if _memories_for_reasoning:
                print(f"  → [归藏·P0] 检索到 {len(_memories_for_reasoning)} 条相关记忆注入推理")
                for m in _memories_for_reasoning[:3]:
                    print(f"      [{m['source']}] {m['text'][:50]} (relevance={m['relevance']:.2f})")
        except Exception as e:
            print(f"  → [归藏·P0] 记忆检索跳过: {e}")

    # 将检索到的记忆注入 cards 的 learning 区供算子消费
    if _memories_for_reasoning:
        cards.setdefault("memory_injections", [])
        for m in _memories_for_reasoning:
            cards["memory_injections"].append(m)

    print(f"[太一] 五算子运行中...")
    models = run_all_operators(fc, cards, query=fc.query)
    synth = ModelSynthesizer()
    model = synth.synthesize(models["contradiction"], models["practice"], models["protracted_war"], models["ocgs"])

    # 无为算子结果
    wuwei = models.get("wuwei", {})
    print(f"  → 矛盾论: {model['contradiction']['primary']}")
    print(f"  → 持久战: {model['protracted_war']['primary']['label']}")
    print(f"  → 无为论: {wuwei.get('verdict','未评估')} - {wuwei.get('reason','')[:60]}")
    # F-1: 将持久战阶段注入FC temporal
    pw_label = model['protracted_war']['primary'].get('label','相持')
    pw_phase = model['protracted_war']['primary'].get('phase',0)
    for win in fc.temporal.values():
        win.phase_level = str(pw_phase)

    assertions = []
    for a in getattr(fc, '_assertions_stub', [])[:7]:
        assertions.append({"id":a.get("id",len(assertions)+1),"text":a.get("text",""),"stance":a.get("stance","0"),
            "evidence_level":a.get("evidence_level",2),"bridge":a.get("bridge","Q04"),
            "ternary":{"positive":1,"neutral":0,"negative":0},"counterfactual_branch":a.get("counterfactual_branch")})
    if not assertions:
        assertions = [{"id":1,"text":"信息不足","stance":"0","evidence_level":1,"bridge":"Q04","ternary":{"positive":1,"neutral":1,"negative":1}}]

    cube = {"query":fc.query,"model":model,"bridges":{"activated":["Q02","Q04","Q09"],"opposing":fc.prechecks.get("opposing_bridge_scanned",[])},
        "cards_used":{"tools":[c["card_id"] for c in cards["tools"][:3]],"learning":[c["card_id"] for c in cards["learning"][:3]],"axioms":[c["card_id"] for c in cards["axioms"][:3]]},
        "assertions":assertions,"ternary_landscape":{"positive":1,"neutral":0,"negative":0,"dominant":"+1"},
        "spiral":{"cycles":1,"converged":True},"uncertainty_flag":False,
        "wuwei": wuwei}

    check = check_cognitive_cube(cube)
    status = '✅ 自检通过' if check['pass'] else f"⚠️ {check.get('results','')}"
    print(f"[太一] {status}")

    # 📦 弹药箱记录：分析结果摘要
    activated_bridges_for_log = list(model.get('contradiction',{}).get('bridges',[])) or list(activated_bridges)
    ammo_put(f"管线分析: {query[:60]} → 矛盾{model.get('contradiction',{}).get('primary','?')[:40]} | "
             f"阶段{model.get('protracted_war',{}).get('primary',{}).get('label','?')} | "
             f"质量{score.get('health',0)}分",
             category="pipeline_analysis", ttl_level="short", source="taiyi",
             tags=["pipeline","analysis",query[:20],f"health={score.get('health',0)}"])

    publish("taiyi","analysis.completed",trace_id)

    # 🆕 P0: 推理后记忆存储 + 引用链建立
    if conn:
        try:
            from guicang.memory import MemoryEngine
            me = MemoryEngine(conn)
            store_result = me.store(trace_id, assertions)
            if store_result:
                print(f"  → [归藏] 已存储 {len(store_result)} 条记忆 (trace={trace_id})")
            # 引用链建立
            links = me.build_citation_links(trace_id, assertions)
            if links:
                print(f"  → [归藏] 建立 {links} 条引用边")
            # 贡力更新（P1）
            contrib = me.update_contribution_scores()
            if contrib["updated"] > 0:
                print(f"  → [归藏·P1] 贡力重算: {contrib['updated']}条, 平均={contrib['avg_contribution']}, 最高={contrib['max_contribution']}")
        except Exception as e:
            print(f"  → [归藏] 存储跳过: {e}")

    report = render_report(cube)
    qc = QualityChecker(); qr = qc.check(report, cube)
    score = compute_quality_score(cube)
    cube["_quality_score"] = score; cube["_report"] = report

    bridge_cov = _compute_bridge_coverage(cube)
    tensions = _detect_layer_tension(assertions, bridge_cov)
    spatial = _compute_spatial_expression(cube, bridge_cov, tensions)

    # ── P3: 物理AI可行性评估 ──
    phys = _physical_ai_assessment(fc, cube)
    if phys["overall"] != "概念阶段":
        print(f"  → P3物理AI: {phys['overall']} (物理成熟度={phys['physical_maturity']}, 系统集成={phys['system_maturity']})")

    print(f"  → 质量: {score['health']}/100 ({score['health_label']})")
    print(f"  → 桥覆盖: {bridge_cov}")
    if tensions: print(f"  → 层间张力: {len(tensions)} 处")

    # ═══ L+R 共振步骤(可选) — L+R现为真正并行 ═══
    _resonance_result = None
    _r_output = None
    try:
        from scripts.resonator.runner import run_full_resonance
        from scripts.resonator.models import LeftOutput, Claim, RightOutput

        # 等R管线跑完（后台线程可能在等待L计算期间已经完成）
        _r_parallel = None
        if _r_future is not None and _r_future.is_alive():
            _r_future.join()
            _r_parallel = getattr(_r_future, '_r_result', None)
            if _r_parallel:
                print(f"  → 🎨 R管线并行完成（与L管线重叠执行）")
        elif _r_future is not None:
            _r_parallel = getattr(_r_future, '_r_result', None)

        # 构造左脑产出
        left = LeftOutput(
            query=query,
            contradiction_primary=model.get('contradiction',{}).get('primary',''),
            protracted_war_phase=pw_label,
            claims=[Claim(
                text=a.get('text',''),
                bridge=a.get('bridge',''),
                confidence=a.get('evidence_level',2),
                evidence_level=a.get('evidence_level',2),
                source_refs=[s.get('title','') for s in (a.get('sources',[]) or [])[:3]],
                uncertainty=1.0 - (a.get('evidence_level',2)/3.0)
            ) for a in assertions[:5]],
            structures=[a.get('text','') for a in assertions[:3]],
            frames=[f"矛盾论:{model.get('contradiction',{}).get('primary','')}"],
            bridge_coverage=bridge_cov,
            tensions=tensions,
            quality_score=score.get('health',0),
            uncertainty_flag=cube.get("uncertainty_flag", False),
        )
        # 传递R后台结果，跳过序列执行的R
        out = run_full_resonance(
            query, left=left, right=_r_parallel, trace_id=trace_id,
        )
        _resonance_result = out["result"]
        _r_output = out.get("right_output", _r_parallel)
        print(f"  → 🧠🌙 共振: {_resonance_result.mode_detail}")
        if _resonance_result.has_amplification:
            print(f"      🔊 同频放大: {len(_resonance_result.amplifications)}条")
        if _resonance_result.has_conflict:
            print(f"      ⚠️ 异频检错: {len(_resonance_result.conflicts)}条 - 注意分歧!")
        if _resonance_result.has_emergence:
            print(f"      ✨ 新频涌现: {len(_resonance_result.emergences)}条")
    except Exception as e:
        print(f"  → 🧠 共振跳过: {e}")
        ammo_put(f"管线共振失败: {query[:60]} → {str(e)[:100]}",
                 category="pipeline_error", ttl_level="short", source="resonator",
                 tags=["pipeline","error","resonance",query[:20]])
        try:
            from scripts.anomaly_logger import anomaly_log
            with anomaly_log("共振器", component="bin/pipeline") as _log:
                _log.warn(str(e)[:200])
        except Exception:
            pass

    if conn:
        persist_quality(conn, query, cube, score, blinds=len(blinds))
        if score["health"] < 40:
            try:
                conn.execute("INSERT OR IGNORE INTO tianyan_evolution_rules(rule_id,name,source,pattern,action) VALUES(?,?,?,?,?)",
                    (f"EV-{trace_id}",f"低质量反馈: {query[:30]}","pipeline",f"health={score['health']}","increase_evidence_coverage"))
                conn.commit(); print(f"  → 天演: 已记录低质量反馈规则")
            except: pass

    # ── Phase A: FC缺桥检测 ──
    activated_bridges = {a.get("bridge","") for a in assertions if a.get("bridge")}
    missing_info = _detect_missing_bridges(conn, activated_bridges)
    if missing_info.get("missing"):
        print(f"  → 缺桥检测: +1激活{len(activated_bridges)}桥, 0待探查{len(missing_info['missing'])}桥")
        for p in missing_info["probes"]:
            print(f"     探针: {p['probe_query'][:50]}")

    # ── Phase B: 探针执行+断言卡生成 ──
    probe_results = []
    sc_card_count = 0
    if missing_info.get("probes"):
        print(f"  → Phase B: 执行探针搜索...")
        probe_results = _execute_probes(missing_info["probes"], query)
        for pr in probe_results:
            if pr.get("found",0) >= 2:
                print(f"     桥{pr['bridge_id']}发现{pr['found']}条结果")
        # 生成缺桥断言
        missing_assertions = _create_missing_assertions(probe_results, query)
        if missing_assertions:
            assertions.extend(missing_assertions)
            print(f"     +{len(missing_assertions)}条缺桥断言注入")
        # 暂存SC卡
        if conn:
            sc_card_count = _generate_sc_cards(conn, probe_results)
            if sc_card_count:
                print(f"     +{sc_card_count}张探针SC卡写入琅嬛")

    publish("tiangong","render.completed",trace_id)

    report += f"\n\n---\n\n{_render_six_dim_chart(spatial, score)}\n"
    for dim, val in spatial["dimensions"].items(): report += f"| {dim} | {val} |\n"
    report += f"\n### 三元世界模型\n\n"
    for layer, info in spatial["world_model"].items(): report += f"- **{layer}层**: {info['assertions']} 条断言\n"
    report += f"\n### 缺失桥探测(Phase A)\n\n"
    states = missing_info.get("bridge_states", {})
    report += "| 桥 | 名称 | 三态 |\n|:---|:-----|:----:|\n"
    for bid in sorted(states.keys()):
        s = states[bid]
        icon = {"+1":"✅","0":"🟡","-1":"○"}.get(s,"?")
        name = _BRIDGE_PROFILE_CACHE.get(bid,{}).get("name","") if _BRIDGE_PROFILE_CACHE else ""
        report += f"| {bid} | {name} | {icon}{s} |\n"
    if missing_info.get("probes"):
        report += f"\n**建议探针查询:**\n"
        for p in missing_info["probes"]:
            report += f"- {p['bridge_name']}({p['bridge_id']}): {p['probe_query']}\n"
    # ── Phase B: 探针执行结果 ──
    if probe_results:
        report += f"\n### 缺桥自动探查(Phase B)\n\n| 桥 | 名称 | 发现结果 |\n|:---|:-----|:--------:|\n"
        for pr in probe_results:
            status = "✅" if pr.get("found",0) >= 2 else ("❌" if pr.get("found",0) == 0 else "⚠️")
            report += f"| {pr['bridge_id']} | {pr['bridge_name']} | {status}{pr.get('found',0)}条 |\n"
        if sc_card_count:
            report += f"\n自动生成{sc_card_count}张探针SC卡,已写入琅嬛。\n"
        if missing_assertions:
            report += f"\n自动注入{len(missing_assertions)}条缺桥断言:\n"
            for ma in missing_assertions:
                report += f"- [{ma['bridge']}] {ma['text'][:60]}\n"
    # ── P3: 物理AI可行性评估 ──
    if phys["overall"] != "概念阶段":
        report += f"\n### 物理AI可行性评估(P3)\n\n"
        report += f"| 维度 | 评分 | 说明 |\n|:-----|:----:|:-----|\n"
        report += f"| 物理成熟度 | {phys['physical_maturity']} | 零部件层占比{phys['physical_ratio']:.0%} |\n"
        report += f"| 系统集成度 | {phys['system_maturity']} | 系统层占比{phys['system_ratio']:.0%} |\n"
        report += f"| 认知赋能 | {phys['cognitive_ratio']:.0%} | AI层占比 |\n"
        report += f"| **综合判定** | **{phys['overall']}** | 复合分数{phys['composite']}/3 |\n"
        report += f"\n{phys['physical_detail']}\n"
    # ── 共振结果追加 ──
    if _resonance_result:
        report += f"\n### 🧠🌙 L+R共振结果\n\n"
        if _resonance_result.amplifications:
            for a in _resonance_result.amplifications[:3]:
                report += f"- 🔊 同频: {a.claim.text[:50]} 信度{a.confidence_before}→{a.confidence_after}\n"
        if _resonance_result.conflicts:
            for c in _resonance_result.conflicts[:2]:
                report += f"- ⚠️ 分歧: {c.diagnosis[:60]}\n"
        if _resonance_result.emergences:
            for e in _resonance_result.emergences[:2]:
                report += f"- ✨ 涌现: {e.synthesis[:60]}\n"
        if _r_output:
            if _r_output.intuitions:
                for i in _r_output.intuitions[:2]:
                    report += f"- 🎭 直觉: {i.text[:50]}\n"
            if _r_output.incongruities:
                for inc in _r_output.incongruities[:2]:
                    report += f"- ⚡ 不协调: {inc.description[:50]}\n"

    report += f"\n---\n\n**健康度**: {score['health']}/100 ({score['health_label']})\n"

    # ── 🪞 P1-⑦ 真话放大镜自动验证（输出前最后一道门）──
    _truth_appendix = ""
    try:
        _tm_dir = os.path.join(WORKSPACE, "skills", "真话放大镜")
        if _tm_dir not in sys.path:
            sys.path.insert(0, _tm_dir)
        # 优先使用 V2 真话放大镜（可验证声明体系），降级到 v3.2
        try:
            from scripts.truth_magnifier_hook_v2 import auto_verify_pipeline
        except ImportError:
            from scripts.truth_magnifier_hook import auto_verify_pipeline
        _truth_appendix = auto_verify_pipeline(report, cube)
        if _truth_appendix:
            report += _truth_appendix
            print(f"  → 🪞 真话放大镜验证: 已追加验证附录")
        else:
            print(f"  → 🪞 真话放大镜验证: ✅ 通过")
    except Exception as e:
        print(f"  → 🪞 真话放大镜验证跳过: {e}")

    if output:
        with open(output,"w") as f: f.write(report)
        print(f"\n📄 报告已保存: {output}")
    return report


# ═══════ CLI入口 ═══════

def main():
    parser = argparse.ArgumentParser(description="昆仑认知管线 CLI")
    sub = parser.add_subparsers(dest="cmd")
    run_parser = sub.add_parser("run", help="运行分析管线")
    run_parser.add_argument("query", help="分析查询")
    run_parser.add_argument("--output","-o",default=None,help="输出文件")
    run_parser.add_argument("--staging",action="store_true",default=True,help="使用staging数据")
    args = parser.parse_args()
    if args.cmd == "run":
        report = run_pipeline(args.query, args.output, args.staging)
        if not args.output: print(report)
    else: parser.print_help()


# ═══════ F-2: FC六层完整性检查 ═══════

def _check_six_layers(fc) -> dict:
    """FC构造后自动检查六层(技术·资本·人才·政策·治理·应用)完整性"""
    _SIX_LAYERS = {
        "技术":    {"bridges": ["Q01","Q03"], "desc": "核心技术与硬件基础"},
        "资本":    {"bridges": ["Q10"],       "desc": "产业投资与资本市场"},
        "人才":    {"bridges": ["Q05"],       "desc": "人才培养与知识储备"},
        "政策":    {"bridges": ["Q02"],       "desc": "产业政策与制度环境"},
        "治理":    {"bridges": ["Q08"],       "desc": "标准体系与协同治理"},
        "应用":    {"bridges": ["Q04"],       "desc": "场景落地与市场适配"},
    }

    # 从实体中提取已覆盖的桥
    covered_bridges = set()
    for e in fc.entities:
        for b in e.discovered_by:
            covered_bridges.add(b[:3])


    missing = []
    for layer_name, info in _SIX_LAYERS.items():
        has = any(b in covered_bridges for b in info["bridges"])
        if not has:
            missing.append({"layer": layer_name, "target_bridge": info["bridges"][0], "desc": info["desc"]})

    if missing:
        print(f"  ⚠️ FC六层完整性检查: 缺{len(missing)}层")
        for m in missing:
            print(f"     缺{m['layer']}({m['desc']}) → 建议补充{m['target_bridge']}实体")
    else:
        print(f"  ✅ FC六层完整性检查: 六层全部覆盖")

    return {"complete": len(missing) == 0, "missing": missing}


# ═══════ 安全+并发管线 ═══════

def run_pipeline_safe(query: str, output: str = None) -> str:
    try:
        fc = build_factcrystal(query, search_results=[])
    except Exception:
        print("[谛听] 搜索不可用·降级staging")
        fc = build_staging_factcrystal(query)
    try:
        models = run_all_operators(fc, {})
    except Exception:
        print("[太一] 算子失败·默认模型")
        models = {"contradiction":{},"practice":{},"protracted_war":{},"ocgs":{}}
    return "ok"

def run_pipeline_concurrent(queries: list[str], max_workers: int = 3) -> list[dict]:
    results, errors = [], []
    def _worker(q):
        try: results.append({"query":q,"status":"ok","output":run_pipeline(q)[:200]})
        except Exception as e: errors.append({"query":q,"status":"error","error":str(e)[:100]})
    threads = []
    for q in queries:
        t = threading.Thread(target=_worker, args=(q,)); t.start(); threads.append(t)
        if len(threads) >= max_workers:
            for t in threads: t.join(); threads = []
    for t in threads: t.join()
    return {"completed":len(results),"errors":len(errors),"results":results,"error_details":errors}

if __name__ == "__main__":
    # 全局异常钩子:未捕获的异常写入弹药箱+打印摘要,不沉默
    try:
        main()
    except Exception as e:
        import traceback as _tb
        _exc = _tb.format_exc()[:2000]
        print(f"💥 管线崩溃: {e}")
        try:
            from scripts.anomaly_logger import anomaly_log
            with anomaly_log("pipeline.main", component="bin/pipeline") as _log:
                _log.error(str(e)[:300])
        except Exception:
            pass
        print(f"  详情:\n{_exc}")
