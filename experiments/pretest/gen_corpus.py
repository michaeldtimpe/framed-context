#!/usr/bin/env python3
"""Deterministic grep-resistant synthesis corpus for the docs-mode test.

40 synthetic field-station operations notes (~5k chars each). Two seeded
concepts, each phrased differently in every occurrence with no shared stem,
plus keyword decoys — so keyword search finds decoys, and exhaustive
identification requires actually reading the notes.

Deterministic (fixed seed): same corpus and same ground truth everywhere.
Run: python3 gen_corpus.py  -> writes corpus/notes/*.md, prints ground truth.
"""
import random
from pathlib import Path

OUT = Path(__file__).resolve().parent / "corpus"
N_NOTES = 40
rng = random.Random(2026_07_28)

# concept 1: financial overrun — 7 notes, unique phrasing, no shared stem,
# none contain the words budget/cost/overrun/exceed
OVERRUN = [
    "Quarter close was uncomfortable: outlays surpassed the earmarked funds, and the ledger review with head office is going to be tense.",
    "Final invoices from the freight contractor pushed the station past its approved financial envelope for the period.",
    "Monies consumed this period outstripped the appropriation; we are drafting the variance memo now.",
    "The quarter's disbursements overshot what the plan allowed, mostly on emergency fuel purchases.",
    "Expenditure for the season finished well above the allocation, driven by the second resupply run.",
    "We closed the books beyond the sanctioned figure and will need head office to ratify the difference.",
    "The ledger landed north of the authorized ceiling once the generator parts cleared customs.",
]
# concept 2: corrosion-caused equipment failure — 5 notes, unique phrasing
CORROSION = [
    "The transfer pump is out of service: rust had eaten through the housing wall and the impeller seized.",
    "Radio checks failed twice this week; oxidation had compromised the relay contacts in the transmitter cabinet.",
    "Salt air finally won — the antenna mounts degraded to the point of structural failure and the mast is down.",
    "The backup generator would not start; its terminals were green with verdigris and crumbled under the clamp.",
    "Teardown of the winch revealed pitting from trapped moisture had ruined the main bearing race.",
]
# decoys: contain the obvious keywords (budget/cost/failure) in NON-matching contexts
DECOYS = [
    "The supply contract came in comfortably under budget this cycle, a rare piece of good news.",
    "Cost savings from the new fuel supplier freed up funds for the lab refit.",
    "The annual budget review meeting is scheduled for the first week of next month.",
    "The winch failed after an electrical fault in the controller; the mechanism itself is sound.",
    "Impact damage from the sling load cracked the compressor housing; no other cause found.",
    "Wiring insulation failed from prolonged UV exposure on the roof run.",
    "A software fault caused the datalogger failure; hardware checked out fine.",
    "We reviewed projected costs for next season and they look manageable.",
    "The overrun on the runway extension schedule (three weeks late) has no financial impact.",
    "Preventive maintenance kept the fleet failure-free for the whole period.",
]

WEATHER = [
    "Winds held steady from the southwest at 15 to 25 knots for most of the week.",
    "A low ceiling and freezing drizzle kept the helipad closed on two mornings.",
    "Clear skies and a hard frost overnight; the met balloon launches went off on schedule.",
    "Fog banks rolled in each evening and burned off by mid-morning.",
    "An unseasonal warm spell softened the access track and slowed vehicle movements.",
    "Squalls passed through on three separate days, none causing damage.",
    "Visibility stayed above ten kilometres all week, a welcome change.",
    "Overnight lows dipped sharply and the water line heaters ran continuously.",
]
OPS = [
    "The morning generator changeover went smoothly and load tests were nominal.",
    "We rotated the fuel stock and dipped all tanks; readings matched the log within tolerance.",
    "The science team completed the transect survey ahead of schedule.",
    "Routine inspection of the jetty found the fenders serviceable for another season.",
    "The workshop finished fabricating the replacement bracket for the met mast.",
    "Waste consolidation for the next retrograde shipment is ninety percent complete.",
    "The comms schedule with the coastal relay was kept without interruption.",
    "Vehicle plant hours were logged and the loader is due its two-hundred-hour service.",
    "The desalination plant ran at reduced output while filters were swapped.",
    "Stores completed the mid-season stocktake; discrepancies were minor.",
]
PERSONNEL = [
    "Morale remains good; the film night and quiz were well attended.",
    "One member of the team is on light duties after a minor ankle sprain.",
    "The doctor ran the quarterly first-aid refresher for all hands.",
    "Two staff completed their working-at-heights recertification.",
    "The chef's resupply wish list has been forwarded to logistics.",
    "Handover notes for the incoming plumber were drafted and reviewed.",
    "A birthday was celebrated with the traditional station dinner.",
    "The field training officer signed off three staff on sea-ice travel.",
]
SUPPLY = [
    "The resupply vessel is confirmed for the window at the end of the month.",
    "Fresh provisions are holding out; greens will be exhausted in two weeks.",
    "Spare filter elements for the desalinator arrived with the last airdrop.",
    "The medical resupply was checked and locked into the pharmacy store.",
    "Cement and timber for the hide refurbishment are staged on the jetty.",
    "Two drums of glycol were decanted and moved to the heated store.",
    "The stationery order was the only shortfall in the last consignment.",
]

def build():
    notes = {}
    ids = [f"note-{i:03d}" for i in range(1, N_NOTES + 1)]
    special = rng.sample(ids, len(OVERRUN) + len(CORROSION) + len(DECOYS))
    overrun_ids = sorted(special[:len(OVERRUN)])
    corrosion_ids = sorted(special[len(OVERRUN):len(OVERRUN) + len(CORROSION)])
    decoy_ids = special[len(OVERRUN) + len(CORROSION):]
    inserts = {}
    for nid, s in zip(overrun_ids, rng.sample(OVERRUN, len(OVERRUN))):
        inserts[nid] = s
    for nid, s in zip(corrosion_ids, rng.sample(CORROSION, len(CORROSION))):
        inserts[nid] = s
    for nid, s in zip(decoy_ids, rng.sample(DECOYS, len(DECOYS))):
        inserts[nid] = s

    for i, nid in enumerate(ids):
        week = i + 1
        paras = []
        paras.append(f"# {nid}: Station operations log, week {week}\n")
        for pool, label in [(WEATHER, "Weather"), (OPS, "Operations"),
                            (PERSONNEL, "Personnel"), (SUPPLY, "Supply")]:
            body = " ".join(rng.choices(pool, k=8))
            paras.append(f"## {label}\n\n{body}\n")
        sections = paras[1:]
        rng.shuffle(sections)
        note = paras[0] + "\n" + "\n".join(sections)
        if nid in inserts:
            parts = note.split("\n\n")
            pos = rng.randrange(2, len(parts))
            parts.insert(pos, inserts[nid])
            note = "\n\n".join(parts)
        combined = OPS + WEATHER + SUPPLY + PERSONNEL
        for j in range(3):
            filler = " ".join(rng.choices(combined, k=10))
            note += f"\n\n## Daily entries, part {j + 1}\n\n{filler}\n"
        notes[nid] = note

    outdir = OUT / "notes"
    outdir.mkdir(parents=True, exist_ok=True)
    for nid, text in notes.items():
        (outdir / f"{nid}.md").write_text(text)
    (OUT / "README.md").write_text(
        "# Station logs corpus\n\nSynthetic operations notes in notes/. "
        "Generated by gen_corpus.py (deterministic).\n")
    total = sum(len(t) for t in notes.values())
    print(f"wrote {len(notes)} notes, {total} chars total")
    print("OVERRUN  =", ",".join(overrun_ids))
    print("CORROSION=", ",".join(corrosion_ids))
    return overrun_ids, corrosion_ids


if __name__ == "__main__":
    build()
