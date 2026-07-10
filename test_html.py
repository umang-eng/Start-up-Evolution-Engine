import asyncio
from backend.exports.export import export_compiler

blueprint_data = {
    "executive_summary": {"startup_name": "Test Startup", "vision": "Vision", "summary": "Summary"},
    "dna": {"category": "Cat", "business_model": "BM", "target_market": "Market", "strategic_vectors_score": 90},
    "features": {"total_features": 1, "complexity_score": "low", "features": [{"name": "F1", "description": "D1", "priority": "high"}]},
    "team": {"recommended_team_size": 2, "org_chart": [{"title": "CEO", "department": "EXEC", "estimated_salary_usd": 100000, "responsibilities": ["Lead"]}]},
    "swot": {"strengths": ["S1"], "weaknesses": ["W1"], "opportunities": ["O1"], "threats": ["T1"], "mitigations": [], "founder_actions": []},
    "cost": {"funding_requirements": {"minimum_target_usd": 100000}, "cash_runway_calculations": {"estimated_runway_months": 12}, "operational_costs": []}
}

try:
    html = export_compiler.compile_blueprint_to_html(blueprint_data)
    print("HTML Length:", len(html))
except Exception as e:
    import traceback
    traceback.print_exc()

try:
    deck = export_compiler.compile_blueprint_to_deck(blueprint_data)
    print("Deck generated:", bool(deck))
except Exception as e:
    import traceback
    traceback.print_exc()
