# UK Traffic Law: Fault Attribution at Signal-Controlled Junctions — Structured Knowledge Base for a Traffic-Simulation Model

*(Research reference for an academic simulation model of a signalised junction on Euston Road (A501), London. NOT legal advice.)*

## TL;DR
- Fault in the model resolves along three axes with different evidential strength: (a) **driver fault** is anchored in hard statutory duties — running a red is a criminal offence under RTA 1988 s.36 read with TSRGD 2016 Schedule 14 Part 1 para 5(3), attracting a £100 fixed penalty and three penalty points (offence code TS10), rising to a fine of up to £1,000 on prosecution; (b) **signal-authority ("AI") fault** is legally *weak and unsettled* — under Gorringe v Calderdale [2004] UKHL 15 an authority is generally NOT liable for failing to sign/warn (nonfeasance), but CAN be liable for *misfeasance* (creating a trap, e.g. conflicting green signals) per Bird v Pearce; in London the authority is **Transport for London**, which operates circa 6,400 traffic-signal junctions across the Greater London boundary; (c) **emergency-vehicle fault** turns on a conditional exemption — blue-light vehicles may treat red as give-way (TSRGD 2016 Sch 14 Pt 1 para 5(4)-(6)) but still owe a duty of care (Griffin v Mersey, Keyse v Commissioner).
- The model must distinguish **"MUST/MUST NOT" rules** (backed by legislation → breach is an offence and strong evidence of negligence) from **"should" advisory rules** (Highway Code guidance → not an offence, but admissible under RTA 1988 s.38(7) to establish or negate civil/criminal liability).
- Apportionment uses negligence (duty/breach/causation), reduced for contributory negligence (Law Reform (Contributory Negligence) Act 1945 s.1) and split between multiple wrongdoers (Civil Liability (Contribution) Act 1978 s.1); a canonical benchmark is Griffin v Mersey (green-light driver 60% contributorily negligent vs red-light ambulance).

## Key Findings
1. Red-light running is both a criminal offence (RTA 1988 s.36 + TSRGD) and near-conclusive of driver fault in a collision, because the red signal's legal meaning is a *prohibition* on proceeding beyond the stop line.
2. Emergency vehicles (fire, ambulance, blood, NHS-tasked, bomb disposal, special forces, police, National Crime Agency) have an *express* red-light exemption in TSRGD 2016, but it is conditional on not endangering others — so an emergency vehicle CAN still be at fault.
3. Highway maintenance / works vehicles do **not** get the red-light exemption; they are not "emergency vehicles" for that purpose.
4. Authority liability for a malfunctioning signal is the legally thinnest area. The safe modelling rule: no liability for mere failure/omission; potential liability only where the authority positively created a dangerous, misleading state (conflicting greens).
5. Ordinary drivers MUST NOT break the law to give way to an emergency vehicle (Highway Code Rule 219) — so a driver who runs a red to clear the way is still at fault.

## Details

### AREA 1 — Obeying traffic signals (duty to stop at red)

```
{
  id: "RTA1988-s36",
  source: "Road Traffic Act 1988, s.36 (1988 c.52)",
  plain_language: "A driver who fails to comply with the indication of a lawfully-placed prescribed traffic sign (which includes traffic light signals) commits a criminal offence.",
  binds: "driver",
  fault_if_violated: "Driver at fault. Fixed penalty: £100 fine + three penalty points + offence code TS10; on prosecution the fine can reach £1,000. Traffic lights are 'signs' to which s.36 applies via the Traffic Signs Regulations."
}
```

```
{
  id: "TSRGD2016-Sch14-Pt1-para5(3)",
  source: "Traffic Signs Regulations and General Directions 2016, Schedule 14 Part 1 para 5(3) (SI 2016/362)",
  plain_language: "The red signal conveys the prohibition that vehicular traffic must not proceed beyond the stop line.",
  binds: "driver",
  fault_if_violated: "Driver at fault — crossing the stop line on red breaches the prescribed prohibition, which is the substantive rule enforced by RTA 1988 s.36. (Verbatim: 'the red signal conveys the prohibition that vehicular traffic must not proceed beyond the stop line.')"
}
```

```
{
  id: "TSRGD2016-Sch14-Pt1-para5(9)",
  source: "TSRGD 2016, Schedule 14 Part 1 para 5(9) (SI 2016/362)",
  plain_language: "A steady amber signal has the same effect as red, except that a vehicle so close to the stop line that it cannot safely stop may proceed.",
  binds: "driver",
  fault_if_violated: "Driver at fault if they cross on amber when they could have stopped safely; not at fault if too close to stop safely."
}
```

```
{
  id: "TSRGD2016-Sch14-Pt1-para5(14)",
  source: "TSRGD 2016, Schedule 14 Part 1 para 5(14) (SI 2016/362)",
  plain_language: "Traffic proceeding beyond a stop line on green must proceed with due regard to the safety of other road users and subject to any direction by a constable/traffic officer/traffic warden.",
  binds: "driver",
  fault_if_violated: "A driver on green who proceeds without due regard to others' safety can still bear fault despite having a green light. (Verbatim: 'Vehicular traffic proceeding beyond a stop line must proceed with due regard to the safety of other road users...')"
}
```

```
{
  id: "HC-Rule109",
  source: "The Highway Code, Rule 109 (Laws: RTA 1988 s.36 & TSRGD)",
  plain_language: "You MUST obey all traffic light signals and traffic signs giving orders.",
  binds: "driver",
  fault_if_violated: "MUST rule backed by legislation — breach is an offence and strong evidence of driver fault."
}
```

```
{
  id: "HC-Rule175",
  source: "The Highway Code, Rule 175 (Laws: RTA 1988 s.36 & TSRGD Sch 14 Pts 1 & 4)",
  plain_language: "You MUST stop behind the white stop line unless the light is green; on amber you may go on only if already over the line or too close to stop safely.",
  binds: "driver",
  fault_if_violated: "Driver at fault for crossing on red/unjustified amber (MUST rule, legislative backing)."
}
```

```
{
  id: "HC-Rule176",
  source: "The Highway Code, Rule 176 (Laws: RTA 1988 s.36 & TSRGD Sch 14)",
  plain_language: "You MUST NOT move over the white line when red is showing; go on green only if there is room to clear; if lights are not working, treat as an unmarked junction and proceed with great care.",
  binds: "driver",
  fault_if_violated: "Driver at fault for crossing on red. IMPORTANT for the model: if lights are NOT working, the MUST duty falls away and the driver's duty reverts to ordinary care at an unmarked junction."
}
```

```
{
  id: "RTA1988-ss1-3",
  source: "Road Traffic Act 1988, ss.1, 2, 2A, 3 (ss.1-2A substituted by Road Traffic Act 1991 s.1; s.3ZA inserted by Road Safety Act 2006)",
  plain_language: "Offences of causing death by dangerous driving (s.1: 'A person who causes the death of another person by driving a mechanically propelled vehicle dangerously on a road or other public place is guilty of an offence'), dangerous driving (s.2), and careless/inconsiderate driving (s.3). 'Dangerous' = driving that falls FAR below what would be expected of a competent and careful driver, where it would be obvious to such a driver that driving that way would be dangerous (s.2A); 'careless' = driving that falls BELOW that standard (s.3ZA).",
  binds: "driver",
  fault_if_violated: "Driver at fault; red-light running that endangers others can escalate from a simple s.36 offence to careless (s.3, 'falls below') or dangerous (s.2, 'falls far below') driving depending on how far below standard the driving fell."
}
```

### AREA 2 — Right of way / priority at junctions

```
{
  id: "HC-Rule170-H2",
  source: "The Highway Code, Rule 170 & Rule H2 (2022 hierarchy of road users)",
  plain_language: "At a junction you should give way to pedestrians crossing or waiting to cross a road into which or from which you are turning; if they have started to cross they have priority. You MUST give way to pedestrians on a zebra crossing and to pedestrians/cyclists on a parallel crossing.",
  binds: "driver",
  fault_if_violated: "'Should' rule (advisory) EXCEPT the zebra/parallel-crossing element which is MUST. Failing to give way is evidence of driver fault under RTA 1988 s.38(7)."
}
```

```
{
  id: "HC-Rule171-172",
  source: "The Highway Code, Rules 171-172 (Laws: RTA 1988 s.36 & TSRGD regs 10, 16, 25)",
  plain_language: "You MUST stop at a STOP sign/solid white line; you MUST give way to traffic on the main road at a GIVE WAY sign/broken white lines.",
  binds: "driver",
  fault_if_violated: "MUST rules with legislative backing — emerging driver at fault if they fail to stop/give way."
}
```

```
{
  id: "HC-Rule177",
  source: "The Highway Code, Rule 177",
  plain_language: "A green filter arrow indicates a filter lane; proceed in the arrow's direction only.",
  binds: "driver",
  fault_if_violated: "Driver at fault for entering/using filter contrary to the arrow."
}
```

```
{
  id: "HC-Rule179-183",
  source: "The Highway Code, Rules 179-183",
  plain_language: "When turning right, position correctly and give way to oncoming traffic; when turning left do not cut across; give way to pedestrians/cyclists as per H2/H3.",
  binds: "driver",
  fault_if_violated: "'Should' guidance; breach is evidence of fault under s.38(7). A right-turning driver who fails to yield to oncoming traffic is usually primarily at fault."
}
```

```
{
  id: "HC-H1",
  source: "The Highway Code, Rule H1 (introduced 29 Jan 2022)",
  plain_language: "Road users who can cause the greatest harm bear the greatest responsibility to reduce danger to others (hierarchy: pedestrians > cyclists > horse riders > motorcyclists > cars/taxis > vans/minibuses > large passenger/heavy goods vehicles).",
  binds: "driver | other",
  fault_if_violated: "Advisory principle shaping apportionment; heavier vehicles carry greater responsibility."
}
```

```
{
  id: "HC-H3",
  source: "The Highway Code, Rule H3 (2022)",
  plain_language: "Drivers/motorcyclists should not cut across cyclists, horse riders or horse-drawn vehicles going ahead when turning into or out of a junction, and should not turn if it would cause them to stop or swerve.",
  binds: "driver",
  fault_if_violated: "Advisory; breach is strong evidence of driver fault in a turning collision with a cyclist going ahead."
}
```

```
{
  id: "JosephEva-priority",
  source: "Joseph Eva Ltd v Reeves [1938] 2 KB 393 (CA; parallel [1938] 2 All ER 115), per Scott LJ",
  plain_language: "A driver crossing on green has right of way and owes no duty to anticipate traffic entering against the red, beyond taking reasonable steps to avoid a collision with red-crossing traffic he actually sees.",
  binds: "driver",
  fault_if_violated: "The red-crossing driver ('the trespasser') is at fault; historically the green driver had a near-absolute priority ('the trespasser will have no chance of escaping liability on a plea alleging contributory negligence against the car which has the right of way') — but this 'absolute rule' has been limited by later cases (see Griffin)."
}
```

### AREA 3 — Emergency vehicles

```
{
  id: "HC-Rule219",
  source: "The Highway Code, Rule 219",
  plain_language: "Watch and listen for emergency vehicles with blue/red/green lights and sirens; take appropriate action to let them pass WHILE COMPLYING WITH ALL TRAFFIC SIGNS; do not endanger others or mount the kerb.",
  binds: "driver",
  fault_if_violated: "'Should' rule, but critically it directs that you must NOT break the law to give way — a driver who runs a red or enters a bus lane to make way is at fault for that offence."
}
```

```
{
  id: "RTRA1984-s87",
  source: "Road Traffic Regulation Act 1984, s.87 (as substituted by Road Safety Act 2006 s.19; amended by Deregulation Act 2015 s.50)",
  plain_language: "Statutory speed limits do not apply to vehicles used for fire/rescue, ambulance, NHS-emergency-response, police or NCA purposes if observing the limit would be likely to hinder that use.",
  binds: "emergency-vehicle",
  fault_if_violated: "If the exemption's conditions are NOT met (not on a qualifying purpose), the driver is speeding and at fault. Even when exempt, excessive speed can still found a negligence claim."
}
```

```
{
  id: "TSRGD2016-Sch14-Pt1-para5(4)-(6)",
  source: "TSRGD 2016, Schedule 14 Part 1 para 5(4)-(6) (SI 2016/362)",
  plain_language: "For a vehicle used for fire/rescue, Scottish Fire and Rescue Service, ambulance, blood service, NHS emergency response, bomb/explosive disposal, special forces, police or NCA purposes, where observing the red would be likely to hinder that use, the red signal instead means: the vehicle must not proceed beyond the stop line 'in such a manner or at such a time as to be likely to endanger any person or to cause the driver of another vehicle to change its speed or course in order to avoid an accident.'",
  binds: "emergency-vehicle",
  fault_if_violated: "Emergency vehicle at fault if it proceeds against red in a way that endangers others or forces evasive action — the exemption converts red from an absolute prohibition to a 'give-way'-style conditional permission, NOT a blanket right."
}
```

```
{
  id: "Griffin-v-Mersey",
  source: "Griffin v Mersey Regional Ambulance [1998] PIQR P34 (CA, 8 Oct 1997)",
  plain_language: "An ambulance crossing on red under exemption collided with a car crossing on green; the ambulance was liable but the car driver was 60% contributorily negligent for failing to see/hear the ambulance and ignoring other motorists' behaviour.",
  binds: "emergency-vehicle | driver",
  fault_if_violated: "Establishes that BOTH parties can be at fault. The CA held the trial judge 'rightly identified the duty upon the defendants' driver crossing this junction against the red light, as a high or heavy one, but equally rightly he recognised a duty of care upon the plaintiff beyond that of merely taking reasonable steps to avoid colliding with any vehicle crossing on red which he happened to see.' The 'absolute' Joseph Eva priority does not apply against a blue-light vehicle. Benchmark apportionment 60/40 against the green-light driver."
}
```

```
{
  id: "Keyse-v-Commissioner",
  source: "Keyse v Commissioner of Police of the Metropolis [2001] EWCA Civ 715 (18 May 2001)",
  plain_language: "Even in an emergency a driver must drive with reasonable care in all the circumstances; a police car driven by PC David Keyse on emergency duty seriously injured pedestrian Robert Scutts; the car was found to have been driven negligently, with liability reduced by 25% for the pedestrian's contributory negligence at first instance.",
  binds: "emergency-vehicle",
  fault_if_violated: "Emergency driver remains liable in negligence if they drive without reasonable care. Verbatim principle: 'the driver of an emergency vehicle is normally entitled to assume that other road users will not ignore the unmistakable evidence of its approach and where appropriate, temporarily at any rate, will use the road accordingly.' The emergency justifies some but not unlimited risk."
}
```

### AREA 4 — Authorised / priority vehicle classes

```
{
  id: "RVLR1989-reg16",
  source: "Road Vehicles Lighting Regulations 1989, reg.16 (SI 1989/1796)",
  plain_language: "No vehicle other than an emergency vehicle may be fitted with a blue warning beacon/special warning lamp or a device resembling one.",
  binds: "emergency-vehicle | other",
  fault_if_violated: "Non-emergency vehicle displaying a blue beacon commits an offence; blue-light entitlement is the marker of 'emergency vehicle' status."
}
```

```
{
  id: "RVLR1989-reg11",
  source: "Road Vehicles Lighting Regulations 1989, reg.11 (SI 1989/1796)",
  plain_language: "Sets which lights/colours vehicles may show; permits blue light from a warning beacon fitted to an emergency vehicle (reg.11(2)(k)) and specific colour schemes for fire/ambulance/police control vehicles.",
  binds: "emergency-vehicle",
  fault_if_violated: "Improper light fitment/use is an offence; relevant to whether a vehicle qualifies as an emergency vehicle."
}
```

```
{
  id: "EmergencyVehicle-classes",
  source: "RVLR 1989 definition of 'emergency vehicle' (as amended, e.g. SI 2005/2559, SI 2009/3221) and TSRGD 2016 Sch 14 Pt 1 para 5(6)",
  plain_language: "Classes with the TSRGD red-light exemption are: fire and rescue authority, Scottish Fire and Rescue Service, ambulance, blood service, NHS-emergency-response, bomb/explosive disposal, special forces, police, and National Crime Agency. For lighting/siren purposes the 'emergency vehicle' definition also extends to coastguard, mountain rescue, mine rescue, RAF mountain rescue and lifeboat launching vehicles, plus (added 2005) MoD nuclear-response and HMRC serious-crime vehicles.",
  binds: "emergency-vehicle",
  fault_if_violated: "Only listed classes get the red-light and speed exemptions; a vehicle outside these classes has no exemption and is at fault if it proceeds against red."
}
```

```
{
  id: "MaintenanceVehicles-no-exemption",
  source: "TSRGD 2016 Sch 14 Pt 1 para 5(6) (list excludes highway-maintenance); RVLR 1989 reg.17 (amber beacons)",
  plain_language: "Highway-maintenance and works vehicles use AMBER beacons and are NOT emergency vehicles; they have no red-light exemption, though works/traffic-authority vehicles may have limited exemptions from certain restrictions (e.g. keep-left signs, some access) under Traffic Regulation Orders.",
  binds: "other",
  fault_if_violated: "A maintenance/works vehicle that crosses a red is at fault exactly like an ordinary driver — no blue-light exemption applies."
}
```

### AREA 5 — Authority duty and liability for signal malfunction

```
{
  id: "HighwaysAct1980-s41",
  source: "Highways Act 1980, s.41 (with s.58 defence); scope confined by Goodes v East Sussex CC [2000] 1 WLR 1356 (HL)",
  plain_language: "The highway authority has a duty to maintain the fabric of the highway; s.58 gives a defence where reasonable care was taken.",
  binds: "traffic-authority",
  fault_if_violated: "Per Goodes v East Sussex CC [2000] 1 WLR 1356 (HL), the s.41 duty to 'maintain' is confined to keeping the physical fabric/surface of the highway in repair (Goodes concerned ice/snow on the carriageway; note its ice holding was legislatively reversed by the Railways and Transport Safety Act 2003 s.111, inserting Highways Act 1980 s.41(1A) — but the fabric/repair SCOPE principle it states survives and is what we rely on). The DISTINCT proposition that the s.41 duty does not extend to traffic signs/signals, and that a highway authority owes no private-law duty to provide or erect signs/markings, is Lord Hoffmann in Gorringe v Calderdale [2004] UKHL 15. (Earlier CA authority: Lavis v Kent CC (1992) 90 LGR 416.) So a signal fault is generally NOT actionable under s.41."
}
```

```
{
  id: "Gorringe-v-Calderdale",
  source: "Gorringe v Calderdale MBC [2004] UKHL 15; [2004] 1 WLR 1057",
  plain_language: "A highway authority's duty to 'maintain' under s.41 is confined to keeping the fabric of the road in repair and does not require signs/markings; broad public-law duties (RTA 1988 s.39) create no private-law duty of care; there is no liability for mere failure to warn.",
  binds: "traffic-authority",
  fault_if_violated: "Authority generally NOT liable for nonfeasance (failure to provide/repair a sign or warning). This is the core reason signal-authority fault is legally weak."
}
```

```
{
  id: "Poole-BC-v-GN",
  source: "Poole BC v GN [2019] UKSC 25; [2020] AC 780",
  plain_language: "The modern UK Supreme Court restatement of the omissions principle: a public authority is generally under no duty of care to confer a benefit or protect from harm it did not create, absent an assumption of responsibility; liability attaches to positive acts that make things worse, not to failures to act.",
  binds: "traffic-authority",
  fault_if_violated: "Reinforces the misfeasance-only branch (aligned with Gorringe/Stovin): signal-authority fault turns on a positively-created dangerous/misleading state (e.g. conflicting greens), not on a signal merely failing. Cite alongside Stovin v Wise and Gorringe."
}
```

```
{
  id: "Stovin-v-Wise",
  source: "Stovin v Wise [1996] UKHL 15; [1996] AC 923",
  plain_language: "A public authority is not generally liable in negligence for failing to exercise a statutory power (pure omission).",
  binds: "traffic-authority",
  fault_if_violated: "Reinforces no-liability-for-omission; authority fault requires a positive act."
}
```

```
{
  id: "Bird-v-Pearce",
  source: "Bird v Pearce [1979] RTR 369 (CA)",
  plain_language: "Where a highway authority positively created a hazard — obliterating/removing established give-way road markings without a temporary warning — it was negligent and liable; the authority had created an expectation and then a new source of danger.",
  binds: "traffic-authority",
  fault_if_violated: "Authority CAN be at fault for MISFEASANCE — creating a trap or a new source of danger. Distinguished in Gorringe on the basis that Bird's authority had 'negligently introduced a new source of danger.' The simulation analogue: signals showing conflicting greens or a wrong indication created by the authority/its system."
}
```

```
{
  id: "RTRA1984-ss64-65",
  source: "Road Traffic Regulation Act 1984, ss.64-65",
  plain_language: "s.64 defines a 'traffic sign' as any object/device conveying warnings, requirements, restrictions or prohibitions (including signals and road markings) and provides that s.36 RTA 1988 applies; s.65 empowers the traffic authority to place traffic signs/signals in accordance with the Secretary of State's directions (TSRGD).",
  binds: "traffic-authority",
  fault_if_violated: "Placing power, not a maintenance duty; establishes that signals are 'signs' whose disobedience is an offence, and identifies the authority as the placer/operator."
}
```

```
{
  id: "TMA2004-s16",
  source: "Traffic Management Act 2004, s.16 (network management duty)",
  plain_language: "Every local traffic authority has a duty to manage its road network with a view to securing the expeditious movement of traffic, so far as reasonably practicable having regard to its other obligations.",
  binds: "traffic-authority",
  fault_if_violated: "A public-law/management duty; like RTA s.39 it is very unlikely to found a private-law damages claim for a signal fault (consistent with Gorringe reasoning)."
}
```

```
{
  id: "TfL-London-signals",
  source: "Greater London Authority Act 1999; Traffic Management Act 2004 (TfL as GLA functional body)",
  plain_language: "Transport for London operates London's traffic-signal system — on the order of ~6,000 traffic-signal junctions within the Greater London boundary (TfL-published figure; attach a TfL source + as-at date before citing a precise number), one of Europe's largest such networks. Euston Road (A501) is part of the Transport for London Road Network (TLRN, the 'red routes'), so TfL is BOTH the highway authority and the signal-operating authority for it — a stronger and less ambiguous controllership than a borough road, where signals are TfL but the carriageway is the borough's.",
  binds: "traffic-authority",
  fault_if_violated: "Identifies the correct defendant for any signal-malfunction claim on the A501: Transport for London (Euston Road is TLRN, so TfL is both highway and signal authority)."
}
```

### AREA 6 — Fault / liability principles

```
{
  id: "Negligence-elements",
  source: "Common law (duty, breach, causation, damage)",
  plain_language: "A party is liable in negligence where they owed a duty of care, breached it by falling below the reasonable standard, and thereby caused foreseeable damage.",
  binds: "driver | traffic-authority | emergency-vehicle",
  fault_if_violated: "The general framework for allocating fault to any actor in the model."
}
```

```
{
  id: "RTA1988-s38(7)",
  source: "Road Traffic Act 1988, s.38(7)",
  plain_language: "Failure to observe the Highway Code is not itself an offence, but 'any such failure may in any proceedings (whether civil or criminal...) be relied upon by any party to the proceedings as tending to establish or negative any liability which is in question in those proceedings.'",
  binds: "driver | emergency-vehicle",
  fault_if_violated: "This is the bridge that lets 'should' (advisory) Highway Code rules carry evidential weight in fault attribution, though with less force than a 'MUST' offence."
}
```

```
{
  id: "LawReform-ContribNeg-1945-s1",
  source: "Law Reform (Contributory Negligence) Act 1945, s.1(1)",
  plain_language: "Where a person's damage results partly from their own fault and partly of another's, the claim is not defeated but 'the damages recoverable in respect thereof shall be reduced to such extent as the court thinks just and equitable having regard to the claimant's share in the responsibility for the damage.'",
  binds: "driver | emergency-vehicle | other",
  fault_if_violated: "Mechanism to split fault between an injured party and a defendant (e.g. Griffin 60/40)."
}
```

```
{
  id: "CivilLiability-Contribution-1978-s1",
  source: "Civil Liability (Contribution) Act 1978, s.1(1) & s.2(1)",
  plain_language: "s.1(1): 'any person liable in respect of any damage suffered by another person may recover contribution from any other person liable in respect of the same damage (whether jointly with him or otherwise).' s.2(1): the amount of contribution 'shall be such as may be found by the court to be just and equitable having regard to the extent of that person's responsibility for the damage in question.'",
  binds: "driver | traffic-authority | emergency-vehicle",
  fault_if_violated: "Mechanism to apportion between multiple wrongdoers — e.g. a red-light-running driver AND an authority whose signal was faulty (joint tortfeasors)."
}
```

## Synthesis — Decision Logic for the Model

The rules let the model resolve a junction incident by walking a decision tree that mirrors how a UK court would attribute fault:

**Step 1 — Was the signal functioning correctly?**
- If YES (signals gave a lawful, consistent indication): the signal authority is almost certainly NOT at fault (Gorringe/Stovin — no liability for omission, and s.41 does not cover signals). Fault sits with road users. Proceed to Step 2.
- If NO — signals were dark/not working: the MUST duties (Rules 175-176) fall away; each driver's duty reverts to ordinary care at an unmarked junction (Rule 176). No automatic authority liability for the mere failure.
- If NO — signals gave a *wrong/conflicting* indication created by the system (e.g. conflicting greens): this is the misfeasance scenario (Bird v Pearce analogue). The authority (TfL in London) can bear a share of fault for creating a trap. This is the one route to "AI"/authority fault, and it is legally the least settled — flag low confidence.

**Step 2 — Did a driver break a signal rule?**
- A driver who crossed the stop line on red breached TSRGD 2016 Sch 14 Pt 1 para 5(3) and committed an RTA 1988 s.36 offence → strong, near-decisive driver fault. If the manner of driving fell far below standard, escalate to careless (s.3) or dangerous (s.2) driving.
- A driver on green who failed to proceed with due regard to safety (para 5(14)) can still carry a minority share.

**Step 3 — Was an emergency vehicle on a genuine blue-light run?**
- If an emergency vehicle (a listed class in TSRGD Sch 14 Pt 1 para 5(6)) crossed on red, apply the conditional exemption: it is NOT at fault merely for crossing red, BUT is at fault if it proceeded so as to endanger others or force evasive action (para 5(5)). Speed exemption via RTRA 1984 s.87 applies in parallel.
- The other driver still owes a duty to look and listen (Griffin, Rule 219). Apply a contributory-negligence split — Griffin's 60/40 against the non-emergency driver is a reasonable default benchmark, adjustable for visibility/audibility facts (Keyse: each case fact-specific; the emergency driver is "normally entitled to assume that other road users will not ignore the unmistakable evidence of its approach").
- A maintenance/works vehicle (amber beacon) gets NO exemption — treat exactly as an ordinary driver.

**Step 4 — Did any driver break the law to give way?**
- A driver who ran a red, entered a bus lane, or stopped in a box junction to let an emergency vehicle through is at fault for that offence (Rule 219) — the model should NOT excuse a rule breach done "to help."

**Step 5 — Apportion.**
- Use negligence elements to assign a share to each culpable actor, reduce a claimant's recovery for contributory negligence (1945 Act s.1), and split between multiple wrongdoers as joint tortfeasors (1978 Act s.1) on a "just and equitable" basis.

## Recommendations
1. **Encode the MUST/should distinction as a fault-weight field.** Give MUST rules (backed by RTA 1988 s.36 + TSRGD) a high fault weight (offence + prima facie negligence); give "should" rules a lower evidential weight routed through RTA 1988 s.38(7). Threshold to change: if a rule's Highway Code text says "MUST/MUST NOT" AND cites a statute, flag it as hard-law.
2. **Model the authority ("AI") as liable ONLY on the misfeasance branch.** Default authority fault to zero for correctly-functioning or merely-failed signals; enable a non-zero authority share only where the model generates a positively wrong/conflicting indication. Set TfL as the responsible authority entity for the Euston Road (A501) junction (TLRN).
3. **Implement the emergency-vehicle exemption as conditional, not absolute.** Represent red-as-give-way with an "endangerment" test drawn verbatim from para 5(5): if the emergency vehicle's entry was "likely to endanger any person or to cause the driver of another vehicle to change its speed or course in order to avoid an accident," assign it a fault share even though it was exempt.
4. **Use Griffin's 60/40 as the calibration anchor** for green-driver-vs-red-emergency-vehicle collisions, and expose visibility/audibility parameters that shift the split (per Keyse's fact-specific approach and its 25% pedestrian contributory finding).
5. **Benchmarks that should change the output:** signal-log evidence that indications were conflicting → shift share to TfL; dashcam/telemetry showing the green-light driver could have seen/heard the emergency vehicle → increase their contributory share; proof the "emergency" vehicle was not on a qualifying purpose → remove its exemption entirely.

## Caveats and Confidence Flags

**(a) Section/rule numbers that could not be fully verified against primary source:**
- The exact meaning of the **red signal (TSRGD 2016 Sch 14 Pt 1 para 5(3))** and the **emergency exemption (para 5(4)-(6))** WERE verified verbatim against the legislation.gov.uk text of SI 2016/362. However, older Highway Code editions cite "TSRGD regs 10 & 36" (the 2002 numbering); current Rule 175-176 cite "TSRGD Sch 14 Pts 1 & 4." The model should use the **2016 Schedule 14 references**, not the legacy 2002 regulation numbers.
- **Bird v Pearce** citation is commonly given as [1979] RTR 369 (CA); some sources date the first-instance decision to 1978. Treat the CA decision as authoritative.
- The precise **RVLR 1989 definition of "emergency vehicle"** has been amended several times; the class list is drawn from TSRGD 2016 Sch 14 para 5(6) (for the red-light exemption) and RVLR (for lighting). These two lists are similar but not identical — verify the exact class before relying on it.
- **Joseph Eva Ltd v Reeves** [1938] 2 KB 393 pre-dates BAILII's core coverage; the Scott LJ quotations rest on a reputable secondary reproduction (swarb.co.uk), corroborated across multiple sources, rather than a primary transcript.

**(b) Legally unsettled areas (low confidence):**
- **Authority liability for signal malfunction is the least settled area.** There is abundant authority that an authority is NOT liable for omissions/failure to sign (Gorringe, Stovin, Lavis), and clear authority that it CAN be liable for misfeasance/creating a trap (Bird v Pearce). But there is **thin direct case law on liability for a traffic signal that positively displays conflicting greens or a wrong indication.** The Bird v Pearce misfeasance principle is the best available analogue; treat any authority-fault output as legally tentative and flag it. (Note also that TfL records identify 591 traffic-signal sites in London without vehicular traffic detection — a data point relevant to how signal states are generated, not to liability per se.)
- The interaction between the **network management duty (TMA 2004 s.16)** and private-law liability is untested for signal faults; it almost certainly does not create a damages remedy (consistent with Gorringe's treatment of RTA s.39), but this is an inference, not a decided point.
- The **"absolute" green-light priority** in Joseph Eva v Reeves has been expressly limited where emergency vehicles are involved (Griffin) and should not be coded as an unqualified rule; each collision is fact-specific.

**(c) MUST/MUST NOT vs "should" — critical for fault-attribution strength:**
- Highway Code rules using **"MUST/MUST NOT"** are backed by specific legislation (identified by the "Law/Laws" tag in the Code). Breach is a criminal offence AND, via RTA 1988 s.38(7), strong evidence of civil fault. Examples in scope: Rules 109, 175, 176 (traffic lights); 171-172 (STOP/GIVE WAY signs).
- Rules using **"should"** (e.g. Rule 170/H2 give-way to pedestrians at junctions except the zebra/parallel-crossing element which is MUST; Rules 179-183 turning; H1, H3; Rule 219 emergency vehicles) are advisory: breach is NOT itself an offence but IS admissible under s.38(7) to establish or negate liability. The model should weight these lower than MUST rules but not treat them as legally irrelevant.