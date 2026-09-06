# DSBSS: Plain English Study & Architecture Guide

> **Purpose of this document:** A zero-buzzword, crystal-clear explanation of what this project actually does, how every calculation works, what each file is responsible for, and why the current interface feels cluttered. Use this as your study sheet before doing a major visual and code cleanup.

---

## 1. The Core Real-World Problem

Imagine you manage a busy railway track (like the Konkan Railway section connecting Goa and Maharashtra).

### How maintenance works today (The Old / Bad Way):
Tracks wear down and need regular inspections and repairs:
1. **Civil Engineering team** says: *"We need to inspect and tamp the tracks for 2 hours."* Track gets shut down on Monday. Trains get delayed.
2. **Electrical (OHE) team** says: *"We need to inspect the overhead electric wires for 1.5 hours."* Track gets shut down on Wednesday. Trains get delayed again.
3. **Signaling & Telecom (S&T) team** says: *"We need to service the motorized track switches for 1 hour."* Track gets shut down on Friday. More train delays.

**Total track outage:** $2 + 1.5 + 1 = 4.5\text{ hours}$ (270 minutes) across 3 separate disruptions.

### The Solution: "Shadow Blocking" (What this project does):
1. **Bundling:** Instead of closing the track 3 separate times, put all 3 repair teams on the track **at the exact same time**. Since they work concurrently, the total closure is only as long as the longest job (2 hours instead of 4.5 hours). You instantly save 2.5 hours of track closure.
2. **The "Shadow" concept:** Don't shut the track down during morning or evening rush hour when premium passenger trains (like Rajdhani or Vande Bharat) are running. Instead, scan the daily timetable and find a natural "lull" (a gap with few or no trains). Slip the combined maintenance block into that gap like a "shadow" that trains never notice.

---

## 2. Buzzword Translation Dictionary

Before reading further, here is a translation of the hackathon buzzwords into normal human English:

| Buzzword in Code/UI | What It Actually Means |
| :--- | :--- |
| **Dynamic Shadow-Block Planning System** | A tool that bundles maintenance jobs into schedule gaps so trains don't get delayed. |
| **Constraint Programming (CP-SAT Solver)** | A math puzzle solver (using Google's free `ortools` library) that finds the best time slot. |
| **Spatio-Temporal Optimization Matrix** | Checking both *where* (space / track) and *when* (time) trains and workers are on the rails. |
| **Explainable AI (XAI) Financial Router** | A simple calculator that picks the cheapest backup route when a track is broken, and shows the math step-by-step. |
| **Constrained Shortest Path First (CSPF)** | Finding an alternate route that physically fits the train (not too heavy, right fuel/electricity). |
| **Gross Tonne Kilometre (GTKM)** | The standard railway unit of work: $\text{Weight of train (tonnes)} \times \text{Distance traveled (km)}$. |
| **Predictive IoT Telemetry Ingestion Watchdog** | A small machine learning script that warns you if a track switch motor is drawing too much current and might break soon. |
| **Point Machine** | The electric motor that pushes the rails to switch a train from one track to another. |
| **Marey String Chart** | A standard railway graph where the horizontal axis is time of day and the vertical axis is station distance. Train routes look like diagonal lines ("strings"). |
| **Autonomous Interlocking Fail-Safe HUD** | A fancy title on the dashboard screen to make it sound futuristic. |

---

## 3. The 4 Core Building Blocks of the Project

The software is split into 4 clean parts under the `core/` folder:

```
DSBSS/
├── core/
│   ├── data_engine.py          # 1. Timetable reader
│   ├── shadow_block_solver.py  # 2. Schedule slot finder (Google OR-Tools)
│   ├── ml_diagnostics.py       # 3. Switch motor health checker (Random Forest)
│   └── xai_rerouter.py         # 4. Backup route & cost calculator
├── api_stage2.py               # Web API for motor health checker
├── main_app.py                 # Streamlit visual dashboard
```

---

### Block 1: The Timetable Reader (`core/data_engine.py`)
* **What it does:** Reads the raw CSV file (`data/FINAL_ML_READY_DATA.csv`), which contains 186,000+ rows of train schedules across India.
* **How it filters:** It extracts trains passing through 4 key Konkan Railway stations:
  * Madgaon Jn (`MAO` - 0 km)
  * Karmali (`KRMI` - 33 km)
  * Thivim (`THVM` - 51 km)
  * Pernem (`PERN` - 67 km)
* **Priority Weighting:** Trains aren't all equal. It assigns each train a priority score from 1 to 5:
  * **Score 5 (Super Premium):** Vande Bharat, Rajdhani, Shatabdi, Tejas (huge penalty if delayed).
  * **Score 3 (Standard):** Express, Mail, Superfast.
  * **Score 1 (Low Priority):** Slow local passenger trains and freight goods trains.

---

### Block 2: The Maintenance Slot Finder (`core/shadow_block_solver.py`)
* **What it does:** Uses Google OR-Tools to answer one question: *"When is the best time today to close the track for maintenance?"*
* **How it calculates:**
  1. You tell it how much time each department needs:
     * Track Engineering = 120 mins
     * Electrical OHE = 90 mins
     * Signaling = 60 mins
  2. Because all teams work at the same time, the required closure duration is:
     $$\text{Bundled Duration} = \max(120, 90, 60) = 120\text{ minutes}$$
  3. The solver tests every possible start time during the 24-hour day (from minute 0 to 1440).
  4. For every minute the track is closed, it checks if any train is scheduled to pass:
     * If a train collides with the maintenance window, a penalty is added based on that train's priority score.
     * Colliding with a Vande Bharat (weight 5) incurs 5 points of penalty. Colliding with a freight train (weight 1) incurs 1 point.
  5. The solver finds the start time that has the **lowest penalty score** (ideally 0, meaning an empty gap in the schedule).

---

### Block 3: The Switch Motor Failure Detector (`core/ml_diagnostics.py`, `scripts/train_model.py`, `api_stage2.py`)
* **What is a Point Machine?**
  Whenever a train switches tracks, an electric motor physically slides the steel rail over. If this motor gets stuck with dirt, rocks, or rusted gears, trains will be halted at red signals.
* **What are the sensors measuring?**
  1. `motor_current_peak_amps`: Highest electric current drawn during movement (Normal: 3–5 Amps. If jammed: 7–9 Amps).
  2. `motor_current_avg_amps`: Average electric current drawn.
  3. `throw_duration_ms`: Time taken to slide the switch (Normal: ~3,000 ms = 3 seconds. If sticking: 4,000–5,000 ms).
  4. `vibration_peak_g`: Mechanical shaking (Normal: ~0.10g. If grinding: 0.30–0.50g).
  5. `ambient_temp_c`: Outdoor weather temperature.
* **What did the Machine Learning model do?**
  * In `scripts/train_model.py`, we trained a simple `RandomForestClassifier` on 1,000 recorded switch operations.
  * The model learned: If peak amps > 6.5A AND throw time > 3,800ms, the switch is degrading (`label_anomaly = 1`).
  * The trained model is saved as `models/rf_model.pkl` (285 KB).
* **The Auto-Trigger Concept:**
  If the sensor detects degradation, the software can automatically submit a 60-minute Signaling maintenance request to the schedule solver *before* the switch completely breaks in real life.
* **`api_stage2.py`:** A small FastAPI web server that allows external sensors to send readings via HTTP POST to `/predict` and receive an immediate `{"status": "HEALTHY"}` or `{"status": "DANGER"}` response.

---

### Block 4: The Backup Route & Cost Calculator (`core/xai_rerouter.py`)
* **What it does:** When a track is completely blocked (due to an accident, landslide, or active maintenance), a train must be diverted onto an alternate track (e.g. Bypass Line B, Branch Line C, Chord Line D). Which line should it take?
* **It evaluates routes in 2 simple stages:**

#### Stage 1: The Physical Reality Check (Constraint Pruning)
Can the train physically run on this alternate line?
1. **Axle Load Limit:**
   * A heavy loaded coal train weighs 4,200 tonnes.
   * If Line B only supports 2,000 tonnes, the track or bridges could collapse.
   * Result: **Rejected!**
2. **Electrification (Overhead Wires):**
   * A passenger train pulled by an electric engine (WAP-7) requires 25kV overhead wires.
   * If Branch Line C is non-electrified (diesel engines only), the train has no power.
   * Result: **Rejected!**
3. **Headway / Capacity:**
   * If a single-track line already has 5 trains queued up and its maximum safe capacity is 5, no more trains can enter.
   * Result: **Rejected!**
4. **Active Blockage:**
   * If a line is already shut down for maintenance, trains cannot enter.
   * Result: **Rejected!**

#### Stage 2: The Money Check (Financial Maximization)
For the alternate lines that pass Stage 1, which one keeps the most money?
It uses a 4-part formula based on official Indian Railways economics:

$$\mathbf{P_{\text{net}} = R - \left( C_{\text{GTKM}} + P_{\text{delay}} + C_{\text{opp}} \right)}$$

1. **Revenue ($R$):** The freight charges or passenger tickets collected for this journey (e.g. +₹35,00,000 for Rajdhani; +₹50,00,000 for a Coal rake).
2. **GTKM Operating Cost ($C_{\text{GTKM}}$):**
   * Indian Railways calculates operational costs in **Gross Tonne Kilometres (GTKM)**.
   * The official benchmark is approximately **₹0.90 per tonne-kilometre**.
   * Formula:
     $$C_{\text{GTKM}} = \text{Train Weight (Tonnes)} \times \text{Route Distance (km)} \times ₹0.90$$
   * Example: A 1,100-tonne train taking a 650 km bypass costs:
     $$1,100 \times 650 \times 0.90 = ₹6,43,500$$
3. **Punctuality Delay Penalty ($P_{\text{delay}}$):**
   * If a line has speed restrictions or takes longer, the train is delayed.
   * Premium passenger trains have a high penalty (₹5,000 per minute).
   * Freight trains have a low penalty (₹500 per minute).
   * Formula:
     $$P_{\text{delay}} = \text{Estimated Delay (mins)} \times \text{Penalty Rate (₹/min)}$$
   * Example: A 45-minute delay for Rajdhani costs:
     $$45 \times ₹5,000 = ₹2,25,000$$
4. **Opportunity Congestion Cost ($C_{\text{opp}}$):**
   * If the alternate line already has 4 other trains on it, putting this train on it will slow everyone else down.
   * We assign an estimated congestion bottleneck fee of ₹15,000 per train ahead:
     $$4 \times ₹15,000 = ₹60,000$$

**The Winner:**
$$\text{Net Profit} = \text{Revenue} - (\text{GTKM Cost} + \text{Delay Penalty} + \text{Opportunity Cost})$$
The system chooses the route with the highest Net Profit and prints out the exact addition and subtraction so any human dispatcher can verify the decision.

---

## 4. The 5 Tabs on the Dashboard (`main_app.py`)

The main dashboard is built in Streamlit and contains 5 tabs:

1. **Tab 1: Marey String Chart**
   * Shows a time-distance graph of all trains on the Konkan corridor.
   * Vertical axis: Stations from Madgaon (0 km) to Pernem (67 km).
   * Horizontal axis: Hours of the day (00:00 to 24:00).
   * Diagonal lines: Trains moving between stations.
   * Dark grey shaded box: The synchronized maintenance window recommended by the solver.
2. **Tab 2: Shadow-Block Studio**
   * Sliders for Engineering, Electrical, and Signaling repair times.
   * Shows a comparison bar chart: Unbundled time (e.g. 270 mins across 3 days) vs Bundled time (120 mins in 1 day).
   * Displays the exact optimal time slot found by Google OR-Tools (e.g. `14:30 - 16:30`).
3. **Tab 3: IoT Telemetry Radar**
   * Interactive sliders for switch motor sensors (Amps, throw duration, vibration).
   * Live gauge showing motor health percentage (e.g. 98% Normal vs 15% Danger).
   * A button: *"Simulate Fault"* that immediately triggers a 60-minute S&T maintenance request in the schedule solver.
   * Waveform line chart showing simulated sensor telemetry over time.
4. **Tab 4: XAI Financial Router**
   * Select a train and simulate a broken track.
   * Shows the mathematical equation HUD.
   * Left side: Constraint check cards (Axle weight, electric catenary, capacity).
   * Right side: Step-by-step math expanders showing revenue, fuel/distance cost, delay penalty, and net profit.
   * Grouped bar chart comparing costs across all routes.
   * Table of all alternate tracks and their technical specifications.
5. **Tab 5: Authority Dispatch Order (Form T/409)**
   * In Indian Railways, when a track is closed or speed restrictions are put in place, the controller issues an official form called **Form T/409 (Caution Order)**.
   * This tab generates the text format of that order and gives you a button to download it as a `.txt` file.

---

## 5. Honest Critique: Why the Codebase & UI Feel Ugly and Cluttered

If you feel like the UI is "ugly and there are a bunch of buzz words that are completely unnecessary", you are 100% right. Here is an honest breakdown of why:

### 1. "Hackathon Syndrome" Visual Overkill
* **Too many neon colors:** Pink/crimson (`#f43f5e`), emerald green (`#10b981`), cyan (`#38bdf8`), purple (`#a855f7`), and amber (`#f59e0b`) are all fighting for attention on a single screen.
* **Too many badges and borders:** Almost every card has glowing borders, rounded tags, chips saying "OPTIMAL", "CONVERGED", "NOMINAL", "AI AUTONOMOUS DISPATCHER v3.2", "FAIL-SAFE DYNAMIC".
* Real railway control room software (like Siemens, Alstom, or Indian Railways TMS) is sober, high-contrast, clean, and legible, not a sci-fi video game HUD.

### 2. Excessive Jargon Where Simple English Works Better
* *"Autonomous Interlocking Dynamic CTC HUD"* $\to$ Should just be: **Section Operations Center**.
* *"Spatio-Temporal CP-SAT Optimization Solver Telemetry"* $\to$ Should just be: **Maintenance Slot Finder**.
* *"2-Stage CSPF Dynamic Financial Rerouting Engine"* $\to$ Should just be: **Train Diversion & Cost Evaluator**.

### 3. Layout Sprawl in `main_app.py`
* `main_app.py` grew to 800+ lines because HTML snippets, CSS styles, math calculations, and UI widgets are all in one giant file.
* Tabs have too much nested markdown and inline HTML tags (`<div class="ctc-panel">`, `<span>`, `<b style="color: ...">`) which makes editing or styling a pain.

---

## 6. Cleanup & Redesign Checklist (For Your Next Steps)

When you are ready to overhaul the UI and codebase, here is the recommended plan:

### Phase 1: Language & Copy Simplification
- [ ] Replace science-fiction buzzwords with authentic, professional railway terms or simple English.
- [ ] Change "AUTONOMOUS AI DISPATCHER v3.2" to "Centralized Traffic Control (CTC) Schedule Planner".
- [ ] Make card titles informative rather than theatrical (e.g., instead of "TRACK RECLAIMED INDEX", use "Track Outage Saved").

### Phase 2: Visual & CSS Modernization
- [ ] **Simplify the Color Palette:** Pick 2 primary colors (e.g. a deep Navy Blue/Slate background and clean Off-White text, with a single accent color like Indian Railways Maroon `#800000` or clean Cobalt `#2563eb`).
- [ ] **Drop the Inline HTML:** Replace hardcoded `<div style="...">` inside Python strings with native Streamlit widgets (`st.metric`, `st.container`, `st.dataframe`) or a clean external CSS file.
- [ ] **Reduce Visual Noise:** Remove unnecessary glowing borders and reduce the number of redundant stat chips.

### Phase 3: Code Modularization
- [ ] Move tab rendering logic out of `main_app.py` into separate UI modules (e.g., `ui/tab_marey.py`, `ui/tab_shadow_block.py`, `ui/tab_iot.py`, `ui/tab_financial_router.py`).
- [ ] Keep `main_app.py` under 100 lines as a clean controller that simply orchestrates the layout.

---

*This document is saved at `docs/study.md` for reference whenever you need to explain, present, or refactor the system.*
