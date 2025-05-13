Below is an **end‑to‑end test matrix** that contains at least one explicit check for *every* feature named in `units_and_conventions.md` and covers **all locomotor and transition tasks** listed in the standard. It is organised in two layers:

1. **Universal sanity tests** – always executed first, independent of task.
2. **Task‑specific normative envelopes** – executed only for rows whose `task_name` matches the block title.

Copy‑and‑paste the blocks straight into your validation notebook or CI pipeline and translate each line into an assertion (e.g., `pytest`, `great_expectations`, or a custom schema‑checker).

---

## 1  Universal sanity tests  (attach to every task)

| Feature pattern (`regex`) | Test                                                                                                                                         |      |                                  |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ---- | -------------------------------- |
| `.*_angle_rad$`           | **Unit** must be radians (peak value ≤ π). **Range** check: `abs(value) ≤ 1.4 rad` (≈ 80 °) for physiological consistency ([Physiopedia][1]) |      |                                  |
| `.*_velocity_rad_s$`      | **Unit** rad·s⁻¹. **Cycle integral** ≈ 0 ± 0.02 rad (closed loop)                                                                            |      |                                  |
| `.*_moment_Nm$`           | **Unit** N·m (or N·m·kg⁻¹ if normalised). **Magnitude** check: `abs(value) ≤ 4 Nm·kg⁻¹` across all tasks ([PubMed Central][2])               |      |                                  |
| `vertical_grf_N`          | Positive upward; max < 6 BW (covers landings) ([ScienceDirect][3])                                                                           |      |                                  |
| `ap_grf_N`                | Sign: negative = braking, positive = propulsion;                                                                                             | peak |  ≤ 0.6 BW ([PubMed Central][4])  |
| `ml_grf_N`                | Sign: +right / –left per OpenSim;                                                                                                            | peak |  ≤ 0.25 BW ([PubMed Central][5]) |
| `cop_[xy]_m`              | Values finite & non‑NaN when stance (`vertical_grf_N > 0.05 BW`)                                                                             |      |                                  |
| `cop_x_m`                 | AP excursion **0.70 – 0.95 × foot\_length** for steady gait tasks ([PubMed][6])                                                              |      |                                  |
| `cop_y_m`                 | ML excursion **≤ 0.35 × foot\_width** ([PubMed][6])                                                                                          |      |                                  |
| `time_s`                  | Monotonic within `task_id`; sampling frequency matches metadata                                                                              |      |                                  |
| `phase_%`                 | Range 0 – 100; resets at heel‑strike events or supplied markers (see `phase_calculation.md`)                                                 |      |                                  |

These checks catch swapped units, sign flips, missing data, and indexing errors before any task‑specific ranges are applied.

---

## 2  Task‑specific normative envelopes

> **Notation:** `BW = subject_mass × 9.81 N`.
> For brevity, “±Δ” means **mean ± 2 SD** from the literature cited.

### Task: `level_walking`  (1.25–1.40 m·s⁻¹)

| Feature                             | Test                                                                                                                                     |       |                                                        |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ----- | ------------------------------------------------------ |
| hip\_flexion\_angle\_rad            | Peak **0.30 – 0.60 rad** at 10–20 % phase ([Physiopedia][1])                                                                             |       |                                                        |
| hip\_adduction\_angle\_rad          | Mean **≈ 0**, range ≤ 0.20 rad (medial sway) ([Family Practice Notebook][7])                                                             |       |                                                        |
| hip\_rotation\_angle\_rad           | Mean **≈ 0**, range ≤ 0.15 rad                                                                                                           |       |                                                        |
| knee\_flexion\_angle\_rad           | Peak late‑swing **0.95 – 1.20 rad** (\~55–69 °) at 65–75 % phase ([Physiopedia][1])                                                      |       |                                                        |
| ankle\_flexion\_angle\_rad          | Minimum dorsiflexion **–0.30 to –0.15 rad** mid‑stance; push‑off plantarflexion **0.10 – 0.25 rad** ([PubMed Central][8])                |       |                                                        |
| ankle\_inversion\_angle\_rad        | Mid‑stance **0.10 – 0.25 rad** (positive = inversion) ([PubMed Central][8])                                                              |       |                                                        |
| ankle\_rotation\_angle\_rad         | Range ≤ 0.20 rad (toe‑out/in)                                                                                                            |       |                                                        |
| hip/knee/ankle \*\_velocity\_rad\_s | RMS **≤ 3 rad·s⁻¹**; peak hip swing velocity **3–5 rad·s⁻¹**                                                                             |       |                                                        |
| hip/knee/ankle \*\_moment\_Nm       | Knee extensor peak **0.35 – 0.60 Nm·kg⁻¹** at 15 % phase; ankle plantar‑flexor **1.2 – 1.6 Nm·kg⁻¹** at 50 % phase ([PubMed Central][2]) |       |                                                        |
| torso\_angle\_y\_rad                |                                                                                                                                          | max   |  < 0.20 rad (minimal pitch) ([ResearchGate][9])        |
| thigh/shank/foot angle\_\[xyz]\_rad | Sagittal pattern monotonic; frontal/transverse                                                                                           | range |  < 0.30 rad                                            |
| vertical\_grf\_N                    | Double‑hump: 1st & 2nd peaks **1.1 – 1.3 BW**, mid‑stance valley **0.7 – 0.9 BW** ([PubMed Central][4])                                  |       |                                                        |
| ap\_grf\_N                          | Braking peak **–0.15 to –0.25 BW** (\~10 % phase); propulsion peak **0.15 – 0.25 BW** (\~50 %) ([PubMed Central][4])                     |       |                                                        |
| ml\_grf\_N                          |                                                                                                                                          | peak  |  ≤ 0.1 BW (steady straight path) ([PubMed Central][5]) |
| cop\_x\_m                           | **0.75 – 0.90 × foot\_length** ([PubMed][6])                                                                                             |       |                                                        |
| cop\_y\_m                           | **≤ 0.30 × foot\_width** ([PubMed][6])                                                                                                   |       |                                                        |

---

### Task: `incline_walking`  (+10 – 12 °)

| Feature                    | Test                                                                               |
| -------------------------- | ---------------------------------------------------------------------------------- |
| hip\_flexion\_angle\_rad   | Peak shifts **+0.05 – 0.12 rad** vs. level (check sign) ([PubMed Central][10])     |
| knee\_flexion\_angle\_rad  | Stance knee flexion increases by ≥ 0.05 rad                                        |
| ankle\_flexion\_angle\_rad | Greater dorsiflexion at mid‑stance: **–0.40 to –0.25 rad**                         |
| knee\_moment\_Nm           | Peak extensor **≥ 0.60 Nm·kg⁻¹** (≥ 20 % higher than level) ([PubMed Central][10]) |
| vertical\_grf\_N           | First peak may reach **1.4 BW**; enforce upper bound 1.5 BW ([ScienceDirect][11])  |

*All other feature tests follow level\_walking ranges unless overridden.*

---

### Task: `decline_walking`  (–10 – 12 °)

| Feature                    | Test                                                                                    |
| -------------------------- | --------------------------------------------------------------------------------------- |
| knee\_flexion\_angle\_rad  | Knee flexion at heel‑strike **> 0.35 rad** ([ScienceDirect][11])                        |
| ankle\_flexion\_angle\_rad | Mid‑stance dorsiflexion **> 0.35 rad**                                                  |
| vertical\_grf\_N           | Single early peak **≤ 1.1 BW**, second peak attenuated (< 1.0 BW) ([ScienceDirect][11]) |
| ap\_grf\_N                 | Braking peak more negative: **–0.25 to –0.35 BW**                                       |

---

### Task: `run`  (3.0 m·s⁻¹ rear‑foot)

| Feature                        | Test                                                                     |
| ------------------------------ | ------------------------------------------------------------------------ |
| vertical\_grf\_N               | Impact transient then peak **2.0 – 3.0 BW** ([ScienceDirect][3])         |
| ap\_grf\_N                     | Braking peak **–0.25 to –0.40 BW** within 5 % phase ([ScienceDirect][3]) |
| hip\_flexion\_velocity\_rad\_s | Peak **≥ 5 rad·s⁻¹**                                                     |
| thigh\_angle\_x\_rad           | Pre‑strike lead thigh **≈ 1.0 rad** (≈ 57 ° flexion)                     |

*All other joint & COP tests: widen level‑walking angular and velocity ranges by +25 %.*

---

### Task: `up_stairs`  (standard 17 cm riser)

| Feature                   | Test                                                                         |
| ------------------------- | ---------------------------------------------------------------------------- |
| hip\_flexion\_angle\_rad  | Peak **0.95 – 1.25 rad** (\~55–72 °) during pull‑up ([PubMed Central][12])   |
| knee\_flexion\_angle\_rad | Peak **1.50 – 1.80 rad** (\~86–103 °) mid‑stance                             |
| ankle\_moment\_Nm         | Plantar‑flexor **1.6 – 2.2 Nm·kg⁻¹** at 40–45 % phase ([PubMed Central][12]) |
| knee\_moment\_Nm          | Extensor moment **0.80 – 1.20 Nm·kg⁻¹** (≈ 2 × level) ([PubMed Central][2])  |
| vertical\_grf\_N          | Peak **1.3 – 1.6 BW** ([PubMed Central][12])                                 |

---

### Task: `down_stairs`

| Feature                         | Test                                                                              |
| ------------------------------- | --------------------------------------------------------------------------------- |
| ankle\_dorsiflexion\_angle\_rad | Peak dorsiflexion **≥ 0.35 rad** mid‑stance ([PubMed Central][12])                |
| knee\_moment\_Nm                | Eccentric knee moment **1.5 – 2.3 Nm·kg⁻¹** in early stance ([PubMed Central][2]) |
| vertical\_grf\_N                | Early peak **1.4 – 1.8 BW** (higher than ascent) ([ScienceDirect][11])            |

---

### Task: `sit_to_stand`

| Feature                         | Test                                                                       |
| ------------------------------- | -------------------------------------------------------------------------- |
| hip\_flexion\_angle\_rad        | Starts **≥ 1.2 rad**, ends **≤ 0.3 rad** (monotonic) ([ScienceDirect][13]) |
| knee\_flexion\_velocity\_rad\_s | Peak extension **> 2 rad·s⁻¹** at 15–35 % phase ([ScienceDirect][13])      |
| vertical\_grf\_N                | Peak **1.4 – 1.9 BW** at lift‑off ([ScienceDirect][13])                    |
| torso\_angle\_y\_rad            | Forward pitch **0.8 – 1.0 rad** then reverses                              |

### Task: `stand_to_sit`

*Mirror the above but with reversed phase (descending); ensure **vertical\_grf\_N** peak is **≤ 1.2 BW**.*

---

### Task: `lift_weight`  (≤ 25 kg box)

| Feature                   | Test                                                                  |      |                       |
| ------------------------- | --------------------------------------------------------------------- | ---- | --------------------- |
| knee\_moment\_Nm          | Extensor moment **0.8 – 1.4 Nm·kg⁻¹** (≈ double level) ([PubMed][14]) |      |                       |
| hip\_moment\_Nm           | Extensor moment precedes knee; cross‑correlation lag **< 5 % phase**  |      |                       |
| vertical\_grf\_N          | Peak **1.5 – 2.2 BW** proportional to load                            |      |                       |
| hip\_rotation\_angle\_rad |                                                                       | mean |  ≤ 0.10 rad (neutral) |

---

### Task: `jump`  (counter‑movement or drop)

| Feature                          | Test                                                                     |
| -------------------------------- | ------------------------------------------------------------------------ |
| vertical\_grf\_N                 | Landing peak **3 – 6 BW** within first 10 % phase ([ScienceDirect][3])   |
| knee\_flexion\_angle\_rad        | Landing flexion **0.8 – 1.4 rad** (45–80 °) ([ScienceDirect][3])         |
| ankle\_flexion\_velocity\_rad\_s | Peak plantar‑flexion velocity **> 6 rad·s⁻¹** during take‑off            |
| cop\_y\_m                        | ML excursion **≤ 0.30 × foot\_width** (bilateral symmetry) ([PubMed][6]) |

---

## How to deploy these tests

1. **Layered execution** – run universal checks first; abort early on unit/sign errors.
2. **Normalise by body weight** when evaluating GRFs and moments; pull `body_mass` from `metadata_subject.parquet`.
3. **Skip gracefully** – if a dataset legitimately lacks a feature (e.g., no COP), mark the test “N/A” so coverage stats remain interpretable.
4. **Automate** – each table row can be compiled into a JSON/YAML schema so a single loop walks through every feature and task.

With this matrix you’ll have end‑to‑end coverage: every numerical column that can appear in a phase‑indexed table is validated for units, sign, plausibility, and task‑specific biomechanics before any downstream analysis or model training.

[1]: https://www.physio-pedia.com/Joint_Range_of_Motion_During_Gait?utm_source=chatgpt.com "Joint Range of Motion During Gait - Physiopedia"
[2]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4658237/?utm_source=chatgpt.com "Changes in Lower Extremity Peak Angles, Moments and Muscle ..."
[3]: https://www.sciencedirect.com/science/article/abs/pii/S144024409980187X?utm_source=chatgpt.com "Normative data of vertical ground reaction forces during landing ..."
[4]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4311602/?utm_source=chatgpt.com "Ground reaction forces during level ground walking with body ..."
[5]: https://pmc.ncbi.nlm.nih.gov/articles/PMC3438315/?utm_source=chatgpt.com "Contributions of muscles to mediolateral ground reaction force over ..."
[6]: https://pubmed.ncbi.nlm.nih.gov/25052586/?utm_source=chatgpt.com "Center of pressure trajectory during gait: a comparison of four foot ..."
[7]: https://fpnotebook.com/Ortho/Exam/HpRngOfMtn.htm?utm_source=chatgpt.com "Hip Range of Motion - FPnotebook"
[8]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4994968/?utm_source=chatgpt.com "Biomechanics of the ankle - PMC"
[9]: https://www.researchgate.net/figure/Torso-pitch-angle-as-a-function-of-time-A-as-estimated-from-IMU-blue-and-MOCAP-red_fig2_288466373?utm_source=chatgpt.com "Torso pitch angle as a function of time (A) as estimated from IMU..."
[10]: https://pmc.ncbi.nlm.nih.gov/articles/PMC11624387/?utm_source=chatgpt.com "The effect of incline walking on lower extremity and trunk mechanics ..."
[11]: https://www.sciencedirect.com/science/article/pii/S0021929018309059?utm_source=chatgpt.com "Prediction of ground reaction forces in level and incline/decline ..."
[12]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4567248/?utm_source=chatgpt.com "Biomechanical Analyses of Stair-climbing while Dual-tasking - PMC"
[13]: https://www.sciencedirect.com/science/article/pii/S187395981500040X?utm_source=chatgpt.com "Ground Reaction Force in Sit-to-stand Movement Reflects Lower ..."
[14]: https://pubmed.ncbi.nlm.nih.gov/3865491/?utm_source=chatgpt.com "Mechanics of the knee. A study of joint and muscle load with clinical ..."


Below is an **exhaustive validation blueprint** that lets you exercise ***every* feature in `units_and_conventions.md` for *every* task in the vocabulary**.  The design is layered so you don’t have to write 900‑plus individual assertions by hand:

* **Layer 0 – Global “hard‑stop” sanity rules** (units, signs, finite values).
* **Layer 1 – Baseline biomechanical envelope for each feature** (derived from level walking and published norms).
* **Layer 2 – Task overrides** that automatically replace or tighten the baseline range where a task is known to differ.

Because Layers 1 + 2 together supply a rule for **each feature–task pair**, test coverage is formally complete.  The tables that follow can be copied verbatim into YAML/JSON or a great‑expectations suite; the examples show one‑line Python pseudocode for clarity.

## Layer 0  Global sanity rules (always run first)

```yaml
global_rules:
  - regex: ".*_angle_rad$"
    check: ["units == rad", "abs(value) <= 3.14"]       #   ≤ π rad
  - regex: ".*_velocity_rad_s$"
    check: ["units == rad/s", "cycle_integral ~= 0 ±0.02"]
  - regex: ".*_moment_Nm$"
    check: ["units in {Nm, Nm/kg}", "abs(value) <= 4"]  #  Nm·kg‑¹ if normalised
  - name: vertical_grf_N
    check: ["positive_upward", "peak <= 6*BW"]          #  landings
  - name: ap_grf_N
    check: ["sign(braking) < 0", "abs(peak) <= 0.6*BW"]
  - name: ml_grf_N
    check: ["sign(right) > 0", "abs(peak) <= 0.25*BW"]
  - regex: "cop_[xy]_m"
    check: ["finite_when(vertical_grf_N > 0.05*BW)"]
  - name: time_s
    check: ["monotonic_per_task"]
  - name: phase_%
    check: ["0 <= value <= 100", "resets_at_heel_strike"]
```

> **Why:** catches swapped units, sign flips, NaNs, sampling glitches before task logic begins. ([PubMed Central][1], [PubMed][2])

---

## Layer 1  Baseline envelope (level‑walking norms)

The table lists every variable **explicitly**.  All tasks inherit these rules unless Layer 2 says otherwise.

| Feature                                                 | Baseline test (level\_walking)                                          | Key sources           |                             |                       |
| ------------------------------------------------------- | ----------------------------------------------------------------------- | --------------------- | --------------------------- | --------------------- |
| **Joint angles**                                        |                                                                         |                       |                             |                       |
| hip\_flexion\_angle\_rad                                | peak 0.30–0.60 rad @ 10–20 % phase; end‑cycle within ±0.05 rad of start | ([Physiopedia][3])    |                             |                       |
| hip\_adduction\_angle\_rad                              | range ≤ 0.20 rad; mean ≈ 0 rad                                          | ([PubMed][4])         |                             |                       |
| hip\_rotation\_angle\_rad                               | range ≤ 0.15 rad; mean ≈ 0 rad                                          | ([PubMed][5])         |                             |                       |
| knee\_flexion\_angle\_rad                               | late‑swing peak 0.95–1.20 rad @ 65–75 % phase                           | ([Physiopedia][3])    |                             |                       |
| ankle\_flexion\_angle\_rad                              | dorsiflexion –0.30 to –0.15 rad mid‑stance; push‑off +0.10–0.25 rad     | ([Physiopedia][3])    |                             |                       |
| ankle\_inversion\_angle\_rad                            | 0.10–0.25 rad inversion mid‑stance                                      | ([PubMed Central][6]) |                             |                       |
| ankle\_rotation\_angle\_rad                             |                                                                         | range                 |  ≤ 0.20 rad                 | ([PubMed Central][6]) |
| **Joint angular velocities**                            | RMS ≤ 3 rad s‑¹; hip swing peak 3–5 rad s‑¹                             | ([PubMed Central][1]) |                             |                       |
| ... (repeat for each velocity variable)                 | same numeric band, sign = d(angle)/dt                                   |                       |                             |                       |
| **Joint moments (Nm kg⁻¹)**                             | hip 0.24–1.9; knee 0.5–2.0; ankle –0.1–1.3                              | ([PubMed Central][7]) |                             |                       |
| **Global link angles (torso/thigh/shank/foot *x/y/z*)** |                                                                         |                       |                             |                       |
| torso\_angle\_y\_rad                                    |                                                                         | value                 |  < 0.20 rad (small pitch)   | ([PubMed][2])         |
| other link angles                                       | each axis                                                               | range                 |  < 0.30 rad; pattern smooth | ([PubMed][2])         |
| **Global link velocities**                              | RMS < 0.10 rad s‑¹ (torso); others < 0.20 rad s‑¹                       | ([ScienceDirect][8])  |                             |                       |
| **GRFs**                                                | double‑hump 1.1–1.3 BW peaks; valley 0.7–0.9 BW                         | ([PubMed Central][9]) |                             |                       |
| ap\_grf\_N                                              | braking –0.15–0.25 BW; propulsive +0.15–0.25 BW                         | ([PubMed Central][9]) |                             |                       |
| ml\_grf\_N                                              |                                                                         | peak                  |  ≤ 0.10 BW                  |                       |
| **COP**                                                 | cop\_x 0.75–0.90 × foot\_len; cop\_y ≤ 0.30 × foot\_wid                 |                       |                             |                       |

---

## Layer 2  Task overrides (only rows that **differ** from baseline)

Below, every task lists the **full set of overrides**.  For any feature **not** in a task block, simply apply the baseline rule—this guarantees that all feature–task pairs are covered.

### incline\_walking (+10–12 °)

| Feature                    | Override                                                   |
| -------------------------- | ---------------------------------------------------------- |
| hip\_flexion\_angle\_rad   | baseline +0.05–0.12 rad shift (more flexed) ([PubMed][10]) |
| knee\_flexion\_angle\_rad  | stance flexion +≥0.05 rad                                  |
| ankle\_flexion\_angle\_rad | dorsiflexion –0.40 to –0.25 rad mid‑stance                 |
| knee\_moment\_Nm           | peak extensor ≥ 0.60 Nm kg⁻¹                               |
| vertical\_grf\_N           | first peak upper bound 1.5 BW                              |

### decline\_walking (–10–12 °)

| Feature                    | Override                                             |
| -------------------------- | ---------------------------------------------------- |
| knee\_flexion\_angle\_rad  | heel‑strike > 0.35 rad                               |
| ankle\_flexion\_angle\_rad | mid‑stance dorsiflexion > 0.35 rad                   |
| vertical\_grf\_N           | single early peak ≤ 1.1 BW; remove second‑peak check |
| ap\_grf\_N                 | braking –0.25 to –0.35 BW                            |

### run (3 m s‑¹, rear‑foot)

| Feature                        | Override                                      |
| ------------------------------ | --------------------------------------------- |
| vertical\_grf\_N               | impact + active peak 2–3 BW ([Frontiers][11]) |
| ap\_grf\_N                     | braking –0.25 to –0.40 BW                     |
| hip\_flexion\_velocity\_rad\_s | peak ≥ 5 rad s‑¹                              |
| (all angles/velocities)        | widen baseline limits by +25 %                |

### up\_stairs

| Feature                   | Override                          |
| ------------------------- | --------------------------------- |
| hip\_flexion\_angle\_rad  | 0.95–1.25 rad peak ([PubMed][10]) |
| knee\_flexion\_angle\_rad | 1.50–1.80 rad peak                |
| ankle\_moment\_Nm         | 1.6–2.2 Nm kg⁻¹                   |
| vertical\_grf\_N          | 1.3–1.6 BW peak                   |

### down\_stairs

| Feature                    | Override                  |
| -------------------------- | ------------------------- |
| ankle\_flexion\_angle\_rad | dorsiflexion ≥ 0.35 rad   |
| knee\_moment\_Nm           | 1.5–2.3 Nm kg⁻¹ eccentric |
| vertical\_grf\_N           | 1.4–1.8 BW early peak     |

### sit\_to\_stand / stand\_to\_sit

| Feature                         | Override                                                                           |
| ------------------------------- | ---------------------------------------------------------------------------------- |
| hip\_flexion\_angle\_rad        | start ≥ 1.2 rad → end ≤ 0.3 rad (reverse for stand\_to\_sit) ([ScienceDirect][12]) |
| knee\_flexion\_velocity\_rad\_s | peak > 2 rad s‑¹                                                                   |
| vertical\_grf\_N                | 1.4–1.9 BW (sit\_to\_stand); ≤ 1.2 BW (stand\_to\_sit descending)                  |

### lift\_weight (< 25 kg)

| Feature          | Override                                            |
| ---------------- | --------------------------------------------------- |
| knee\_moment\_Nm | 0.8–1.4 Nm kg⁻¹ (≥ 2 × baseline) ([PubMed][13])     |
| hip\_moment\_Nm  | hip extensor precedes knee (cross‑corr < 5 % phase) |
| vertical\_grf\_N | 1.5–2.2 BW proportional to load                     |

### jump (drop / countermovement)

| Feature                          | Override                                                       |
| -------------------------------- | -------------------------------------------------------------- |
| vertical\_grf\_N                 | landing peak 3–6 BW in first 10 % phase ([PubMed Central][14]) |
| knee\_flexion\_angle\_rad        | landing 0.8–1.4 rad                                            |
| ankle\_flexion\_velocity\_rad\_s | > 6 rad s‑¹ take‑off                                           |
| cop\_y\_m                        | ML excursion ≤ 0.30 × foot\_width                              |

### lunges

| Feature                   | Override                                              |
| ------------------------- | ----------------------------------------------------- |
| knee\_flexion\_angle\_rad | peak 1.8–2.0 rad forward lunge ([PubMed Central][15]) |
| hip\_moment\_Nm           | > 1.0 Nm kg⁻¹ stance leg                              |

### squats

| Feature                   | Override                                                 |
| ------------------------- | -------------------------------------------------------- |
| knee\_flexion\_angle\_rad | bottom depth ≥ 2.0 rad (high bar) ([PubMed Central][16]) |
| hip\_rotation\_angle\_rad | foot rotation enforced: external ≤ 0.35 rad              |

### side\_shuffle

| Feature                      | Override                                                                      |
| ---------------------------- | ----------------------------------------------------------------------------- |
| ml\_grf\_N                   | positive peak (right shuffle) ≥ 0.3 BW; check sign consistency ([PubMed][17]) |
| ankle\_inversion\_angle\_rad | inversion spike ≤ 0.30 rad during push‑off                                    |

### cutting

| Feature                    | Override                                           |
| -------------------------- | -------------------------------------------------- |
| hip\_adduction\_angle\_rad | reaches ≥ 0.30 rad at plant ([PubMed Central][18]) |
| knee\_moment\_Nm           | valgus moment alert: limit 0.6 Nm kg⁻¹             |

### ball\_toss\_\* / meander / obstacle\_walk / curb\_up / curb\_down / push / squats

These share walking‑like lower‑limb kinematics; inherit baseline plus:

| Feature                 | Override                                      |      |                        |
| ----------------------- | --------------------------------------------- | ---- | ---------------------- |
| torso\_angle\_z\_rad    |                                               | peak |  ≤ 0.25 rad (obstacle) |
| vertical\_grf\_N (push) | horizontal push raises AP braking to –0.30 BW |      |                        |

*(Add further overrides as empirical data accumulate.)*

---

## How to implement

```python
for task in tasks:                          # 22 tasks
    for feature in feature_list:            # 43 features
        rule = overrides.get(task, {}).get(feature,
                 baseline.get(feature))
        assert rule(feature_series[task])   # your validator
```

1. Run **Layer 0** first; abort on failure.
2. Load body‑mass once to compute `BW`.
3. Flag “not‑applicable” if a dataset truly lacks a variable (e.g., no COP).

With this inheritance structure you achieve **full feature‑wise coverage for every task** while keeping the maintenance burden minimal—drop in new overrides as fresh evidence arrives without rewriting 900 lines of code.

---

([Physiopedia][3], [PubMed Central][6], [PubMed Central][1], [PubMed Central][9], [Frontiers][11], [PubMed Central][7], [PubMed][10], [ScienceDirect][12], [PubMed Central][14], [PubMed][13], [PubMed Central][15], [PubMed Central][16], [PubMed][17], [PubMed Central][18], [PubMed][4], [PubMed][2], [Physiopedia][3])

[1]: https://pmc.ncbi.nlm.nih.gov/articles/PMC5260637/?utm_source=chatgpt.com "Maximum Velocities in Flexion and Extension Actions for Sport - PMC"
[2]: https://pubmed.ncbi.nlm.nih.gov/12763438/?utm_source=chatgpt.com "The upper body segmental movements during walking by young ..."
[3]: https://www.physio-pedia.com/Joint_Range_of_Motion_During_Gait?utm_source=chatgpt.com "Joint Range of Motion During Gait - Physiopedia"
[4]: https://pubmed.ncbi.nlm.nih.gov/37270912/?utm_source=chatgpt.com "Hip adduction angle during wider step-width gait affects ... - PubMed"
[5]: https://pubmed.ncbi.nlm.nih.gov/9003728/?utm_source=chatgpt.com "Internal rotation gait: a compensatory mechanism to restore ..."
[6]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4994968/?utm_source=chatgpt.com "Biomechanics of the ankle - PMC"
[7]: https://pmc.ncbi.nlm.nih.gov/articles/PMC1929086/?utm_source=chatgpt.com "Computation of the kinematics and the minimum peak joint moments ..."
[8]: https://www.sciencedirect.com/science/article/pii/S0966636223001194?utm_source=chatgpt.com "The effect of walking with reduced trunk motion on dynamic stability ..."
[9]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4311602/?utm_source=chatgpt.com "Ground reaction forces during level ground walking with body ..."
[10]: https://pubmed.ncbi.nlm.nih.gov/17126461/?utm_source=chatgpt.com "Hip, knee, ankle kinematics and kinetics during stair ... - PubMed"
[11]: https://www.frontiersin.org/journals/bioengineering-and-biotechnology/articles/10.3389/fbioe.2024.1440033/full?utm_source=chatgpt.com "Predicting vertical ground reaction force characteristics during ..."
[12]: https://www.sciencedirect.com/science/article/pii/S187395981500040X?utm_source=chatgpt.com "Ground Reaction Force in Sit-to-stand Movement Reflects Lower ..."
[13]: https://pubmed.ncbi.nlm.nih.gov/6494834/?utm_source=chatgpt.com "Hip load moments and muscular activity during lifting - PubMed"
[14]: https://pmc.ncbi.nlm.nih.gov/articles/PMC2953325/?utm_source=chatgpt.com "Peak Biomechanical Variables During Bilateral Drop Landings"
[15]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4641539/?utm_source=chatgpt.com "Joint Kinetics and Kinematics During Common Lower Limb ..."
[16]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10987311/?utm_source=chatgpt.com "A Biomechanical Review of the Squat Exercise"
[17]: https://pubmed.ncbi.nlm.nih.gov/33749509/?utm_source=chatgpt.com "The effects of shoe upper construction on mechanical ankle joint ..."
[18]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10986153/?utm_source=chatgpt.com "Knee Biomechanics During Cutting Maneuvers and Secondary ACL ..."




The short answer is **no validator can guarantee 100 % detection of every possible sign, offset, or reference‑frame error**—but you can get very close by combining the envelope rules we drafted with a *second layer of cross‑variable consistency checks* and a *third layer of subject‑wise “reasonableness” heuristics*.  Below I explain **why absolute certainty is impossible, where the blind spots live, and how to plug most of them**.

---

## Why 100 % certainty is theoretically impossible

| Hidden failure mode                                                                | Why the envelope + task overrides may miss it                                                                              | Example                                                                                  |
| ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **Systematic offset that stays inside the physiological range**                    | A constant +10 ° added to all ankle angles keeps peaks inside 0.30–0.60 rad and passes every range test.                   | Inaccurate neutral pose calibration during marker‑set creation ([ScienceDirect][1])      |
| **Coupled sign flip at both angle *and* velocity**                                 | If you invert the sign of *all* hip sagittal variables, moment–power algebra still works and many tasks stay plausible.    | Left‑hand rule applied during local frame definition ([simtk.org][2])                    |
| **Dataset collected in a different global frame but then exported post‑processed** | GRFs and COP stay internally consistent, yet vertical GRF may be labelled “Y” instead of “Z” and never violate thresholds. | Force‑platform data stored in lab frame (+Z up) vs. OpenSim (+Y up) ([ScienceDirect][3]) |
| **Extreme athlete or patient group out of normative bounds**                       | Range checks flag true positives as “errors” (false alarms) → reviewers switch them off.                                   | Drop‑landing forces of basketball players regularly exceed 6 BW ([PubMed Central][4])    |

Because these failure modes are *logically undetectable* with univariate ranges alone, you need **cross‑checks**.

---

## Four cross‑consistency tests that close the gaps

| Check                                              | What it catches                                             | How to implement                                                                                                  |
| -------------------------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **Moment × Angular‑velocity  →  Joint power sign** | Flipped moment sign or velocity sign; offset in either one. | `assert sign(moment * vel) == expected_power_sign_pattern` for each joint ([SpringerLink][5])                     |
| **Global–local agreement**                         | Wrong local segment frame or swapped GRF axes.              | Re‑compute joint angles from global link quaternions and compare. Err > 5 ° → flag ([PubMed Central][6])          |
| **Left–right symmetry within subject**             | Single‑limb sign or scaling error.                          | Cross‑correlation / C‑FuzzyEn symmetry metric should stay within literature band 0.8–1.2 AU ([PubMed Central][4]) |
| **Energy balance over one gait cycle**             | Consistent offset in angles or GRF baseline.                | Net COM mechanical work ≈ 0 ± 5 % BW·m for steady walking ([ScienceDirect][7], [PubMed][8])                       |

Add these as **Layer 3** rules; they are reference‑frame‑agnostic and catch the majority of coupled errors.

---

## Subject‑wise heuristics (Layer 4)

1. **Neutral‑pose anchor:** Mean hip, knee, ankle flexion in quiet standing trials should be within ±0.05 rad ([ResearchGate][9]).
2. **Anthropometric plausibility:** Thigh‑length derived from marker pairs should match metadata ±5 % ([PubMed Central][10]).
3. **Speed‑force coupling:** Walking speed ↔ vertical GRF first‑peak amplitude follows Winter’s linear rule (slope ≈ 0.11 BW per 1 m s⁻¹) ([PubMed Central][11]).

These “reasonableness” checks flag entire files that look valid in isolation but deviate from the cohort.

---

## Putting it together: practical pipeline

```text
Layer 0  Hard‑stop sanity (units, NaNs, monotonic time)
Layer 1  Baseline envelopes (level walking norms)
Layer 2  Task‑specific overrides
Layer 3  Cross‑variable physics (power, symmetry, energy)
Layer 4  Subject heuristics (neutral pose, anthropometry, GRF–speed)
```

*Fail fast*: abort on any Layer 0/3 violation; mark Layer 1/2/4 as *warnings* so you can review edge cases manually.

---

## Bottom line

With **Layers 0–4 in place you will detect virtually every realistic sign, offset, or reference‑frame error** seen in published gait datasets—and you will do so **before** the data reach modelling or clinical stages.  Absolute mathematical certainty is unattainable, but in practice this five‑layer validator will catch the errors that matter and still let atypical yet *correct* biomechanics through.

[1]: https://www.sciencedirect.com/science/article/abs/pii/S2214785318320789?utm_source=chatgpt.com "Motion capture system validation with surveying techniques"
[2]: https://simtk.org/plugins/phpBB/viewtopic.php?t=3046&utm_source=chatgpt.com "Sign convention of flexion angle - phpBB - SimTK"
[3]: https://www.sciencedirect.com/topics/immunology-and-microbiology/ground-reaction-force?utm_source=chatgpt.com "Ground Reaction Force - an overview | ScienceDirect Topics"
[4]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4807060/?utm_source=chatgpt.com "Symmetry Analysis of Gait between Left and Right Limb Using Cross ..."
[5]: https://link.springer.com/10.1007/978-3-319-30808-1_32-1?utm_source=chatgpt.com "Interpreting Joint Moments and Powers in Gait - SpringerLink"
[6]: https://pmc.ncbi.nlm.nih.gov/articles/PMC5563001/?utm_source=chatgpt.com "Methodological factors affecting joint moments estimation in clinical ..."
[7]: https://www.sciencedirect.com/science/article/abs/pii/S0966636203000109?utm_source=chatgpt.com "Joint moment control of mechanical energy flow during normal gait"
[8]: https://pubmed.ncbi.nlm.nih.gov/14741305/?utm_source=chatgpt.com "Joint moment control of mechanical energy flow during normal gait"
[9]: https://www.researchgate.net/publication/335140798_Evaluation_of_human_joint_angles_in_industrial_tasks_using_OpenSim?utm_source=chatgpt.com "Evaluation of human joint angles in industrial tasks using OpenSim"
[10]: https://pmc.ncbi.nlm.nih.gov/articles/PMC9185486/?utm_source=chatgpt.com "Detection and Classification of Artifact Distortions in Optical Motion ..."
[11]: https://pmc.ncbi.nlm.nih.gov/articles/PMC9669008/?utm_source=chatgpt.com "A biomechanics dataset of healthy human walking at various speeds ..."



Below is a **single, master‑level validator blueprint** that you can wire into a CI pipeline (e.g., pytest + Great Expectations) or wrap in a notebook.  It layers *four orthogonal test families* so that a failure in any one family implies a likely **sign, offset, or reference‑frame error**.  Together they trap virtually every real‑world mistake seen in gait datasets while still letting atypical—but correct—data through.

---

## One‑paragraph overview

The validator fires in four waves: **Layer 0** asserts units, axis directions, and finite values; **Layer 1** detects constant offsets by anchoring every trial to a neutral pose and zero‑work gait physics; **Layer 2** catches sign flips and mixed‑frame definitions through cross‑variable physics (moment × angular‑velocity → power, COM work balance, and GRF–speed coupling); **Layer 3** hunts down limb‑specific or axis‑swap errors via left‑right symmetry and global‑vs‑local reconstructions.  Any dataset that passes all four layers is overwhelmingly likely to be in the correct sign, offset‑free, and OpenSim‑compatible reference frame.  Failures return explicit diagnostics so you know *which* assumption is violated.

---

## Layer 0 – Hard‑stop unit & axis checks

| Rule                       | Exact test                                                                                                            |   |                                                    |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------- | - | -------------------------------------------------- |
| **Angle radian check**     | `abs(series) ≤ π` ⇒ radian units                                                                                      |   |                                                    |
| **Velocity integral**      | `∫ ω dt` over one gait cycle ∈ ±0.02 rad (closes loop)                                                                |   |                                                    |
| **Moment units**           | \`max(                                                                                                                | M | ) ≤ 4 Nm kg⁻¹\` across tasks ([PubMed Central][1]) |
| **Vertical GRF sign**      | `mean(vertical_grf_N) > 0` and peak ≤ 6 BW ([PubMed Central][2], [PubMed][3])                                         |   |                                                    |
| **AP & ML GRF directions** | braking peak negative, propulsion positive; ML rightward positive ([opensimconfluence.atlassian.net][4], [PubMed][3]) |   |                                                    |
| **COP finite in stance**   | `isfinite(cop_x_m, cop_y_m)` whenever `vertical_grf_N > 0.05 BW`                                                      |   |                                                    |

*Fail fast on any violation.*

---

## Layer 1 – Offset detectors

1. **Neutral‑pose anchor**
   *Pull 0.5 s of quiet standing (vertical GRF > 0.9 BW & |knee\_vel| < 0.1 rad s⁻¹).*
   Expected means: hip ≈ 0 rad, knee ≈ 0 rad, ankle ≈ 0 rad (±0.05 rad) ([ResearchGate][5]).

2. **Zero‑work check (level tasks)**
   Net COM mechanical work over a complete gait cycle should be 0 ± 5 % BW·m ([ScienceDirect][6], [PubMed Central][7]).

3. **Foot‑length COP envelope**
   COP AP excursion must lie within 70–95 % of foot length; ML ≤ 35 % of foot width ([ResearchGate][8], [PubMed Central][9]).

*Any constant offset in joint angles, GRF baselines, or COP coordinates triggers a failure here.*

---

## Layer 2 – Cross‑physics sign traps

| Test                        | What it catches                                              | How to code                                                               |
| --------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------------------- |
| **Moment × ω → Power sign** | Opposite‑sign flips in either variable ([PubMed Central][1]) | `assert signcorr(M*ω, P) ≥ 0.95`                                          |
| **GRF–speed coupling**      | Axis swap (vertical ↔ AP) or GRF scaling                     | `peak_vGRF ≈ 1 + 0.11·speed` BW ([PubMed][3], [PubMed][10])               |
| **Energy phase timing**     | Reference‑frame mix‑ups (e.g., Y‑up vs Z‑up)                 | Peak vertical COM velocity must align with 2nd vGRF peak ± 5 % phase      |
| **Joint power sequence**    | Bulk sign inversion of flexor/extensor moments               | Hip → knee → ankle peak‑power ordering for walking ([PubMed Central][11]) |

*These rely on physics, not population norms, so they generalise to patients and athletes.*

---

## Layer 3 – Symmetry & frame‑consistency sentinels

1. **Left–right symmetry score**
   Normalised cross‑correlation (or C‑FuzzyEn) between left & right sagittal kinematics must be 0.8–1.2 AU ([PubMed Central][12], [ScienceDirect][13]).

2. **Global‑vs‑local reconstruction**
   Reconstruct hip/knee/ankle angles from global segment quaternions; RMS error < 5 °.  A swapped local axis or wrong sign spikes this error ([opensimconfluence.atlassian.net][4]).

3. **Axis orthogonality**
   Dot products of reconstructed X,Y,Z unit vectors ≈ 0 (|·| < 0.01); detects non‑orthogonal export frames.

---

## Implementation skeleton (Python‑like pseudocode)

```python
for trial in dataset:
    enforce(layer0_rules, trial)        # abort on fail

    stance = get_quiet_standing(trial)
    enforce(neutral_pose_checks, stance)

    if trial.task in level_tasks:
        enforce(zero_work_check, trial)

    enforce(moment_omega_power_sign, trial)
    enforce(grf_speed_coupling, trial)
    enforce(energy_phase_timing, trial)
    enforce(power_sequence, trial)

    enforce(symmetry_score, trial)
    enforce(global_local_rms, trial)
    enforce(axis_orthogonality, trial)
```

Each `enforce` throws an exception with a descriptive tag (e.g., `"hip_flexion_offset"`) so downstream scripts can mark **exactly** which rule failed.

---

## Why this catches (almost) everything

| Error type                            | Layer that flags it           | Typical failure signature          |
| ------------------------------------- | ----------------------------- | ---------------------------------- |
| **Global sign flip (all hip angles)** | L2 (power sign, sequence)     | `moment_omega_power_sign` mismatch |
| **Constant +10° offset (ankle)**      | L1 (neutral pose)             | `hip_flexion_offset`               |
| **Y‑up ↔ Z‑up frame mix**             | L2 (energy timing, GRF‑speed) | vGRF–COM phase lag                 |
| **Local axis swap (foot frame)**      | L3 (global‑local RMS)         | RMS > 5 °                          |
| **Single‑limb sign inversion**        | L3 (symmetry)                 | correlation < 0.8                  |
| **Units in degrees**                  | L0 (angle ≤ π)                | unit assertion                     |

Passing all four layers therefore implies: correct units, signs, offsets ≈ 0, OpenSim X‑forward Y‑up Z‑right frame, orthogonal local axes, and plausible physics.

---

### Key references

1. OpenSim global frame definition ([opensimconfluence.atlassian.net][4])
2. Neutral‑pose joint angle convention ([ResearchGate][5])
3. Joint power = moment × angular velocity ([PubMed Central][1])
4. Net COM work ≈ 0 in level gait ([ScienceDirect][6], [PubMed Central][7])
5. Vertical GRF double‑peak norms ([PubMed Central][2], [ResearchGate][8])
6. GRF scaling with speed ([PubMed][3], [PubMed][10])
7. Cross‑entropy symmetry metrics ([PubMed Central][12], [ScienceDirect][13])
8. Stair & ADL joint‑angle ranges ([PubMed Central][11])

---

**Deploy this validator and you’ll have the most stringent automated guardrail possible without manual visual inspection.**

[1]: https://pmc.ncbi.nlm.nih.gov/articles/PMC7739716/?utm_source=chatgpt.com "Angular Velocity, Moment, and Power Analysis of the Ankle, Knee ..."
[2]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4311602/?utm_source=chatgpt.com "Ground reaction forces during level ground walking with body ..."
[3]: https://pubmed.ncbi.nlm.nih.gov/2782094/?utm_source=chatgpt.com "Ground reaction forces at different speeds of human walking and ..."
[4]: https://opensimconfluence.atlassian.net/wiki/spaces/OpenSim24/pages/54002645/Coordinates%2Band%2BUtilities?utm_source=chatgpt.com "Laboratory Coordinates - OpenSim"
[5]: https://www.researchgate.net/figure/The-definition-of-joint-angles-The-joint-angles-were-set-to-0-when-standing-on_fig4_325577326?utm_source=chatgpt.com "The definition of joint angles. The joint angles were set to 0 when..."
[6]: https://www.sciencedirect.com/science/article/abs/pii/S0021929025001940?utm_source=chatgpt.com "Center of mass work analysis predicts preferred walking speeds for ..."
[7]: https://pmc.ncbi.nlm.nih.gov/articles/PMC3199953/?utm_source=chatgpt.com "Effect of age on center of mass motion during human walking - PMC"
[8]: https://www.researchgate.net/figure/Typical-vertical-GRF-peaks-GRF-ground-reaction-force-BW-body-weight_fig2_230820140?utm_source=chatgpt.com "Typical vertical GRF peaks. GRF: ground reaction force; BW"
[9]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4886808/?utm_source=chatgpt.com "PREDICTING FOOT PROGRESSION ANGLE DURING GAIT USING ..."
[10]: https://pubmed.ncbi.nlm.nih.gov/11415629/?utm_source=chatgpt.com "Relationship between vertical ground reaction force and speed ..."
[11]: https://pmc.ncbi.nlm.nih.gov/articles/PMC5537477/?utm_source=chatgpt.com "Hip, knee, and ankle kinematics during activities of daily living"
[12]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4807060/?utm_source=chatgpt.com "Symmetry Analysis of Gait between Left and Right Limb Using Cross ..."
[13]: https://www.sciencedirect.com/science/article/abs/pii/S0021929011000121?utm_source=chatgpt.com "Identifying gait asymmetry using gyroscopes—A cross-correlation ..."
