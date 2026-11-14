"""Add symptoms, synonyms and symptom -> specialty rules from a JSON catalog file.

    python -m app.commands.seed_symptom_catalog --dry-run   # show what would change
    python -m app.commands.seed_symptom_catalog             # apply (one transaction)
    python -m app.commands.seed_symptom_catalog --file other_hospital.json

Additive and idempotent: a symptom is matched by name (case-insensitive) and only what is
missing is added - new symptoms, new synonyms, new rules. Nothing is deleted, existing
rule weights, red flags and admin edits are kept. Only the backend's own tables are
touched (symptoms, symptom_specialty_rules, then the AI search index); the ERP-owned
directory (hospitals, specialties, departments, doctors, slots) is only read.
"""

import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import func, select

from app.core.db import SessionLocal, engine
from app.models import Specialty, Symptom, SymptomSpecialtyRule
from app.services import search_index

DEFAULT_FILE = Path(__file__).resolve().parents[1] / "seed_data" / "symptom_catalog_extra.json"
KEYWORDS_MAX = 500  # symptoms.keywords column size


def _split(keywords: str | None) -> list[str]:
    return [k.strip() for k in (keywords or "").split(",") if k.strip()]


async def apply(path: Path, dry_run: bool) -> dict[str, int]:
    entries = json.loads(path.read_text(encoding="utf-8"))["symptoms"]
    stats = {"symptoms_added": 0, "synonyms_added": 0, "rules_added": 0, "warnings": 0}
    async with SessionLocal() as session:
        specialties = {s.name.lower(): s for s in (await session.scalars(select(Specialty))).all()}
        for entry in entries:
            name = entry["name"].strip()
            symptom = await session.scalar(
                select(Symptom).where(func.lower(Symptom.name) == name.lower())
            )
            if symptom is None:
                symptom = Symptom(
                    name=name,
                    keywords="",
                    description=entry.get("description"),
                    is_red_flag=bool(entry.get("red_flag_message")),
                    red_flag_message=entry.get("red_flag_message"),
                )
                session.add(symptom)
                await session.flush()
                stats["symptoms_added"] += 1
                print(f"+ symptom   {name}" + ("  [warning sign]" if symptom.is_red_flag else ""))

            current = _split(symptom.keywords)
            known = {k.lower() for k in current} | {symptom.name.lower()}
            added = [k for k in entry.get("keywords", []) if k.strip().lower() not in known]
            merged = ",".join(current + added)
            if len(merged) > KEYWORDS_MAX:
                stats["warnings"] += 1
                print(f"! synonyms  {name}: over {KEYWORDS_MAX} characters, extra ones skipped")
                while added and len(",".join(current + added)) > KEYWORDS_MAX:
                    added.pop()
                merged = ",".join(current + added)
            if added:
                symptom.keywords = merged
                stats["synonyms_added"] += len(added)
                print(f"+ synonyms  {name}: {', '.join(added)}")

            for specialty_name, weight in entry.get("rules", []):
                specialty = specialties.get(specialty_name.lower())
                if specialty is None:
                    stats["warnings"] += 1
                    print(f"! rule      {name} -> {specialty_name}: no such specialty, skipped")
                    continue
                rule = await session.scalar(
                    select(SymptomSpecialtyRule).where(
                        SymptomSpecialtyRule.symptom_id == symptom.id,
                        SymptomSpecialtyRule.specialty_id == specialty.id,
                    )
                )
                if rule is None:
                    session.add(
                        SymptomSpecialtyRule(
                            symptom_id=symptom.id, specialty_id=specialty.id, weight=weight
                        )
                    )
                    stats["rules_added"] += 1
                    print(f"+ rule      {name} -> {specialty.name} ({weight})")

        if dry_run:
            await session.rollback()
            print("dry run: nothing was saved")
        else:
            await session.commit()
            if await search_index.sync_index(session):
                print("AI search index updated")
            else:
                print("AI search index not updated now; the background job retries within a minute")
    return stats


async def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    stats = await apply(args.file, args.dry_run)
    await engine.dispose()
    print(" ".join(f"{k}={v}" for k, v in stats.items()))


if __name__ == "__main__":
    asyncio.run(main())
