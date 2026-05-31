#!/usr/bin/env python3
"""Add UK/EU/US primary regulatory sources flagged as TODO in §2.8."""
from __future__ import annotations
import json
from pathlib import Path

REG = Path(__file__).parent / "registry.json"
SOURCE_PROMPT = "lit-review-uk-eu-primary"

# (tag, title, year, url, source_type, category, relevance)
ENTRIES = [
    ("ofqual-2020",
     "Ofqual, Awarding GCSE, AS, A level, advanced extension awards and extended project qualifications in summer 2020 (interim report and Direction)",
     2020,
     "https://www.gov.uk/government/publications/awarding-gcse-as-a-level-advanced-extension-awards-and-extended-project-qualifications-in-summer-2020-interim-report",
     "Government policy", "a",
     "UK Ofqual A-level standardisation algorithm 2020; first major UK public-sector algorithmic-fairness reversal (centre-assessed grades reinstated 17 August 2020)."),
    ("syri-court-hague-2020",
     "NJCM et al. v. The Netherlands (Systeem Risico Indicatie / SyRI judgment), Court of The Hague, ECLI:NL:RBDHA:2020:865, 5 February 2020",
     2020,
     "https://uitspraken.rechtspraak.nl/details?id=ECLI:NL:RBDHA:2020:865",
     "Judgment", "a",
     "First European court ruling to strike down a public-sector algorithm on human-rights grounds (Article 8 ECHR); establishes proportionality as operative judicial test."),
    ("amazon-recruit-2018",
     "Dastin, J., 'Amazon scraps secret AI recruiting tool that showed bias against women', Reuters, 10 October 2018",
     2018,
     "https://www.reuters.com/article/world/insight-amazon-scraps-secret-ai-recruiting-tool-that-showed-bias-against-women-idUSKCN1MK0AG/",
     "Journalism", "b",
     "Amazon internal recruiting tool encoded gender bias from male-dominated training data; canonical industry abandonment case."),
    ("chicago-ssl-oig-2020",
     "Chicago Office of Inspector General, Advisory Concerning the Chicago Police Department's Predictive Risk Models (Strategic Subject List)",
     2020,
     "https://igchicago.org/wp-content/uploads/2020/01/OIG-Advisory-Concerning-CPDs-Predictive-Risk-Models-.pdf",
     "Operator report", "a",
     "Retrospective audit of Chicago Strategic Subject List predictive-policing scores; documents racially disparate outcomes relative to predictive validity."),
    ("nyc-ads-task-force-2019",
     "New York City Automated Decision Systems Task Force, Report (Local Law 49 of 2018)",
     2019,
     "https://www.nyc.gov/assets/adstaskforce/downloads/pdf/ADS-Report-11192019.pdf",
     "Government policy", "a",
     "NYC ADS Task Force could not produce public inventory of deployed systems; transparency mechanism collapsed internally rather than through judicial challenge."),
    ("equality-act-2010-psed",
     "Equality Act 2010, Section 149: Public Sector Equality Duty (UK)",
     2010,
     "https://www.legislation.gov.uk/ukpga/2010/15/section/149",
     "Statute", "a",
     "Statutory duty on UK public authorities to have due regard to advancing equality of opportunity in the exercise of their functions; applicable to TfL and other public-sector signal-control operators."),
    ("eu-ai-act-2024",
     "Regulation (EU) 2024/1689 of the European Parliament and of the Council of 13 June 2024 laying down harmonised rules on artificial intelligence (Artificial Intelligence Act)",
     2024,
     "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX%3A32024R1689",
     "Statute", "a",
     "EU AI Act: Annex III §2 classifies AI in road traffic management as high-risk; Article 12 mandates automatic event logging; high-risk obligations effective 2 August 2026."),
    ("uk-atrs",
     "UK Algorithmic Transparency Recording Standard (ATRS), Cabinet Office and Central Digital and Data Office",
     2023,
     "https://www.gov.uk/government/collections/algorithmic-transparency-recording-standard-hub",
     "Government policy", "a",
     "ATRS Tier 1 (public-facing short summary) and Tier 2 (detailed template covering data inputs, model type, outputs, equality impacts) — UK reporting templates for public-sector algorithmic systems."),
    ("bridges-v-swp-2020",
     "R (Bridges) v Chief Constable of South Wales Police [2020] EWCA Civ 1058",
     2020,
     "https://www.bailii.org/ew/cases/EWCA/Civ/2020/1058.html",
     "Judgment", "a",
     "First UK appellate ruling on public-sector facial-recognition deployment; Equality Act PSED s.149 breach found because no equality impact assessment had preceded deployment."),
    ("schufa-cjeu-2023",
     "Schufa Holding AG (Case C-634/21), Court of Justice of the European Union, judgment of 7 December 2023, ECLI:EU:C:2023:957",
     2023,
     "https://curia.europa.eu/juris/document/document.jsf?docid=280426&doclang=EN",
     "Judgment", "a",
     "CJEU held Article 22 GDPR (right against solely automated decisions) applies to algorithmic credit scoring even where a human caseworker is nominal decision-maker; closes human-in-the-loop escape route."),
    ("nchrp-969-2021",
     "Transportation Research Board, NCHRP Report 969: Improving Pedestrian Safety at Signalized Intersections",
     2021,
     "https://nap.nationalacademies.org/catalog/26095/improving-pedestrian-safety-at-signalized-intersections",
     "Government policy", "a",
     "Documents that standard signal-timing software treats pedestrian phase design as geometric-capacity question rather than delay-minimisation objective; pedestrian wait time absent from optimisation objective functions."),
    ("dangerous-by-design-2024",
     "Smart Growth America, Dangerous by Design 2024",
     2024,
     "https://smartgrowthamerica.org/dangerous-by-design/",
     "Operator report", "b",
     "US pedestrian fatality rates four times higher in low-income census tracts than in tracts with median incomes above $100,000; attributed in part to signal timing optimised for vehicle throughput in lower-income areas."),
    ("tfl-ksi-2023",
     "Transport for London, Casualties in Greater London during 2022 (Statistical Release, April 2023)",
     2023,
     "https://content.tfl.gov.uk/casualties-in-greater-london-2022.pdf",
     "Operator report", "a",
     "TfL's KSI (killed-or-seriously-injured) statistics; residents in the most deprived London postcodes face nearly double the road-collision KSI risk of those in the least deprived."),
]


def main() -> None:
    reg = json.loads(REG.read_text(encoding="utf-8"))
    existing_tags = {p["tag"] for p in reg["papers"]}
    added = 0
    skipped = 0
    for tag, title, year, url, source_type, category, relevance in ENTRIES:
        if tag in existing_tags:
            skipped += 1
            print(f"  SKIP (exists): {tag}")
            continue
        reg["papers"].append({
            "tag": tag,
            "title": title,
            "year": year,
            "url": url,
            "source_prompt": SOURCE_PROMPT,
            "source_type": source_type,
            "category": category,
            "relevance": relevance,
            "status": "external_reference",
            "filename": None,
            "size_bytes": None,
            "sha256": None,
            "http_status": None,
            "downloaded_at": None,
            "error": None,
        })
        existing_tags.add(tag)
        added += 1
        print(f"  +  {tag}")
    REG.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nadded {added}; skipped {skipped}; total entries now {len(reg['papers'])}")


if __name__ == "__main__":
    main()
