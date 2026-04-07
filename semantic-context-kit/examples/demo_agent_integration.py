"""Demo: SemanticContextKit integrated with an Agent workflow.

Shows how the kit provides domain context at each Agent stage:
  Reasoner → knowledge_brief (auto-inject domain vision)
  Planner  → experience_recall (historical reference)
  Actor    → lookup (on-demand facts)
  Observer → risk_check (constraint checklist)

Usage:
    # Make sure the big platform is running at localhost:8000
    python examples/demo_agent_integration.py
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logging.basicConfig(level=logging.INFO, format="%(message)s")

from semantic_context_kit import SemanticContextKit


def main():
    print("=" * 70)
    print("SemanticContextKit — Agent Integration Demo")
    print("=" * 70)

    # ── Step 1: Load domain view from platform ──────────────────
    print("\n[1] Loading domain view from platform...")
    try:
        kit = SemanticContextKit.from_platform(
            "http://localhost:8000",
            keywords=["BGP", "OSPF", "VXLAN", "MPLS", "BFD", "VRRP"],
            max_nodes=200,
        )
    except Exception as exc:
        print(f"  Platform not available ({exc}), loading from sample file...")
        sample = Path(__file__).parent / "sample_domain_view.json"
        if sample.exists():
            kit = SemanticContextKit.from_file(sample)
        else:
            print("  No sample file either. Run the platform first.")
            return

    print(f"  {kit.summary()}")

    # ── Step 2: Simulate Agent Reasoner ─────────────────────────
    print("\n" + "=" * 70)
    print("[2] REASONER STAGE: 'What do I need to know?'")
    print("=" * 70)

    goal = "Design a dual-exit campus network with OSPF and BGP"
    print(f"\n  Goal: {goal}")

    # Auto-annotate the goal
    tags = kit.annotate(goal)
    print(f"\n  Detected concepts: {[f'{t.surface_form}({t.node_id})' for t in tags]}")

    # Get knowledge brief
    brief = kit.knowledge_brief(goal)
    print(f"\n  Knowledge Brief:")
    print(f"    Concepts: {[c['name'] for c in brief.get('concepts', [])]}")
    print(f"    Methods:  {[m['name'] for m in brief.get('methods', [])]}")
    print(f"    Conditions: {[c['name'] for c in brief.get('conditions', [])]}")
    print(f"    Scenarios: {[s['name'] for s in brief.get('scenarios', [])]}")
    print(f"    Risks: {len(brief.get('risks', []))}")
    print(f"    Evidence: {len(brief.get('evidence', []))}")

    # ── Step 3: Simulate Agent Planner ──────────────────────────
    print("\n" + "=" * 70)
    print("[3] PLANNER STAGE: 'How was this done before?'")
    print("=" * 70)

    exp = kit.experience_recall("OSPF area design")
    print(f"\n  Best practices: {len(exp.get('best_practices', []))}")
    for bp in exp.get("best_practices", [])[:3]:
        print(f"    - {bp.get('name', '?')}: {bp.get('description', '')[:80]}")
    print(f"  Lessons: {len(exp.get('lessons', []))}")

    # Reasoning chain
    print("\n  Five-layer reasoning chain for OSPF:")
    chain = kit.reasoning_chain("OSPF")
    for layer, nodes in (chain.get("layers") or {}).items():
        for n in nodes:
            print(f"    [{layer}] {n['name']} — {n.get('relation', '')}")

    # ── Step 4: Simulate Agent Actor ────────────────────────────
    print("\n" + "=" * 70)
    print("[4] ACTOR STAGE: 'Look up specific facts'")
    print("=" * 70)

    for term in ["BGP", "OSPF", "BFD"]:
        info = kit.lookup(term)
        if "error" not in info:
            node = info["node"]
            print(f"\n  {node['name']} ({node['node_id']}):")
            print(f"    Layer: {node['layer']}")
            print(f"    Description: {node['description'][:100]}")
            print(f"    Relations: {len(info['relations'])}")
            print(f"    Evidence: {len(info['evidence'])}")

    # ── Step 5: Simulate Agent Observer ─────────────────────────
    print("\n" + "=" * 70)
    print("[5] OBSERVER STAGE: 'What's wrong with this plan?'")
    print("=" * 70)

    check = kit.risk_check(
        selected=["BGP", "OSPF", "VRRP"],
        scenario="dual-exit campus with high availability",
    )
    print(f"\n  Selected: {check.get('selected', [])}")
    print(f"  Conflicts: {len(check.get('conflicts', []))}")
    for c in check.get("conflicts", []):
        print(f"    - {c['a']} vs {c['b']}: {c['relation']}")
    print(f"  Risks: {len(check.get('risks', []))}")
    for r in check.get("risks", [])[:3]:
        print(f"    - {r.get('condition', '?')}: {r.get('description', '')[:80]}")
    print(f"  Missing: {len(check.get('missing', []))}")
    for m in check.get("missing", []):
        print(f"    - {m['suggestion']}: {m['reason']}")
    print(f"  Dependency gaps: {len(check.get('dependency_gaps', []))}")
    for d in check.get("dependency_gaps", [])[:3]:
        print(f"    - {d['node']} needs {d['missing_dependency']}")

    # ── Step 6: Learn from project ──────────────────────────────
    print("\n" + "=" * 70)
    print("[6] LEARNING: Accumulate project knowledge")
    print("=" * 70)

    kit.learn("Selected OSPF multi-area for backbone due to 500+ devices",
              item_type="decision")
    kit.learn("BFD timer set to 100ms for fast failover",
              item_type="decision")
    kit.learn("Asymmetric routing occurred when BGP MED was not configured",
              item_type="lesson")
    kit.learn_term("Super Spine", parent="IP.SPINE_LEAF",
                   description="Top-tier switch in 3-tier Spine-Leaf fabric")

    export = kit.export_learned()
    print(f"\n  Accumulated: {export['stats']}")
    print(f"  Ready for backfeed to platform")

    # Save to file
    output_path = Path(__file__).parent / "learned_output.json"
    kit.save_learned(output_path)
    print(f"  Saved to: {output_path}")

    print("\n" + "=" * 70)
    print("Demo complete.")
    print("=" * 70)


if __name__ == "__main__":
    main()
