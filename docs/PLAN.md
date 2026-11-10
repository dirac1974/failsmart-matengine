# FailSmart-MatEngine: Expert Scientific Team & Implementation Plan

> [!IMPORTANT]
> **Mission Objective:** Discover, stress-test, and validate earth-abundant, phase-stable, defect-tolerant **inorganic chalcohalide and oxychalcogenide semiconductors** ($\text{Bi/Sb–Cu/Zn/Sn–S/Se/O–Cl/Br/I}$) for a **mechanically decoupled (4-Terminal) 3-Layer "Silicon-Sandwich" Photovoltaic Stack**:
> 1. **Top "Active Glass" Layer ($E_g \in [1.75, 1.95]\text{ eV}$):** Coated directly on soda-lime cover glass ($T_{\text{synth}} \le 500^\circ\text{C}$), harvesting UV/blue/green photons while transmitting $>85\%$ of red/IR light ($>670\text{ nm}$).
> 2. **Middle Anchor ($E_g = 1.12\text{ eV}$):** Off-the-shelf commercial bifacial crystalline silicon wafer.
> 3. **Bottom IR Scavenger ($E_g \in [0.70, 0.85]\text{ eV}$):** Decoupled narrow-gap thin film beneath silicon with a textured rear mirror for $4n^2$ Yablonovitch Total Internal Reflection, harvesting $1100\text{–}1750\text{ nm}$ sub-bandgap infrared photons.

---

## 1. Scientific Blind Spots Resolved Beyond the Initial Concept

Before locking in the agent roster, four deep physical failure modes specific to heavy lone-pair ($ns^2$) chalcohalides and 4T tandem stacks must be built directly into the team's mandate:

1. **Relativistic Spin-Orbit Coupling (SOC) is Non-Negotiable:** Heavy pnictogen/post-transition cations ($\text{Bi}^{3+}, \text{Sb}^{3+}, \text{Sn}^{2+}$) and heavy halides/chalcogenides ($\text{I}^-, \text{Br}^-, \text{Se}^{2-}$) exhibit giant spin-orbit splitting ($0.3\text{–}0.8\text{ eV}$) at the conduction/valence band edges. Standard HSE06 without SOC overestimates band gaps by up to $0.5\text{ eV}$ and misidentifies direct vs. indirect transitions.
2. **The "Bi-Halide Polaron Trap" (Electronic Dimensionality & Carrier Transport):** Many $\text{Bi/Sb}$ halides pass band-gap and defect-tolerance checks yet fail in solar cells (<2% efficiency) because 0D/1D crystal connectivity yields flat bands ($m^* > 1.5\,m_0$) and **self-trapped small polarons**—carriers freeze in local lattice distortions before traversing a $300\text{ nm}$ film. We must enforce 3D/quasi-2D electronic dimensionality, low effective masses ($m_e^*, m_h^* < 0.5\,m_0$), high static dielectric screening ($\varepsilon_0 > 15$), and Fröhlich large-polaron criteria.
3. **Volatile Halide Precursor Loss Under $500^\circ\text{C}$:** Binary metal halides ($\text{BiCl}_3, \text{SbI}_3, \text{SnI}_4$) sublimate or hydrolyze between $150^\circ\text{C}$ and $350^\circ\text{C}$. Retrosynthesis cannot merely check solid-state $\Delta G_{\text{rxn}}$; it must track vapor-phase chemical potentials and favor nonvolatile oxyhalide/sulfide intermediate pathways or solution-complexed routes.
4. **Full-Stack Optical & Parasitic Coupling:** A top absorber with high single-layer SLME is useless if high refractive-index mismatch ($R(\lambda)$) or sub-bandgap tail absorption starves the underlying $1.12\text{ eV}$ silicon wafer. Every candidate must be evaluated inside an optical Transfer-Matrix Method (`TMM`) + $4n^2$ light-trapping stack across all three junctions.

---

## 2. The Expert Scientific Team Roster (7 Agents)

Rather than generic LLM personas, each agent is a **domain-specialized state-machine node** bound to deterministic computational physics tools, hard falsification metrics, and explicit input/output schemas.

```mermaid
flowchart TD
    User["User / Research Director"] --> PI["Agent 0: Principal Investigator & Orchestrator (pi_orchestrator)"]
    
    subgraph Stage1["Stage 1: Compositional & Crystal Generation"]
        PI --> A1["Agent 1: Solid-State Chemist & Inverse-Design Explorer (crystal_explorer)"]
    end
    
    subgraph Stage2["Stage 2: Thermodynamics, Mechanics & Lattice Dynamics"]
        A1 --> A2["Agent 2: Lattice Dynamics & MLIP Surrogate Physicist (surrogate_physicist)"]
    end
    
    subgraph Stage3["Stage 3: Kinetics, Speciation & Manufacturability"]
        A2 --> A3["Agent 3: Retrosynthesis, Kinetics & Leaching Chemist (synthesis_chemist)"]
    end

    subgraph GateA["Adversarial Gate A (Pre-DFT Red Team)"]
        A3 --> A6["Agent 6: Adversarial Red-Team Critic (adversarial_critic)"]
    end

    subgraph Stage4_5["Stages 4 & 5: Quantum Electronics, Defects & Tandem Optics"]
        A6 -->|Promoted Top 1.5%| A4["Agent 4: Quantum Electronic & Defect-Transport Physicist (quantum_defect_physicist)"]
        A4 --> A5["Agent 5: Nanophotonics & 4T Tandem Device Architect (photonic_tandem_architect)"]
    end

    A5 --> A6_Final["Agent 6: Final Red-Team Audit"]
    A6_Final -->|Validated Candidates| PI

    A2 -.->|Hull / Phonon Failures| FML[("Contrastive Failure Memory Ledger (PostgreSQL + pgvector)")]
    A3 -.->|Oxide Sink / Leaching Failures| FML
    A4 -.->|Polaron / Deep Defect Failures| FML
    A5 -.->|Parasitic Optical Failures| FML
    A6 -.->|Adversarial Vetoes| FML
    FML -.->|Contrastive Retraining & Constraints| A1
    FML -.->|Negative-Result Priors| A3
```

### Agent 0: Principal Investigator & Campaign Orchestrator (`pi_orchestrator`)
* **Scientific Persona:** Senior Computational Materials Director & Systems Architect.
* **Core Mandate:** Manages campaign state in `LangGraph`, enforces the compute budget cap (\$$1,000$/sweep), balances exploration between the **Top Active Glass ($1.85\text{ eV}$)** and **Bottom IR Scavenger ($0.75\text{ eV}$)** tracks, and maintains the Pareto frontier across efficiency, synthesizability, and $/W cost.
* **Deterministic Tools:** Campaign state ledger, multi-objective Pareto optimizer (`botorch` / `pymoo`), epistemic uncertainty router (triggers DFT when 4-model MLIP force std $\sigma_F > 0.15\text{ eV/\AA}$ on otherwise top-ranked motifs).

### Agent 1: Solid-State Chemist & Inverse-Design Explorer (`crystal_explorer`)
* **Scientific Persona:** Inorganic Crystallographer & Generative ML Specialist.
* **Core Mandate:** Translates the 3-Tier Element Policy and target electronic rules ($ns^2$ lone-pair cations $\text{Bi}^{3+}, \text{Sb}^{3+}, \text{Sn}^{2+}$ paired with $\text{Cu}^+, \text{Zn}^{2+}, \text{Ba}^{2+}, \text{Sr}^{2+}$ and mixed anions $\text{S}^{2-}, \text{Se}^{2-}, \text{O}^{2-}, \text{Cl}^-, \text{Br}^-, \text{I}^-$) into charge-neutral, Pauling-rule-compliant compositions and 3D unit cells ($\le 32$ atoms/cell).
* **Deterministic Tools:**
  * `SMACT` (Semiconducting Materials by Analogy and Chemical Theory) for oxidation-state neutrality, Pauling electronegativity, and Goldschmidt/octahedral tolerance pre-screening.
  * `MatterGen` (SE(3)-equivariant diffusion with property adapters) + wyckoff-symmetry template substitution (`pyxtal`).
  * `pymatgen` local coordination & bond-valence sum (`BVAnalyzer`) sanity filters (rejects unphysical interatomic distances $< 1.6\text{ \AA}$ before wasting GPU cycles).

### Agent 2: Lattice Dynamics & MLIP Surrogate Physicist (`surrogate_physicist`)
* **Scientific Persona:** Statistical & Condensed Matter Physicist (Thermodynamics & Phonons).
* **Core Mandate:** Evaluates $0\text{ K}$ and finite-temperature ($300\text{–}800\text{ K}$) structural, mechanical, and dynamical stability using an ensemble of universal machine-learning interatomic potentials.
* **Deterministic Tools:**
  * **4-Member MLIP Ensemble (`MACE-OMat24` + `CHGNet`):** Full cell + atomic position relaxation (`FIRE` / `BFGS` via `ASE`) plus force-variance epistemic uncertainty ($\sigma_F$).
  * **Thermodynamic Hull Engine (`pymatgen.analysis.phase_diagram`):** Queries synchronized Materials Project + Alexandria convex hulls (with `MaterialsProject2020Compatibility` corrections). **Hard Gate:** $\Delta E_{\text{hull}} \le 50\text{ meV/atom}$ (or stabilized at $T_{\text{synth}}$ via vibrational/configurational entropy $\Delta G_{\text{hull}}(T) \le 0$).
  * **Dynamic & Mechanical Stability (`phonopy` + `matcalc`):** Finite-displacement supercell phonon spectra and elastic stiffness tensor $C_{ij}$. **Hard Gates:** Rejects imaginary phonon modes ($\omega < -0.5\text{ THz}$ anywhere in the Brillouin zone), checks Born elastic stability ($C_{ij}$ eigenvalues $> 0$), and computes Debye temperature $\Theta_D$ and lattice thermal conductivity proxy.

### Agent 3: Retrosynthesis, Kinetics & Environmental Speciation Chemist (`synthesis_chemist`)
* **Scientific Persona:** Experimental Solid-State Chemist & Geochemical Speciation Expert.
* **Core Mandate:** Guarantees that surviving crystals can actually be synthesized below the **$500^\circ\text{C}$ soda-lime glass ceiling** without collapsing into dead binary/oxide impurity sinks, losing volatile halides, or leaching toxic ions in rainwater.
* **Deterministic Tools:**
  * **Reaction Network & Impurity Sink Simulator (`rxn_network` + LBNL 80k Impurity Dataset):** Constructs grand-potential reaction graphs from commercial precursors ($\text{Bi}_2\text{O}_3, \text{Bi}_2\text{S}_3, \text{BiCl}_3, \text{Cu}_2\text{S}, \text{ZnS}$, etc.) at $T \in [300, 773]\text{ K}$. Computes reaction driving force $\Delta G_{\text{rxn}}$ vs. parasitic competing sinks (e.g., $\text{ZrO}_2, \text{TiO}_2, \text{BiOCl}$).
  * **Contrastive Synthesizability Scorer (`PU-CGCNN` + Impurity Margin Classifier):** Scores crystal synthesizability trained on ICSD positives vs. documented LBNL impurity-phase failures.
  * **Aqueous Leaching & Environmental Gate (`pymatgen` `PourbaixDiagram`):** Evaluates aqueous stability across $\text{pH } 4\text{–}9$ (acid rain to groundwater) and redox potentials $E_h \in [-0.2, +0.8]\text{ V}$. **Hard Gate:** Any Tier 2 element ($\text{Pb, Cd, Se, Sb, In, Ag, Te}$) must remain locked in solid phases ($\Delta G_{\text{pbx}} \le 0.1\text{ eV/atom}$, dissolved concentration $< 10^{-6}\text{ M}$) and cost $< \$0.50/\text{m}^2$ at target optical thickness.

### Agent 4: Quantum Electronic Structure & Defect-Transport Physicist (`quantum_defect_physicist`)
* **Scientific Persona:** Ab Initio Electronic Structure & Semiconductor Defect Theorist.
* **Core Mandate:** Executes high-fidelity open-source DFT (`Quantum ESPRESSO`) on the top $1.5\%$ of Stage 3 survivors to verify true relativistic band gaps, carrier transport, polaron localization, and intrinsic defect tolerance.
* **Deterministic Tools:**
  * **Automated DFT Engine (`atomate2` + `custodian` + `Quantum ESPRESSO` GPU):**
    * *Step 4a (Fast Meta-GGA Screen):* `r2SCAN + SOC` electronic band structure and density of states (DOS) to check orbital hybridization ($ns^2$ cation $s$–anion $p$ antibonding valence band maximum, which is the signature of defect tolerance).
    * *Step 4b (Gold-Standard Hybrid):* `HSE06 + SOC` band structure + optical transition dipole matrix elements $|\langle c,\mathbf{k} | \mathbf{p} | v,\mathbf{k} \rangle|^2$.
  * **Carrier Transport & Polaron Gate (`boltztrap2` / `amset`):** Computes conductivity effective mass tensors $m_e^*, m_h^*$, static and high-frequency dielectric constants ($\varepsilon_0, \varepsilon_\infty$), and Fröhlich coupling constant $\alpha_{\text{F}}$. **Hard Gate:** Rejects 0D localized states where $\max(m_e^*, m_h^*) > 0.8\,m_0$ or small-polaron trapping energy exceeds thermal energy.
  * **Stage 5 Killer Defect Audit (`doped`):** Generates charge-state supercells ($q \in [-3, +3]$) for dominant intrinsic vacancies and antisites ($V_{\text{Anion}}, V_{\text{Cation}}, \text{Cation}_{\text{Anion}}$) with Freysoldt (FNV) finite-size charge corrections. **Hard Gate:** Rejects candidates with low-formation-energy deep mid-gap Shockley-Read-Hall (SRH) traps or Fermi-level pinning that prevents carrier extraction.

### Agent 5: Nanophotonics & 4T Tandem Device Architect (`photonic_tandem_architect`)
* **Scientific Persona:** Optoelectronic Device Physicist & Nanophotonic Engineer.
* **Core Mandate:** Translates DFT optical tensors into realistic 3-layer "Silicon-Sandwich" device efficiency under the AM1.5G solar spectrum, accounting for TCO free-carrier losses, dichroic reflectors, and $4n^2$ Yablonovitch light trapping.
* **Deterministic Tools:**
  * **SLME & Complex Refractive Index Calculator:** Converts DFT dielectric function $\varepsilon_1(\omega) + i\varepsilon_2(\omega)$ into absorption coefficient $\alpha(\omega)$ and complex refractive index $\tilde{n}(\omega) = n(\omega) + i\kappa(\omega)$.
  * **Multilayer Optical & Detailed-Balance Simulator (`tmm` + `pvlib` / custom 4T solver):**
    * Simulates the full optical stack: `Soda-Lime Glass -> Front TCO -> Top Active Glass Absorber (1.75–1.95 eV, d <= 300 nm) -> Rear TCO / Dichroic Mirror -> Optical Coupling Layer -> Bifacial c-Si (1.12 eV, 160 um) -> Dichroic IR Splitter -> Bottom IR Scavenger (0.70–0.85 eV, d <= 400 nm) -> Textured Rear Ag/Dielectric Mirror (4n^2 TIR)`.
    * **Hard Gates:**
      1. Standalone single-junction $\text{SLME} \ge 22\%$ (Top cell) or $\ge 18\%$ (Bottom cell under filtered AM1.5G).
      2. Sub-bandgap optical transmittance of Top Active Glass $T(\lambda \in [680, 1100]\text{ nm}) \ge 85\%$.
      3. Combined 4-Terminal 3-layer stack efficiency $\eta_{\text{4T}} \ge \mathbf{42.0\%}$ (representing a $>15\%$ absolute gain over standalone silicon).

### Agent 6: Adversarial Red-Team Critic & Failure-Memory Curator (`adversarial_critic`)
* **Scientific Persona:** Skeptical Principal Experimentalist & Data Integrity Auditor (with Veto Power).
* **Core Mandate:** Actively attempts to falsify every candidate before expensive cloud GPU DFT runs (Gate A: Stage 3 $\rightarrow$ 4) and before final reporting (Gate B: Stage 5 $\rightarrow$ Patent Dossier). Curates the **Contrastive Failure Memory Ledger**.
* **Adversarial Checklist (Automatic Veto Triggers):**
  1. **Pseudopotential / Functional Artifact Check:** Flags inconsistent Hubbard $U$ or relativistic pseudopotential mismatches across phase-diagram references.
  2. **Hidden Phase-Segregation Check:** For mixed-anion candidates (e.g., $\text{S/Cl}$ or $\text{Se/I}$), computes configurational mixing enthalpy $\Delta H_{\text{mix}}$ across anion orderings to verify the crystal won't photo-segregate like mixed $\text{I/Br}$ perovskites!
  3. **TCO & Interfacial Reactivity Check:** Checks whether the candidate reacts thermodynamically with standard transparent conductive oxides ($\text{ITO}, \text{FTO}, \text{AZO}$) at deposition temperatures ($\Delta G_{\text{interface}} < -100\text{ meV/atom}$).
  4. **Failure Ledger Write-Back:** Logs every rejected structure, the exact physical mechanism of failure, and a structural graph embedding (`MACE` latent vector) into the Failure Memory Ledger.

---

## 3. Operational Workflow & Adversarial Debate Protocol

Every screening sweep follows a deterministic **5-Stage Funnel + 2 Adversarial Red-Team Gates**:

| Stage | Lead Agent | Input $\rightarrow$ Output Count | Physics / Chemistry Gate | Target Compute |
| :--- | :--- | :--- | :--- | :--- |
| **Stage 1: Generation** | `crystal_explorer` | $50,000\text{ stoichiometries} \rightarrow 10,000\text{ crystals}$ | SMACT charge/electronegativity + 3-Tier Element Policy + `MatterGen` ($\le 32\text{ atoms}$) + Bond-Valence sanity | Local GPU / CPU |
| **Stage 2: Surrogate Physics** | `surrogate_physicist` | $10,000 \rightarrow 1,200\text{ dynamically stable}$ | 4x `MACE-OMat24` relaxation + $\Delta E_{\text{hull}} \le 50\text{ meV/atom}$ + Born $C_{ij} \succ 0$ + `phonopy` $\omega^2 > 0$ | Local GPU |
| **Stage 3: Kinetics & Speciation** | `synthesis_chemist` | $1,200 \rightarrow 150\text{ manufacturable}$ | `rxn_network` ($T \le 500^\circ\text{C}$, no oxide sinks) + Halide volatility + Pourbaix ($\text{pH } 4\text{–}9$) + Cost $< \$0.50/\text{m}^2$ | Multi-core CPU |
| **Gate A: Pre-DFT Red Team** | `adversarial_critic` | $150 \rightarrow 20\text{ promoted to DFT}$ | Anion unmixing check ($\Delta H_{\text{mix}}$) + TCO interface stability + Epistemic uncertainty audit | CPU |
| **Stage 4: Quantum & Transport** | `quantum_defect_physicist` | $20 \rightarrow 6\text{ high-mobility absorbers}$ | `QE` `r2SCAN+SOC` $\rightarrow$ `HSE06+SOC` + $m_e^*, m_h^* < 0.8\,m_0$ + Fröhlich polaron check | Cloud GPU Burst |
| **Stage 5: Defects & 4T Optics** | `quantum_defect_physicist` + `photonic_tandem_architect` | $6 \rightarrow 2\text{–}4\text{ patent-ready finalists}$ | `doped` vacancy/antisite supercells (no deep SRH traps) + Full 3-layer `TMM` $4n^2$ stack $\eta_{\text{4T}} \ge 42\%$ | Cloud GPU Burst |

### How the Adversarial Debate Protocol Works in Practice
At **Gate A** (before spending cloud GPU budget on Stage 4 DFT) and **Gate B** (final sign-off), the state machine runs a structured 3-turn debate:
1. **Proposer Brief (`synthesis_chemist` + `surrogate_physicist`):** Submits a `CandidateDossier` JSON containing crystal CIF, $\Delta E_{\text{hull}}$, phonon min frequency, lowest-barrier $T \le 500^\circ\text{C}$ precursor reaction, and Pourbaix pass certificate.
2. **Red-Team Attack (`adversarial_critic`):** Executes automated falsification scripts (anion-ordering supercell sweep to test phase segregation, interfacial reaction hull against $\text{SnO}_2/\text{In}_2\text{O}_3/\text{ZnO}$ TCOs, and coordination-dimensionality graph analysis to detect 0D isolated octahedra).
3. **PI Adjudication (`pi_orchestrator`):** Promotes the candidate to Stage 4 *only* if all hard physical thresholds pass or if epistemic force uncertainty ($\sigma_F > 0.15\text{ eV/\AA}$) justifies an active-learning single-point DFT query.

---

## 4. Contrastive Failure Memory Ledger Schema

To ensure negative results become a compounding scientific asset, every failed candidate at Stages 2–5 is recorded in a structured relational + vector store (`SQLite`/`PostgreSQL` + `FAISS`/`pgvector` for local execution):

```sql
CREATE TABLE material_evaluations (
    candidate_id TEXT PRIMARY KEY,
    formula_reduced TEXT NOT NULL,
    target_layer TEXT CHECK (target_layer IN ('TOP_ACTIVE_GLASS_185EV', 'BOTTOM_IR_075EV')),
    space_group_number INTEGER,
    cif_structure TEXT NOT NULL,
    mace_embedding BLOB,                  -- 128-dim equivariant graph descriptor
    stage_reached INTEGER NOT NULL,       -- 1 to 5
    status TEXT CHECK (status IN ('PROMOTED', 'REJECTED', 'UNCERTAIN_DFT_QUEUE')),
    primary_failure_mode TEXT,            -- e.g., 'IMAGINARY_PHONON', 'OXIDE_IMPURITY_SINK', 'AQUEOUS_LEACHING', 'SMALL_POLARON_TRAP', 'ANION_PHASE_SEGREGATION', 'DEEP_SRH_DEFECT'
    e_above_hull_mev REAL,
    min_phonon_freq_thz REAL,
    rxn_temp_celsius REAL,
    competing_impurity_phases TEXT,       -- JSON array from rxn_network / LBNL dataset
    pourbaix_max_dissolution_mol_l REAL,
    hse06_soc_gap_ev REAL,
    direct_gap_ev REAL,
    max_carrier_eff_mass REAL,
    slme_percent REAL,
    tandem_4t_efficiency_percent REAL,
    adversarial_notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

This ledger directly powers **Contrastive Failure Learning**: after every campaign sweep, `crystal_explorer` and `synthesis_chemist` update a lightweight contrastive classifier on `mace_embedding` vectors to steer generation away from crystal motifs prone to imaginary phonons, $\text{BiOCl}/\text{ZrO}_2$ impurity traps, or 0D polaron localization.

---

## 5. Phased Implementation Roadmap

We can build and execute this architecture in modular phases right inside this workspace:

### Phase 1: Core Repository, Failure Ledger & Deterministic Physics Tools (Local Execution)
1. **Scaffold the `failsmart-matengine` Python package** with strict Pydantic schemas (`CandidateMaterial`, `StabilityReport`, `SynthesisRouteReport`, `OpticalTandemReport`, `FailureRecord`).
2. **Build the Contrastive Failure Memory Ledger** (local SQLite + vector similarity index) pre-seeded with known chalcohalide/perovskite failure archetypes (e.g., $\text{BaZrS}_3$ high-$T$ $\text{ZrO}_2$ sink, mixed $\text{MAPb(I,Br)}_3$ photo-segregation, $\text{Cs}_3\text{Bi}_2\text{I}_9$ 0D polaron trap).
3. **Implement the Stage 1–3 & Gate A Tool Suite:**
   * `tools/composition_gen.py`: 3-Tier Element Policy + `SMACT` charge-neutral quaternary/ternary chalcohalide & oxychalcogenide generator + prototype crystal decorator (`pymatgen` / `pyxtal`).
   * `tools/surrogate_physics.py`: `MACE` / `CHGNet` structural relaxation, convex hull stability against Materials Project, and finite-displacement phonon/elasticity checks.
   * `tools/synthesis_kinetics.py`: $<500^\circ\text{C}$ precursor reaction driving-force calculator, halide volatility filter, TCO interface reactivity check, and `pymatgen` Pourbaix aqueous leaching gate ($\text{pH } 4\text{–}9$).
   * `tools/tandem_optics.py`: Transfer-Matrix + $4n^2$ Yablonovitch 3-layer "Silicon-Sandwich" (Top Active Glass + $1.12\text{ eV}$ c-Si + Bottom IR Scavenger) detailed-balance efficiency calculator.

### Phase 2: Multi-Agent State Machine & Subagent Team Wiring
1. **Define and wire the 7 specialized agents** (`pi_orchestrator`, `crystal_explorer`, `surrogate_physicist`, `synthesis_chemist`, `quantum_defect_physicist`, `photonic_tandem_architect`, and `adversarial_critic`) with the adversarial debate protocol at Gate A and Gate B.
2. **Configure Stage 4/5 Quantum ESPRESSO & `doped` workflow generators** (`tools/qe_workflows.py`) so promoted candidates automatically emit turnkey, `custodian`-wrapped `Quantum ESPRESSO` (`r2SCAN+SOC` / `HSE06+SOC`) and `doped` defect supercell input decks.

### Phase 3: Pilot Dry-Run Screening Campaign & Interactive Dashboard
1. **Execute Pilot Sweep #1** across both target windows:
   * **Track A (Top Active Glass, $1.75\text{–}1.95\text{ eV}$):** $\text{Bi/Sb–Cu/Zn–S/O–Cl/Br}$ oxy-/chalcohalides.
   * **Track B (Bottom IR Scavenger, $0.70\text{–}0.85\text{ eV}$):** $\text{Bi/Sb–Sn/Cu–Se/S–I}$ heavy chalcohalides.
2. **Launch an Interactive Discovery & Failure-Ledger Dashboard** (HTML artifact) visualizing the screening funnel, Pareto frontier ($\eta_{\text{4T}}$ vs. synthesis temperature vs. $/m^2$ cost), 3-layer spectral absorption curves, and the live Contrastive Failure Memory Ledger.
