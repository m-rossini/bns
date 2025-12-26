---
agent: agent
---
# Bean World – Formal Mathematical Specification

This document formalizes **all systems** in the Bean simulation using explicit equations, variables, and update order. It is written to be both *implementation-ready* and *conceptually simple*.

---

## 0. Global Principles (Read First)

1. **Strict separation of concerns**: simulation systems never know about rendering.
2. **No free lunch**: every trait has at least one downside.
3. **No perfect bean**: all optima are contextual.
4. **Systems are pluggable**: beans do not own logic; systems do.
5. **Per-tick determinism** (given seed): same inputs → same outputs.
6. **Local perception**: beans act on *perceived* state, not truth.

---

## 0.1 Simulation vs Rendering Boundary (Critical)

### Simulation Layer (Pure Logic)

Responsible for:

* World state
* Beans state
* All systems

### Rendering Layer (Visualization Only)

Responsible for:

* Drawing
* Animation
* Camera/UI

### Contract

```ts
interface RenderSnapshot {
  id: number
  position: Vector2
  direction: number
  size: number
  speed: number
  alive: boolean
}
```

---

## 1. Core State Definitions

### 1.1 Genotype (Immutable)

All genes are normalized in ([0,1]).

| Gene             | Symbol | Meaning                  |
| ---------------- | ------ | ------------------------ |
| Metabolism Speed | (g_m)  | Basal energy burn        |
| Max Speed        | (g_v)  | Genetic speed ceiling    |
| Fat Accumulation | (g_f)  | Fat storage efficiency   |
| Max Age          | (g_a)  | Longevity ceiling        |
| Awareness        | (g_w)  | Perception accuracy      |
| Sociability      | (g_s)  | Cooperation tendency     |
| Dominance        | (g_d)  | Aggression/assertiveness |
| Sex Drive        | (g_x)  | Mating motivation        |
| Loyalty          | (g_l)  | Partner exclusivity      |

---

### 1.2 Phenotype (Mutable)

| Variable        | Symbol    | Meaning           |
| --------------- | --------- | ----------------- |
| Age             | (t)       | Ticks since birth |
| Energy          | (E)       | Available energy  |
| Size (fat)      | (S)       | Body mass         |
| Target Size     | (S^*)     | Optimal size      |
| Speed           | (v)       | Current velocity  |
| Direction       | (\theta)  | Heading           |
| Social Score    | (R)       | Reputation        |
| Perceived State | (\hat{x}) | Blurred self-view |

---

## 2. Time & Update Order (Per Tick)

```text
update():
  1. age += 1
  2. environment.sample()
  3. perception.update()
  4. action = decision.select()
  5. movement.apply(action)
  6. energy_system.update()
  7. social_system.update()
  8. survival.check()
```

---

## 3. Size (Fat) System

### 3.1 Target Size Curve (Life Bell)

Let:

[
\tau = \frac{t}{t_{max}}, \quad t_{max} = g_a \cdot T_{max}
]

[
S^*(t) = S_{min} + (S_{max} \cdot g_f - S_{min}) \cdot e^{-k(\tau - 0.5)^2}
]

* Childhood → growth
* Adulthood → peak
* Aging → decline

---

### 3.2 Size Change Dynamics

Energy surplus:
[
\Delta S_+ = g_f \cdot \max(0, E - E_{need})
]

Energy deficit:
[
\Delta S_- = (1-g_f) \cdot \max(0, E_{need} - E)
]

Net:
[
S_{t+1} = S_t + \Delta S_+ - \Delta S_-
]

---

## 4. Energy System

### 4.1 Energy Balance Equation

[
E_{t+1} = E_t + I - B - M - A
]

Where:

* (I) = intake
* (B) = basal metabolism
* (M) = movement cost
* (A) = action cost

---

### 4.2 Basal Metabolism

[
B = B_0 \cdot (1 + g_m) \cdot (1 + S)
]

High metabolism + fat = expensive.

---

### 4.3 Movement Cost (with Inertia)

[
M = c_v |\Delta v| + c_t |\Delta \theta| + c_c |v|
]

* accelerating costs
* turning costs
* cruising costs

---

## 5. Speed System

### 5.1 Genetic Speed Ceiling

[
v_{max} = g_v \cdot V_{max}
]

---

### 5.2 Age Speed Factor

[
f_{age}(t) = \tau^p \cdot e^{-q\tau} \cdot (1-\tau^r)
]

---

### 5.3 Size Penalty (Z-score)

[
z = \frac{S - S^*}{0.15 S^*}
]

Penalty:

[
f_{size} =
\begin{cases}
1 & |z| \le 2 \
1 + 0.15 z & z < -2 \
1 - 0.20 z & z > 2
\end{cases}
]

---

### 5.4 Final Speed

[
v = v_{max} \cdot f_{age} \cdot f_{size}
]

---

## 6. Social System

### 6.1 Social Score Update

[
R_{t+1} = R_t + \sum \Delta R_{actions} - \lambda R_t
]

Decay:
[
\lambda = 0.001 + 0.01 g_w
]

---

### 6.2 Mate Attractiveness

[
A_{mate} = R + g_x - g_l + f(S)
]

---

### 6.3 Attack Deterrence

[
D = R + S + v - g_d
]

---

## 7. Action Decision System

Each action has utility:

[
U(a) = \sum_i w_i \cdot O_i(a) + \epsilon
]

Where:

* (O_i) = outcome signals
* (w_i) = trait-dependent weights
* (\epsilon) = noise (low awareness)

Chosen action:
[
a^* = \arg\max U(a)
]

---

## 8. Collision System

### 8.1 Wall Collision

[
E_{loss} = k_w \cdot |v|
]

---

### 8.2 Bean–Bean Collision

Total loss:
[
E_{tot} = k_c \cdot (v_1 + v_2)
]

Split:
[
E_i = E_{tot} \cdot \frac{1/S_i \cdot f_{sex}}{\sum}
]

Females lose more:
[
f_{sex} = \begin{cases}1.2 & female \ 1.0 & male\end{cases}
]

---

## 9. Survival System

### 9.1 Death Probabilities

Age:
[
P_{death}^{age} = \sigma(t - t_{max})
]

Starvation:
[
E < E_{crit} \land S < S_{crit}
]

Obesity:
[
S > S_{obese} \Rightarrow P \uparrow
]

Combat:
[
E < 0 \Rightarrow death
]

---

## 10. Trade-Off Summary (Key Rule)

| Trait       | Upside          | Downside     |
| ----------- | --------------- | ------------ |
| Speed       | Escape, food    | Energy burn  |
| Size        | Survival buffer | Speed loss   |
| Awareness   | Good decisions  | Brain cost   |
| Dominance   | Control         | Attacks      |
| Sociability | Safety          | Exploitation |
| Sex Drive   | Genes spread    | Energy loss  |

---

## 11. Data Collection (Per Tick)

Record:

```json
{
  tick,
  id,
  age,
  energy,
  size,
  speed,
  socialScore,
  action,
  alive
}
```

---

## 12. Final Mental Model (For a 5-Year-Old)

Beans are little creatures.
They eat, move, like each other, fight sometimes, and grow old.

If they are too fast → tired.
If too fat → slow.
If too mean → alone.
If too nice → bullied.

The world decides who survives.
Not one rule — **all rules together**.

---

---

## 13. Configuration System (Authoritative)

All simulation behavior is driven by **validated configuration objects**. No system owns constants.

---

### 13.1 WorldConfig

Controls global simulation context and randomness.

```ts
interface WorldConfig {
  seed: number                     // deterministic RNG seed
  width: number                    // world width (units)
  height: number                   // world height (units)
  roundsPerYear: number
  maxAgeYears: number

  maleFemaleRatio: number          // nominal ratio (e.g. 0.5)
  maleFemaleVariance: number       // relative variance (e.g. 0.1 = ±1%)

  temperatureBaseline: number      // default °C-equivalent
  temperatureVariance: number      // seasonal noise
}
```

---

### 13.2 BeanConfig

Defines biological bounds and base costs.

```ts
interface BeanConfig {
  initialEnergy: number

  sizeMin: number
  sizeMax: number
  obeseSize: number
  starvationSize: number

  baseMetabolism: number

  speedMax: number
  accelerationCost: number
  turnCost: number
  cruiseCost: number

  awarenessBrainCost: number
  sexEnergyCost: number
}
```

---

### 13.3 EnergySystemConfig

Controls energy flow equations.

```ts
interface EnergySystemConfig {
  intakePerFoodUnit: number
  fatBurnRate: number
  fatStoreEfficiency: number

  negativeEnergyPenalty: number
}
```

---

### 13.4 SocialSystemConfig

Controls reputation and interaction decay.

```ts
interface SocialSystemConfig {
  reputationDecayBase: number
  attackPenalty: number
  cooperationBonus: number
  matingBonus: number
}
```

---

### 13.5 ActionSystemConfig

Controls decision noise and inertia.

```ts
interface ActionSystemConfig {
  inertiaRetention: number       // [0,1]
  awarenessNoiseScale: number
  randomActionChance: number
}
```

---

### 13.6 SurvivalSystemConfig

Defines death thresholds.

```ts
interface SurvivalSystemConfig {
  criticalEnergy: number
  criticalSize: number

  obesityDeathSlope: number
  agingDeathSlope: number
}
```

---

### 13.7 Config Invariants

* All ratios ∈ [0,1]
* All costs ≥ 0
* sizeMin < sizeMax
* obeseSize > sizeMax * 0.9

---

### 13.8 Schema Philosophy

Schemas define **what may exist**.
Configs define **what is chosen**.
Systems define **what happens**.

Evolution is an emergent consequence — not a hardcoded rule.

---

**This spec is complete and internally consistent.**

---

## 13. Configuration System (Schema-Driven)

All systems are driven by **validated configuration objects**. No numeric constant used by a system may exist outside a config.

Configs are **data-only**, typically loaded from JSON and validated against schemas.

---

## 13.1 WorldConfig

Controls global simulation properties.

```ts
interface WorldConfig {
  seed: number
  width: number
  height: number
  ticksPerYear: number
  maxYears: number

  // Environment
  baseTemperature: number
  temperatureVariance: number

  // Population
  initialPopulation: number
  maleFemaleRatio: number        // mean (e.g. 0.5)
  maleFemaleVariance: number     // absolute deviation (e.g. 0.01)
}
```

---

## 13.2 BeanConfig

Defines biological constants shared by all beans.

```ts
interface BeanConfig {
  // Size
  minSize: number
  maxSize: number

  // Energy
  initialEnergy: number
  basalMetabolismBase: number
  energyCritical: number

  // Speed
  maxSpeed: number

  // Movement costs
  costPerSpeed: number
  costPerAcceleration: number
  costPerTurn: number

  // Collision
  wallCollisionLoss: number
  beanCollisionLoss: number
}
```

---

## 13.3 EnergySystemConfig

```ts
interface EnergySystemConfig {
  intakePerFoodUnit: number
  fatEnergyDensity: number
  starvationThreshold: number
  obesityThreshold: number
}
```

---

## 13.4 SocialSystemConfig

```ts
interface SocialSystemConfig {
  reputationDecayBase: number
  reputationDecayAwarenessFactor: number

  mateAttractionWeight: number
  attackDeterrenceWeight: number
}
```

---

## 13.5 ActionSystemConfig

```ts
interface ActionSystemConfig {
  utilityNoiseBase: number
  inertiaRetention: number

  // Energy costs
  seekFoodCost: number
  seekMateCost: number
  mateCost: number
  attackCost: number
}
```

---

## 13.6 SurvivalSystemConfig

```ts
interface SurvivalSystemConfig {
  ageDeathSlope: number
  starvationDeathEnergy: number
  starvationDeathSize: number
  obesityDeathProbability: number
}
```

---

## 13.7 Schema Invariants (Must Always Hold)

* All probabilities ∈ [0,1]
* All costs ≥ 0
* All max values > min values
* Ratios ∈ [0,1]

Violating a schema **fails fast** at load time.

---

## 14. System Responsibility Matrix

| System      | Reads            | Writes           |
| ----------- | ---------------- | ---------------- |
| Environment | world            | env state        |
| Action      | perceived state  | action intent    |
| Movement    | action, config   | speed, direction |
| Energy      | intake, movement | energy, size     |
| Social      | interactions     | reputation       |
| Survival    | full state       | alive/dead       |

---

## 15. Rendering Contract (Restated)

Rendering receives **snapshots only**. No system depends on rendering state.

```ts
interface RenderSnapshot {
  id: number
  position: Vector2
  direction: number
  size: number
  speed: number
  alive: boolean
}
```
