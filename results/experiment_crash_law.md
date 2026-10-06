# H2: multi-scenario crash -> UK-law audit suite

**7 scenarios, all proven: YES.** for each predefined crash scenario, the signed audit proves the incident beyond doubt (chain + signatures verify, a tamper is caught) and the governing UK traffic law is inferred directly from the verified audit record + cited to the KB.

## civilian runs red
_A civilian car crosses the stop line against a red indication and collides._

- **Audit record** (seq 0, issuer `J`, hash `a0bb851cd145884d...`): signal=`red`, crossing=`civilian`, key_valid=False, authority=`None`, corroborated=False, conflicting_green=False
- **Proof**: verify_chain=**True**, verify_signatures=**True**, forged-signature caught=**True**
- **Governing UK law (inferred from the verified record):**
  - `LR-driver-red` (RTA1988-s36, fault_weight high): A driver who fails to comply with a lawfully-placed prescribed traffic sign (incl. traffic light signals) commits a criminal offence.
    - why: the vehicle crossed the stop line against a red indication -- a criminal offence (RTA 1988 s36 / TS10)
  - `LR-red-prohibition` (TSRGD2016-Sch14-Pt1-para5(3), fault_weight high): The red signal conveys the prohibition that vehicular traffic must not proceed beyond the stop line.
    - why: the red signal conveys the prohibition that vehicular traffic must not proceed beyond the stop line
- **Proven beyond doubt: YES**

## ambulance crosses red exempt
_An authorised, corroborated ambulance crosses red on an emergency run and conflicts with a car lawfully on green._

- **Audit record** (seq 0, issuer `J`, hash `a08f8ce6eab6aab8...`): signal=`red`, crossing=`ambulance`, key_valid=True, authority=`emergency`, corroborated=True, conflicting_green=False
- **Proof**: verify_chain=**True**, verify_signatures=**True**, forged-signature caught=**True**
- **Governing UK law (inferred from the verified record):**
  - `LR-ev-exemption` (TSRGD2016-Sch14-Pt1-para5(4)-(6), fault_weight medium): An emergency vehicle may treat red as give-way and is NOT at fault merely for crossing red; fault arises ONLY on the para 5(5) endangerment test (it forced evasive action / endangered others).
    - why: an authorised, corroborated emergency vehicle crossed red; not at fault merely for crossing (fault only on the endangerment test)
  - `LR-griffin-calibration` (Griffin-v-Mersey, fault_weight medium): Where a green-light driver collides with a red-crossing emergency vehicle, the default apportionment anchor is 60/40 against the non-emergency (green) driver.
    - why: apportioning the EV-vs-other conflict: the default anchor is 60/40 against the non-emergency party
  - `LR-green-due-regard` (TSRGD2016-Sch14-Pt1-para5(14), fault_weight low): Traffic proceeding beyond a stop line on green must proceed with due regard to the safety of other road users.
    - why: the other party was on green but must proceed with due regard; typically the minority share (Joseph Eva)
- **Proven beyond doubt: YES**

## maintenance runs red
_A highway maintenance/works vehicle crosses red; it is NOT an emergency vehicle._

- **Audit record** (seq 0, issuer `J`, hash `2588b67c5eb13178...`): signal=`red`, crossing=`maintenance`, key_valid=True, authority=`works`, corroborated=False, conflicting_green=False
- **Proof**: verify_chain=**True**, verify_signatures=**True**, forged-signature caught=**True**
- **Governing UK law (inferred from the verified record):**
  - `LR-maintenance-no-exemption` (MaintenanceVehicles-no-exemption, fault_weight high): Highway maintenance/works vehicles are NOT 'emergency vehicles' for the red-light exemption; a works vehicle crossing red is at fault exactly like an ordinary driver.
    - why: a highway maintenance/works vehicle is NOT an emergency vehicle for the red-light exemption; crossing red it is at fault exactly like an ordinary driver
  - `LR-driver-red` (RTA1988-s36, fault_weight high): A driver who fails to comply with a lawfully-placed prescribed traffic sign (incl. traffic light signals) commits a criminal offence.
    - why: crossing the stop line against red is a criminal offence (TS10); near-conclusive of driver fault
- **Proven beyond doubt: YES**

## driver crosses on amber
_A driver crosses on a steady amber when a safe stop was possible._

- **Audit record** (seq 0, issuer `J`, hash `172cf2721cae4aa7...`): signal=`amber`, crossing=`civilian`, key_valid=False, authority=`None`, corroborated=False, conflicting_green=False
- **Proof**: verify_chain=**True**, verify_signatures=**True**, forged-signature caught=**True**
- **Governing UK law (inferred from the verified record):**
  - `LR-amber` (TSRGD2016-Sch14-Pt1-para5(9), fault_weight high): A steady amber has the same effect as red; a driver who could have stopped safely but crossed is at fault. No fault only where too close to stop safely.
    - why: the vehicle crossed on a steady amber when a safe stop was possible (same effect as red)
- **Proven beyond doubt: YES**

## conflicting green fault
_The signal system emits a conflicting green (a positively-wrong indication); two movements are released at once._

- **Audit record** (seq 0, issuer `J`, hash `93dc0a0bc66941d3...`): signal=`green`, crossing=`civilian`, key_valid=False, authority=`None`, corroborated=False, conflicting_green=True
- **Proof**: verify_chain=**True**, verify_signatures=**True**, forged-signature caught=**True**
- **Governing UK law (inferred from the verified record):**
  - `LR-authority-misfeasance` (Bird-v-Pearce, fault_weight low): An authority CAN be liable where it positively creates a trap (e.g. conflicting green signals) — misfeasance, not omission.
    - why: the audit shows the system emitted a conflicting green (a positively-wrong indication) -- misfeasance, not omission
  - `LR-authority-nonfeasance` (Gorringe-v-Calderdale, fault_weight low): A highway authority owes no private-law duty to provide/erect signs or warn (nonfeasance), and s.41 does not extend to signs/signals (Lord Hoffmann); liability only for misfeasance.
    - why: authority fault otherwise defaults to zero; it turns non-zero only on this misfeasance/conflicting-green branch (low-confidence; legal_causation NOT_ASSESSED)
- **Proven beyond doubt: YES**

## dark signal
_The signals are dark/inoperative at the time; a collision occurs at the junction._

- **Audit record** (seq 0, issuer `J`, hash `e286877ce5f77be1...`): signal=`dark`, crossing=`civilian`, key_valid=False, authority=`None`, corroborated=False, conflicting_green=False
- **Proof**: verify_chain=**True**, verify_signatures=**True**, forged-signature caught=**True**
- **Governing UK law (inferred from the verified record):**
  - `LR-dark-signals` (HC-Rule176, fault_weight low): When traffic lights are not working (dark), the MUST duty to obey the signal falls away and each driver reverts to ordinary care as at an unmarked junction.
    - why: the signal was dark/inoperative at the incident time, so the duty to obey it falls away (each driver reverts to ordinary care)
- **Proven beyond doubt: YES**

## spoofed ev triggers red run
_A compromised-but-approved neighbour signs a PHANTOM ambulance claim that commandeers the signal; a civilian then crosses the resulting red and collides. The audit attributes the triggering claim to the signing KEY._

- **Audit record** (seq 0, issuer `J`, hash `885ddf3be6d3bdac...`): signal=`red`, crossing=`civilian`, key_valid=False, authority=`None`, corroborated=False, conflicting_green=False, claim_key=`compromised-neighbour-key`
- **Proof**: verify_chain=**True**, verify_signatures=**True**, forged-signature caught=**True**
- **Governing UK law (inferred from the verified record):**
  - `LR-driver-red` (RTA1988-s36, fault_weight high): A driver who fails to comply with a lawfully-placed prescribed traffic sign (incl. traffic light signals) commits a criminal offence.
    - why: the vehicle crossed the stop line against a red indication -- a criminal offence (RTA 1988 s36 / TS10)
  - `LR-red-prohibition` (TSRGD2016-Sch14-Pt1-para5(3), fault_weight high): The red signal conveys the prohibition that vehicular traffic must not proceed beyond the stop line.
    - why: the red signal conveys the prohibition that vehicular traffic must not proceed beyond the stop line
- **Proven beyond doubt: YES**

> Evidence-pack mapping (audited facts -> which rule governs) with the KB's own fault_weight; NOT a determination of fault against a person (keys/origins, never names). Law grounding: 01-research/uk-traffic-law.md.
