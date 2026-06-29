"""多渠道路由搜索 — EnhancedSearchRouter
昆仑洞天 v7.1 — 谛听v6.5对齐

4层检索路由：
  L1 FTS5 — 琅嬛全文搜索（jieba分词+ILIKE）
  L2 图谱扩散 — FTS命中卡沿知识图谱边扩散
  L3 三力排序 — 归藏记忆召回 + 存通炼排序
  L4 分歧力 — contradictions边反向检索，让对立观点可见

缓存层（v1.1）:
  通过 langhuan.cache.cached_search 集成 LRU 缓存
  热门查询走缓存 ≈1μs，不走 FTS5 ≈10-50ms
"""

from __future__ import annotations
import json, sqlite3
from typing import Optional
from langhuan.cache import cached_search


def _record_vitals(results: list[dict]):
    """将搜索命中的知识卡片记入活性度引擎 + 记录共现对"""
    card_names = [r.get("title", "") for r in results if r.get("title")]
    if not card_names:
        return
    try:
        import sys as _sys
        import os as _os
        _sys.path.insert(0, _os.path.join(_os.path.expanduser("~/.openclaw/workspace"), "scripts"))
        from knowledge_card_vitals import CardVitalsEngine  # type: ignore
        v = CardVitalsEngine()
        v.record_retrieval(card_names)
        
        # 记录检索共现对（用于关联网络）
        if len(card_names) >= 2:
            from knowledge_graph_builder import KnowledgeGraph  # type: ignore
            kg = KnowledgeGraph()
            pairs = []
            for i in range(len(card_names)):
                for j in range(i + 1, len(card_names)):
                    pairs.append((card_names[i], card_names[j]))
            kg.record_cooccur(pairs)
    except Exception:
        pass  # vitals 非关键路径，不打断搜索


def _epsilon_greedy(query: str, results: list[dict], 
                    top_k: int = 30) -> list[dict]:
    """
    ε-贪心采样：以一定概率从休眠池随机抽取卡片探索。
    修改搜索结果的返回列表，加入探索结果。
    """
    import random as _random
    import os as _os
    import sys as _sys
    import json as _json
    
    # 基础探索率 3%
    epsilon = 0.03
    confidence = 0.5
    
    # 根据顶部结果的置信度决定探索力度
    if results:
        top_rel = max(r.get("relevance", 0) for r in results[:3])
        if top_rel < 0.4:
            epsilon = max(epsilon, 0.30)  # 置信度不足，加大探索
    
    if _random.random() >= epsilon:
        return results  # 不探索
    
    # 从休眠池随机抽卡
    try:
        vitals_path = _os.path.join(
            _os.path.expanduser("~/.openclaw/workspace"),
            "data", "knowledge_vitals.json"
        )
        with open(vitals_path) as _f:
            _v = _json.load(_f)
        
        # 找出所有休眠+温卡
        candidates = []
        for name, info in _v.get("cards", {}).items():
            status = info.get("status", "dormant")
            if status in ("dormant", "warm"):
                candidates.append(name)
        
        if not candidates:
            return results
        
        # 取一张随机休眠卡
        chosen = _random.choice(candidates)
        
        # 检查是否已在结果中
        existing = {r.get("title", "") for r in results}
        if chosen in existing:
            return results
        
        # 构造一个低相关度伪结果
        from datetime import datetime as _dt
        fake_result = {
            "title": chosen,
            "card_id": f"explore_{chosen}",
            "content": f"[ε-探索] 休眠卡片: {chosen}",
            "source": "epsilon_explore",
            "relevance": max(0.1, confidence * 0.3),  # 低权重
            "explore": True,
            "timestamp": _dt.now().isoformat(),
        }
        results = list(results) + [fake_result]
        results.sort(key=lambda r: r.get("relevance", 0), reverse=True)
    except Exception:
        pass
    
    return results


# ─── 探索后记录采纳（在渲染/引用时调用） ───
def record_adoption_direct(card_title: str, agent_id: str = "search"):
    """外部调用的采纳记录函数"""
    try:
        import sys as _sys
        import os as _os
        _sys.path.insert(0, _os.path.join(_os.path.expanduser("~/.openclaw/workspace"), "scripts"))
        from knowledge_card_vitals import CardVitalsEngine
        v = CardVitalsEngine()
        v.record_adoption(card_title, agent_id)
    except Exception:
        pass


class EnhancedSearchRouter:
    """增强搜索路由器——4层路由 + 分歧力扩散"""

    def __init__(self, conn: sqlite3.Connection, guicang_conn: Optional[sqlite3.Connection] = None):
        self.conn = conn
        self.guicang = guicang_conn or conn
        # 四力排序权重（可调优）——🆕 P1: 三力→四力（加入贡力）
        self.freshness_weight = 0.15   # 存力
        self.circulation_weight = 0.30 # 通力
        self.authority_weight = 0.30   # 炼力
        self.contribution_weight = 0.25 # 🆕 贡力

    def search(self, query: str, max_results: int = 30,
               enable_oppose: bool = True, use_cache: bool = True) -> list[dict]:
        """
        四层检索路由，返回统一格式搜索结果。
        enable_oppose: 是否启用L4分歧力（默认启）
        use_cache: 是否使用 LRU 缓存（默认启）
        """
        if use_cache:
            def _fts_search_wrapper(q, limit=max_results, **kwargs):
                return self._search_fts(q, limit)
            cached_results = cached_search(
                _fts_search_wrapper, query,
                limit=max_results, enable_oppose=enable_oppose
            )
            if cached_results:
                # L1 缓存命中 → L2-L4 继续正常跑
                results = list(cached_results)
                seen = {self._key(r) for r in results}
                # L2: 图谱扩散
                if len(results) < max_results:
                    for r in self._search_graph(query, max_results * 2):
                        key = self._key(r)
                        if key not in seen:
                            seen.add(key)
                            results.append(r)
                # L3: 归藏记忆
                if len(results) < max_results:
                    for r in self._search_memory_tri_force(query, max_results):
                        key = self._key(r)
                        if key not in seen:
                            seen.add(key)
                            results.append(r)
                # L4: 分歧力
                if enable_oppose and len(results) >= 2:
                    for r in self._search_oppose(query, seen):
                        key = self._key(r)
                        if key not in seen:
                            seen.add(key)
                            results.append(r)
                # 端云协同：根据已命中量决定云和技能的记忆查多少
                cached_local = len(results)
                cached_sat = cached_local / max(max_results, 1)
                if cached_sat >= 0.8:
                    cld_lim, skl_lim = 2, 1
                elif cached_sat >= 0.5:
                    cld_lim, skl_lim = 5, 3
                else:
                    cld_lim, skl_lim = 8, 5
                # L5: 云端知识卡
                if len(results) < max_results:
                    for r in self._search_cloud(query, cld_lim):
                        key = self._key(r)
                        if key not in seen:
                            seen.add(key)
                            results.append(r)
                # 混合排序：确保云端卡可见
                cloud_items_c = [rr for rr in results if rr.get('_cloud')]
                if cloud_items_c:
                    for rr in cloud_items_c:
                        rr['relevance'] = round(rr.get('relevance', 0.3) + 0.12, 3)
                    results.sort(key=lambda rr: rr.get('relevance', 0.3), reverse=True)
                # L6: 技能记忆（L4 skill_memory）
                if len(results) < max_results:
                    for rr in self._search_skill_memory(query, skl_lim):
                        key = self._key(rr)
                        if key not in seen:
                            seen.add(key)
                            results.append(rr)
                # 🔴 活性度记录
                _record_vitals(results)
                results = _epsilon_greedy(query, results, max_results)
                return results[:max_results]

        return self._search_full(query, max_results, enable_oppose)

    def _search_full(self, query: str, max_results: int = 30,
                     enable_oppose: bool = True) -> list[dict]:
        """完整四层搜索（不走缓存）"""
        results = []
        seen_keys = set()

        # ═══ L1: FTS5 全文搜索 ═══
        for r in self._search_fts(query, max_results):
            key = self._key(r)
            if key not in seen_keys:
                seen_keys.add(key)
                results.append(r)

        # ═══ L2: 知识图谱扩散 ═══
        if len(results) < max_results:
            for r in self._search_graph(query, max_results * 2):
                key = self._key(r)
                if key not in seen_keys:
                    seen_keys.add(key)
                    results.append(r)

        # ═══ L3: 归藏记忆三力排序召回 ═══
        if len(results) < max_results:
            for r in self._search_memory_tri_force(query, max_results):
                key = self._key(r)
                if key not in seen_keys:
                    seen_keys.add(key)
                    results.append(r)

        # ═══ L4: 分歧力扩散 ═══
        if enable_oppose and len(results) >= 2:
            oppose_results = self._search_oppose(query, seen_keys)
            for r in oppose_results:
                key = self._key(r)
                if key not in seen_keys:
                    seen_keys.add(key)
                    results.append(r)

        # ═══ 端云协同降级策略（受鸿蒙2030白皮书启发）═══
        # 先统计本地命中量（L1-L4），决定云端查多少
        local_count = len(results)
        local_saturation = local_count / max(max_results, 1)
        
        # L5云卡搜索量: 本地越饱和,云端查越少
        if local_saturation >= 0.8:
            cloud_limit = 2   # 本地够用,云端轻量查2条
            skill_limit = 1   # 技能记忆查1条
            tier_status = "local_saturated"
        elif local_saturation >= 0.5:
            cloud_limit = 5   # 本地中等,云端正常查
            skill_limit = 3
            tier_status = "local_moderate"
        else:
            cloud_limit = 8   # 本地不足,云端全力填充
            skill_limit = 5
            tier_status = "local_underfilled"
        
        # ═══ L5: 云端知识卡搜索（225张云卡） ═══
        cloud_results = self._search_cloud(query, cloud_limit)
        for r in cloud_results:
            key = self._key(r)
            if key not in seen_keys:
                seen_keys.add(key)
                # 本地饱和时,云卡relevance降低; 本地不足时,云卡relevance提升
                base_relevance = r.get('relevance', 0.3)
                if local_saturation >= 0.8:
                    r['relevance'] = round(base_relevance - 0.05, 3)
                elif local_saturation < 0.5:
                    r['relevance'] = round(base_relevance + 0.10, 3)
                results.append(r)

        # ═══ L6: 技能记忆检索（L4 skill_memory） ═══
        skill_results = self._search_skill_memory(query, skill_limit)
        for r in skill_results:
            key = self._key(r)
            if key not in seen_keys:
                seen_keys.add(key)
                # 本地饱和时,技能记忆权重也略降
                base_relevance = r.get('relevance', 0.3)
                if local_saturation >= 0.8:
                    r['relevance'] = round(base_relevance - 0.05, 3)
                results.append(r)

        # 🔴 活性度记录
        _record_vitals(results)
        # ε-贪心探索采样
        results = _epsilon_greedy(query, results, max_results)
        print(f"    [端云协同] 状态={tier_status} 本地={local_count}/{max_results} 云限={cloud_limit} 技能限={skill_limit}")
        
        # 保底：云端卡+技能记忆不占用其他结果位置
        cloud_final = [r for r in results if r.get('_cloud')]
        skill_final = [r for r in results if r.get('_skill_memory')]
        regular = [r for r in results if not r.get('_cloud') and not r.get('_skill_memory')]
        
        keep_cloud = min(2, len(cloud_final))
        keep_skill = min(1, len(skill_final))
        keep_regular = max(0, max_results - keep_cloud - keep_skill)
        
        for r in cloud_final:
            r['relevance'] = round(r.get('relevance', 0.3) + 0.08, 3)
        for r in skill_final:
            r['relevance'] = round(r.get('relevance', 0.3) + 0.22, 3)
        
        results = regular[:keep_regular] + skill_final[:keep_skill] + cloud_final[:keep_cloud]
        results.sort(key=lambda r: r.get('relevance', 0.3), reverse=True)
        return results[:max_results]

    def search_and_format(self, query: str, max_results: int = 30) -> list[dict]:
        """搜索并格式化为 entity_extractor 可消费格式"""
        raw = self.search(query, max_results)
        return [
            {"title": r.get("title", ""), "content": r.get("content", ""),
             "source": r.get("source", "unknown"), "card_id": r.get("card_id", ""),
             "relevance": r.get("relevance", 0.5)}
            for r in raw
        ]

    # ── 内部工具 ──

    @staticmethod
    def _key(r: dict) -> str:
        """去重键"""
        return r.get("card_id") or r.get("memory_id") or r.get("title", "")[:60]

    # ── L1: FTS5 全文搜索 ──

    def _search_fts(self, query: str, limit: int) -> list[dict]:
        """琅嬛全文搜索——双链ILIKE + FTS5精确匹配"""
        results = []
        try:
            bigrams = [query[i:i+2] for i in range(0, len(query)-1)] if len(query) >= 2 else [query]
            like_clauses = ["title LIKE ?", "content LIKE ?"]
            params = [f"%{query}%", f"%{query}%"]
            for bg in bigrams[:3]:
                like_clauses.append("title LIKE ?")
                params.append(f"%{bg}%")
            where = " OR ".join(like_clauses)
            rows = self.conn.execute(
                f"SELECT card_id, title, content, card_type FROM knowledge_cards "
                f"WHERE {where} LIMIT ?", (*params, limit)).fetchall()
            results = [
                {"source": "fts", "card_id": r[0], "title": r[1],
                 "content": (r[2] or "")[:500], "relevance": 0.8, "_type": r[3]}
                for r in rows
            ]
        except Exception:
            pass

        # FTS5 精确匹配补位
        if len(results) < limit and query.isascii():
            try:
                safe = query.replace('-', '_').replace('"', '')
                fts_rows = self.conn.execute(
                    "SELECT card_id, title, content FROM knowledge_fts "
                    "WHERE knowledge_fts MATCH ? ORDER BY rank LIMIT ?",
                    (safe, limit - len(results))).fetchall()
                existing = {r["card_id"] for r in results}
                results.extend(
                    {"source": "fts_match", "card_id": r[0], "title": r[1],
                     "content": (r[2] or "")[:500], "relevance": 1.0}
                    for r in fts_rows if r[0] not in existing
                )
            except Exception:
                pass
        return results

    # ── L5: 云端知识卡搜索（MCP云容器225张卡） ──

    def _search_cloud(self, query: str, limit: int = 5) -> list[dict]:
        """通过MCP协议搜索云端知识卡库（225张）"""
        import urllib.request
        import json as _json

        MCP_URL = "http://101.245.88.123:8888/mcp/messages"
        results = []

        try:
            payload = _json.dumps({
                "jsonrpc": "2.0", "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "search_knowledge_cards",
                    "arguments": {"query": query, "limit": limit}
                }
            }).encode()
            req = urllib.request.Request(
                MCP_URL, data=payload,
                headers={"Content-Type": "application/json"}
            )
            resp = urllib.request.urlopen(req, timeout=8)
            data = _json.loads(resp.read())

            cards_text = data.get("result", {}).get("content", [{}])[0].get("text", "[]")
            cards = _json.loads(cards_text) if isinstance(cards_text, str) else cards_text
            if isinstance(cards, dict):
                cards = cards.get("results", cards.get("cards", [cards]))
            if not isinstance(cards, list):
                cards = []

            seen = set()
            for c in cards:
                cid = c.get("card_id", "") or c.get("id", "")
                title = c.get("title", "")[:80]
                content = (c.get("content", "") or c.get("summary", "") or "")[:500]
                domain = c.get("domain", c.get("bridge_id", "cloud"))
                if title in seen:
                    continue
                seen.add(title)
                results.append({
                    "source": "cloud_knowledge",
                    "card_id": f"cloud-{cid}" if cid else f"cloud-{title[:20]}",
                    "title": f"[云] {title}",
                    "content": content,
                    "relevance": 0.65,
                    "_domain": domain,
                    "_cloud": True,
                })

        except Exception:
            pass
        return results[:limit]

    # ── L2: 知识图谱扩散 ──

    def _search_graph(self, query: str, limit: int) -> list[dict]:
        """FTS命中卡沿知识图谱边扩散"""
        try:
            seeds = self.conn.execute(
                "SELECT card_id FROM knowledge_cards "
                "WHERE title LIKE ? OR content LIKE ? LIMIT 3",
                (f"%{query}%", f"%{query}%")).fetchall()
            if not seeds:
                return []
            seed_ids = [s[0] for s in seeds]
            ph = ",".join("?" * len(seed_ids))
            rows = self.conn.execute(
                f"SELECT DISTINCT ke.to_card, kc.title, kc.content, ke.edge_type, ke.strength "
                f"FROM knowledge_edges ke JOIN knowledge_cards kc ON ke.to_card = kc.card_id "
                f"WHERE ke.from_card IN ({ph}) ORDER BY ke.strength DESC LIMIT ?",
                (*seed_ids, limit)).fetchall()
            return [
                {"source": "graph", "card_id": r[0], "title": r[1],
                 "content": (r[2] or "")[:500], "relevance": r[4] or 0.5,
                 "_edge_type": r[3]} for r in rows
            ]
        except Exception:
            return []

    # ── L3: 三力排序召回 ──

    def _search_memory_tri_force(self, query: str, limit: int) -> list[dict]:
        """归藏记忆召回 + 三力排序（存力×通力×炼力）"""
        try:
            rows = self.guicang.execute(
                "SELECT memory_id, text, stance, evidence_level, score, layer, "
                "created_at, access_count, COALESCE(citation_count,0), COALESCE(verification_count,0) "
                "FROM guicang_memories "
                "WHERE archived_at IS NULL AND text LIKE ? "
                "LIMIT ?", (f"%{query}%", limit)).fetchall()
        except Exception:
            return []

        results = []
        import datetime
        now = datetime.datetime.now()
        for r in rows:
            mid, text, stance, ev_level, score, layer, created_at, access_count, cit, ver = (
                r[0], r[1] or "", r[2] or "0", r[3] or 1, r[4] or 0.5,
                r[5] or "unknown", r[6], r[7] or 0, r[8] or 0, r[9] or 0
            )
            # 三力计算
            try:
                if created_at:
                    age = (now - datetime.datetime.strptime(str(created_at)[:19], "%Y-%m-%d %H:%M:%S")).days
                else:
                    age = 999
            except Exception:
                age = 999
            # 四力计算 + 🆕 贡力
            freshness = 1.0 / (age + 1)  # 存力
            circulation = min(access_count, 20) / 20.0  # 通力
            authority = ev_level / 3.0  # 归一化到0-1

            # 🆕 贡力: 从 citation_count + verification_count 计算
            try:
                cit = r[8] if len(r) > 8 else 0
                ver = r[9] if len(r) > 9 else 0
            except Exception:
                cit = 0
                ver = 0
            cit_norm = min(cit, 10) / 10.0 * 0.4
            ver_norm = min(ver, 10) / 10.0 * 0.35
            contribution = cit_norm + ver_norm  # 践贡暂不计（需要access_count>1才有）

            tri_force_score = (
                freshness * self.freshness_weight +
                circulation * self.circulation_weight +
                authority * self.authority_weight +
                contribution * self.contribution_weight
            )

            results.append({
                "source": "memory",
                "memory_id": mid,
                "title": f"记忆: {text[:60]}",
                "content": text[:500],
                "stance": stance,
                "relevance": round(tri_force_score, 3),
                "_evidence_level": ev_level,
                "_layer": layer,
                "_tri_force": {"freshness": round(freshness, 3),
                               "circulation": round(circulation, 3),
                               "authority": round(authority, 3),
                               "contribution": round(contribution, 3)},
            })

        results.sort(key=lambda x: -x["relevance"])
        return results

    # ── L4: 分歧力回路 ═══

    def _search_oppose(self, query: str, existing_keys: set) -> list[dict]:
        """分歧力扩散——搜索 contradict 边，让对立观点可见
        
        核心机制：FTS命中卡的 knowledge_edges 中 edge_type='contradicts' 的反向检索
        """
        results = []
        try:
            # 先找到匹配query的卡
            seed_cards = self.conn.execute(
                "SELECT card_id FROM knowledge_cards "
                "WHERE title LIKE ? OR content LIKE ? LIMIT 5",
                (f"%{query}%", f"%{query}%")).fetchall()
            if not seed_cards:
                return []

            seed_ids = [s[0] for s in seed_cards]
            ph = ",".join("?" * len(seed_ids))

            # 从这些卡的 contradicts 边找对立卡
            oppose_rows = self.conn.execute(
                f"SELECT DISTINCT ke.from_card, kc.title, kc.content, ke.strength "
                f"FROM knowledge_edges ke "
                f"JOIN knowledge_cards kc ON ke.from_card = kc.card_id "
                f"WHERE ke.to_card IN ({ph}) AND ke.edge_type IN ('contradicts','opposes') "
                f"ORDER BY ke.strength DESC LIMIT 5",
                *[seed_ids]).fetchall()

            # 对称方向：种子卡发出的 contradict 边指向的卡
            oppose_rows2 = self.conn.execute(
                f"SELECT DISTINCT ke.to_card, kc.title, kc.content, ke.strength "
                f"FROM knowledge_edges ke "
                f"JOIN knowledge_cards kc ON ke.to_card = kc.card_id "
                f"WHERE ke.from_card IN ({ph}) AND ke.edge_type IN ('contradicts','opposes') "
                f"ORDER BY ke.strength DESC LIMIT 5",
                *[seed_ids]).fetchall()

            seen_cids = set()
            for row in oppose_rows + oppose_rows2:
                cid = row[0]
                if cid in seed_ids or cid in seen_cids:
                    continue
                seen_cids.add(cid)
                results.append({
                    "source": "oppose",
                    "card_id": cid,
                    "title": row[1] or "",
                    "content": (row[2] or "")[:500],
                    "relevance": 0.6,
                    "_oppose": True,
                })

        except Exception:
            pass
        return results

    # ── L6: 技能记忆检索（L4 skill_memory） ──

    def _search_skill_memory(self, query: str, limit: int = 5) -> list[dict]:
        """检索技能记忆库（含FTS5全文搜索+标签匹配）"""
        try:
            import sys as _sys
            _sys.path.insert(0, "")
            from scripts.skill_memory import SkillMemory  # type: ignore
            sm = SkillMemory()
            raw = sm.search(query, max_results=limit)
            return [
                {"source": "skill_memory",
                 "card_id": r.get("skill_id", ""),
                 "title": f"[规则] {r.get('title', '')}",
                 "content": r.get("summary", "")[:300],
                 "relevance": 0.55 if r.get("confidence") == "T3" else 0.65,
                 "_skill_memory": True,
                 "_confidence": r.get("confidence", "T3"),
                 "_category": r.get("category", ""),
                 "_condition": r.get("condition", ""),
                }
                for r in raw
            ]
        except Exception:
            return []
