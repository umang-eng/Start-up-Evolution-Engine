"""Shadow-mode validation script for Agent Mesh.

Compares AgentModule output against existing baseline results
for each project that has historical data.

Run inside Docker: docker exec see-worker-engine python /app/scripts/shadow_validate.py
"""

import asyncio
import json
import os
import sys
import time

# Ensure correct env inside container
os.environ.setdefault("POSTGRES_HOST", "postgres")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "postgres")
os.environ.setdefault("POSTGRES_PASSWORD", "postgres")
os.environ.setdefault("POSTGRES_DB", "startup_evolution")

sys.path.insert(0, "/app")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database.session import AsyncSessionLocal
from backend.models.project import Project
from backend.models.results import DNAResult
from backend.agents.module import AgentModule
from backend.agents.config import AGENT_MESH_CONFIG
from backend.core.logging import logger


async def get_projects_with_dna(db: AsyncSession) -> list[Project]:
    """Get all projects that have existing DNA results."""
    stmt = (
        select(Project)
        .options(selectinload(Project.dna_result))
        .order_by(Project.created_at.desc())
    )
    projects = (await db.execute(stmt)).scalars().all()
    return [p for p in projects if p.dna_result is not None]


async def run_shadow_validation():
    """Run AgentModule on projects with baseline DNA and compare."""
    print("=" * 70)
    print("SHADOW MODE VALIDATION — DNA Stage")
    print("=" * 70)

    # Enable DNA agent mesh temporarily
    AGENT_MESH_CONFIG["dna"].enabled = True
    agent_module = AgentModule("dna")

    results = []

    async with AsyncSessionLocal() as db:
        projects = await get_projects_with_dna(db)
        print(f"\nFound {len(projects)} projects with baseline DNA results\n")

        for i, project in enumerate(projects, 1):
            baseline = project.dna_result.data
            print(f"[{i}/{len(projects)}] {project.title}")
            print(f"  Baseline scores: {baseline.get('scores', {})}")

            start = time.monotonic()
            try:
                agent_output = await agent_module.run(
                    db=db,
                    project=project,
                    context={},
                )
                elapsed = time.monotonic() - start

                # Compare
                baseline_scores = baseline.get("scores", {})
                agent_scores = agent_output.get("scores", {})
                score_deltas = {}
                for key in baseline_scores:
                    if key in agent_scores:
                        delta = agent_scores[key] - baseline_scores[key]
                        score_deltas[key] = delta

                schema_match = set(baseline.keys()) == set(agent_output.keys())
                avg_abs_delta = (
                    sum(abs(v) for v in score_deltas.values()) / len(score_deltas)
                    if score_deltas else 0
                )

                status = "PASS" if schema_match and avg_abs_delta < 20 else "REVIEW"
                results.append({
                    "project": project.title,
                    "schema_match": schema_match,
                    "score_deltas": score_deltas,
                    "avg_abs_delta": round(avg_abs_delta, 1),
                    "elapsed_s": round(elapsed, 1),
                    "status": status,
                })

                print(f"  Agent scores: {agent_scores}")
                print(f"  Score deltas: {score_deltas}")
                print(f"  Schema match: {schema_match} | Avg delta: {avg_abs_delta:.1f} | {status} | {elapsed:.1f}s\n")

            except Exception as e:
                elapsed = time.monotonic() - start
                print(f"  ERROR: {e} ({elapsed:.1f}s)\n")
                results.append({
                    "project": project.title,
                    "status": "ERROR",
                    "error": str(e),
                    "elapsed_s": round(elapsed, 1),
                })

    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in results if r["status"] == "PASS")
    reviewed = sum(1 for r in results if r["status"] == "REVIEW")
    errors = sum(1 for r in results if r["status"] == "ERROR")
    print(f"  PASS:    {passed}/{len(results)}")
    print(f"  REVIEW:  {reviewed}/{len(results)}")
    print(f"  ERROR:   {errors}/{len(results)}")

    avg_time = sum(r["elapsed_s"] for r in results) / len(results) if results else 0
    print(f"  Avg time: {avg_time:.1f}s per project")

    if passed == len(results):
        print("\n  All projects passed. Safe to enable agent mesh for DNA stage.")
    elif reviewed > 0:
        print(f"\n  {reviewed} projects need manual review before enabling.")
    else:
        print("\n  All projects passed (no reviews needed).")

    # Disable DNA agent mesh again
    AGENT_MESH_CONFIG["dna"].enabled = False

    return results


if __name__ == "__main__":
    asyncio.run(run_shadow_validation())
