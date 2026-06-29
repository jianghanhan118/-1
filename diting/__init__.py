# 昆仑洞天 v7.1 — 谛听 __init__.py
"""谛听 DiTing — 感知引擎·搜索路由·v6.5对齐"""

from xuanfu.schema import FactCrystal, Entity, Relation, TernaryDistribution, TemporalWindow
from diting.entity_extractor import BridgeAwareEntityExtractor
from diting.temporal import TemporalSlicer, FourLensPrecheck

# v7.1 新增组件
from diting.search_entry import SearchEntry
from diting.proposition_analyzer import PropositionAnalyzer, SearchGraph
from diting.enhanced_search import EnhancedSearchRouter
from diting.spiral_enricher import SpiralEnricher

def _write_ternary_edges(conn, fc: FactCrystal):
    """P3b-1: 将事实晶体的三元关系写入 knowledge_edges"""
    if not conn or not fc.relations:
        return
    for r in fc.relations:
        try:
            conn.execute(
                "INSERT OR REPLACE INTO knowledge_edges(from_card,to_card,edge_type,strength,source,"
                "ternary_pos,ternary_neu,ternary_neg,ternary_direction) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    r.from_entity, r.to_entity, r.type,
                    r.ternary.balance, "diting_" + fc.query[:20],
                    r.ternary.positive, r.ternary.neutral, r.ternary.negative,
                    1 if r.ternary.positive > r.ternary.negative else
                    (-1 if r.ternary.negative > r.ternary.positive else 0)
                )
            )
        except Exception:
            pass
    conn.commit()


def build_staging_factcrystal(query: str) -> FactCrystal:
    """降级: staging 事实晶体（当真实搜索不可用时）"""
    entities = [
        Entity(id="E1", name="上证指数", type="market", value=3400, trend="+1",
               stance="0", confidence=2, temporal_window="medium",
               discovered_by=["Q02", "Q04"],
               opposite_bridges=[],
               bridge_coverage=2,
               projections=["区间震荡"]),
        Entity(id="E2", name="降准", type="policy",
               stance="+1", confidence=2, temporal_window="short",
               discovered_by=["Q02", "Q04"],
               opposite_bridges=["Q08"],
               bridge_coverage=3, trend="+1",
               projections=["宽松周期开启"]),
        Entity(id="E3", name="PMI", type="indicator", value=50.8, trend="+1",
               stance="0", confidence=2, temporal_window="short",
               discovered_by=["Q02"],
               opposite_bridges=[],
               bridge_coverage=1,
               projections=["短期稳定"]),
    ]
    relations = [
        Relation(from_entity="E2", to_entity="E1", type="causal",
                 ternary=TernaryDistribution(positive=3, neutral=1, negative=1)),
        Relation(from_entity="E3", to_entity="E1", type="correlation",
                 ternary=TernaryDistribution(positive=2, neutral=1, negative=0)),
    ]
    temporal = {
        "medium": TemporalWindow(entities=[{"id":"E1","value":3200,"trend":"0"}], dominant_trend="区间震荡"),
    }
    return FactCrystal(query=query, entities=entities, relations=relations, temporal=temporal,
                    sources=[{"type":"staging"}],
                    completeness={"blinds":["真实搜索不可用·staging降级"], "active_bridges": ["Q02", "Q04"], "total_bridges": 11, "layers": 1},
                    prechecks={},
                    bridge_conflicts=[],
                    structured_summary=f"staging事实晶体：{query[:50]}")


def build_factcrystal(query: str, conn=None, search_results: list[dict] = None,
                      enable_spiral: bool = True) -> FactCrystal:
    """
    构建事实晶体——v7.1增强管线。

    调用链路（v6.5对齐）:
      search_entry → proposition_analyzer (拆解+桥映射+共振)
        → EnhancedSearchRouter (L1-FTS/L2-图谱/L3-三力/L4-分歧力)
        → entity_extractor → temporal_slicer → FourLensPrecheck
        → SpiralEnricher (多轮盲区补全+置信度重算+收敛判定)
    """
    if conn:
        try:
            # 阶段1: 搜索入口 + 命题分析
            entry = SearchEntry(conn)
            entry_result = entry.process(query, enable_oppose=True)
            graph = entry_result.get("graph", {})

            # 使用增强搜索路由（如果外部未提供search_results）
            if search_results is None or len(search_results) == 0:
                router = EnhancedSearchRouter(conn)
                search_results_raw = router.search_and_format(query, max_results=40)
            else:
                search_results_raw = [
                    {"title": r.get("title",""), "content": r.get("content","")[:500],
                     "source": r.get("source","external"), "relevance": r.get("relevance",0.5)}
                    for r in (search_results or [])
                ]

            # 合并命题分析桥信息到search_results
            if graph:
                for b in graph.get("bridges", []):
                    search_results_raw.append({
                        "title": f"[桥] {b.get('bridge_id','')} ({b.get('layer','')})",
                        "content": f"桥映射: {b.get('bridge_id','')} 层={b.get('layer','')} "
                                   f"命中数={b.get('hit_count',0)} 共振深度={b.get('resonance_depth',0)}",
                        "source": "bridge_mapping",
                        "relevance": 1.0 if b.get("hit_level") == 1 else 0.5,
                    })

            if search_results_raw and len(search_results_raw) > 0:
                extractor = BridgeAwareEntityExtractor(conn)
                entities, entity_blinds = extractor.extract(
                    search_results_raw, query, max_entities=50)
                relations = extractor.extract_ternary_relations(entities)

                slicer = TemporalSlicer()
                temporal = slicer.slice(entities, relations, search_results_raw)

                precheck = FourLensPrecheck(conn)
                checks = precheck.run(entities, relations, temporal)
                if entity_blinds and checks.get("completeness"):
                    checks["completeness"]["blinds"].extend(entity_blinds)

                fc = FactCrystal(
                    query=query, entities=entities, relations=relations,
                    temporal=temporal,
                    sources=[{"type": "search", "count": len(search_results_raw)},
                             {"type": "graph", "data": graph}],
                    completeness=checks.get("completeness", {}),
                    prechecks=checks.get("prechecks", {}),
                )

                # 阶段2: 螺旋补全（v6.5对齐）
                if enable_spiral and conn:
                    try:
                        router = EnhancedSearchRouter(conn)
                        enricher = SpiralEnricher(conn=conn, search_router=router)
                        fc = enricher.enrich(fc, query, max_rounds=3)
                        if fc.convergence_reason:
                            print(f"  → 螺旋补全: {len(fc.enrichment_history)}轮, {fc.convergence_reason}")
                        # 更新completeness的active_bridges
                        active = set()
                        for e in fc.entities:
                            for b in e.discovered_by:
                                if b[:3].startswith("Q"):
                                    active.add(b[:3])
                        fc.completeness["active_bridges"] = list(active)
                        fc.completeness["total_bridges"] = 11
                    except Exception as e:
                        print(f"  → 螺旋补全跳过: {e}")

                _write_ternary_edges(conn, fc)
                return fc
        except Exception as e:
            print(f"  → build_factcrystal降级: {e}")
            pass

    return build_staging_factcrystal(query)
