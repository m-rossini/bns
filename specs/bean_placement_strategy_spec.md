# Technical Specification: Controller-Driven Unicellular Bean Initial Placement & Gender System

This specification defines the complete architectural blueprint, area-based dynamic population calculus, gender balancing logic, visual rendering metadata assignment, and mathematical distribution formulas for initializing unicellular organisms ("beans") in the game world.

All placement strategies and gender balancing mechanisms conform to uniform conceptual interfaces driven by a central Spawn Controller.

---

## 1. System Architecture & Controller Flow

The system decouples Position Generation from Gender and Visual Attribute Assignment. A central Spawn Controller orchestrates the instantiation process by invoking the configured placement strategy and gender controller sequentially.

### 1.1 Orchestration Sequence

1. **Load Configuration:** The Spawn Controller parses the master configuration parameters to identify the active placement strategy name, population density tier, gender ratios, color visual attributes, and world parameters.
2. **Calculate Target Population ($N$):** The controller evaluates the total surface area $A$ of the world bounds, applies the chosen population density coefficient $\rho$, and factors in stochastic variance $v$ to determine the target bean count $N$.
3. **Generate Positions:** The controller passes target population $N$ and world boundaries to the active placement strategy to retrieve a list of positions in two-dimensional space.
4. **Initialize Gender Controller:** The controller initializes the Gender Controller using the configured gender ratio percentages (e.g., male and female allocations summing strictly to 100 percent) along with their corresponding color mappings.
5. **Assign Biological & Visual Attributes:** The Gender Controller processes the position list, assigning a specific gender identity and its associated color property to each generated position based on the exact quota requirements.
6. **Instantiate Entities:** The main controller iterates through the final spawn manifests, instantiating beans at the specified coordinates with their assigned gender traits and visual color profiles.

---

## 2. Dynamic Area-Based Population Calculus

Rather than utilizing a static headcount, population size adapts dynamically to the physical dimensions of the level, scaling predictably across arbitrary world bounds.

### 2.1 World Area Calculation ($A$)
Depending on the geometric shape of the environment bounds, world surface area is derived as:
* **Rectangular Arenas:** $A = \text{Width} \times \text{Height}$
* **Circular Arenas (Petri Dishes):** $A = \pi \times R_{\max}^2$

### 2.2 Population Density Coefficients ($\rho$)
The population density tier dictates the baseline ratio of beans per unit of world surface area:
* **Sparse Density:** $\rho = 0.0005$ (0.05% surface density ratio)
* **Average Density:** $\rho = 0.0020$ (0.20% surface density ratio)
* **Heavy Density:** $\rho = 0.0060$ (0.60% surface density ratio)
* **Super Density:** $\rho = 0.0150$ (1.50% surface density ratio)

### 2.3 Stochastic Population Variance Factor ($v$)
To ensure organic variety across level loads and avoid rigid repeatability, a random variance percentage $v$ within a defined range (e.g., $-0.10$ to $+0.10$ for a ten percent variance envelope) is calculated for each initialization session.

### 2.4 Master Population Formula ($N$)
$$N = \text{Round}\left( A \times \rho(\text{density}) \times (1 + \text{Uniform}(-v, +v)) \right)$$

---

## 3. Spatial Placement Strategies

Every placement strategy implements a uniform interface that receives the calculated target population $N$ alongside the world boundaries. All strategy parameters are registered within the system configuration, with a single selection setting determining the active algorithm.

### 3.1 Poisson-Disc Placement Strategy
* **Purpose:** Generates a semi-random, organic distribution with a strict minimum spacing radius scaled dynamically to prevent cell overlap across any map size.
* **Tunable Attributes:** Base Spacing Scale, Maximum Retry Limit.
* **Calculus & Logic:** Minimum spacing radius $r$ scales inversely with local population density across total world area $A$:
  $$r = \sqrt{\frac{A}{N}} \times \text{BaseSpacingScale}$$
  Candidate coordinates are sampled iteratively in an annulus ($r$ to $2r$) surrounding existing valid points, validating spatial distance constraints until $N$ coordinates are established.

### 3.2 Symmetrical Spawn Strategy
* **Purpose:** Ensures rotational or mirror symmetry across world axes, providing competitive equity or aesthetic balance in structured arenas.
* **Tunable Attributes:** Symmetry Axes Count ($k \ge 1$).
* **Calculus & Logic:** Target count per symmetrical segment is determined by $N_w = \lceil \frac{N}{k} \rceil$. Base coordinates are generated randomly within a primary slice $(\theta \in [0, \frac{2\pi}{k}])$:
  $$r = R_{\max} \times \sqrt{u}, \quad u \sim \text{Uniform}(0, 1)$$
  Coordinates are then replicated across $k$ rotational axes using transformation angle $\phi_i = i \times \frac{2\pi}{k}$ for $i = 0 \dots k-1$:
  $$x' = x \cos(\phi_i) - y \sin(\phi_i)$$
  $$y' = x \sin(\phi_i) + y \cos(\phi_i)$$

### 3.3 Colony Cluster Strategy
* **Purpose:** Seeds distinct bacterial colonies by grouping beans tightly around randomized biological mother centroids whose overall count scales with world area.
* **Tunable Attributes:** Area Per Cluster Metric, Cluster Spread Standard Deviation ($\sigma$).
* **Calculus & Logic:** Total cluster count $C$ scales with world size ($C = \max(1, \text{Round}(\frac{A}{\text{AreaPerCluster}}))$). Centroids are chosen randomly within bounds, and beans per cluster are distributed using two-dimensional Gaussian transformations (Box-Muller method):
  $$\Delta x = \sigma \sqrt{-2 \ln u_1} \cos(2\pi u_2)$$
  $$\Delta y = \sigma \sqrt{-2 \ln u_1} \sin(2\pi u_2)$$
  where $u_1, u_2 \sim \text{Uniform}(0, 1)$.

### 3.4 Center-to-Border Radial Placement Strategy (Core-Heavy)
* **Purpose:** Biases spawn probability toward the exact center of the map, creating a dense central nucleus that thins exponentially toward the perimeter.
* **Tunable Attributes:** Falloff Exponent Curve.
* **Calculus & Logic:** Radial distances $r$ from the origin are generated via a power-law probability curve:
  $$r = R_{\max} \times u^{\text{FalloffExponent}}, \quad u \sim \text{Uniform}(0, 1)$$
  Angles $\theta$ are sampled uniformly across $2\pi$ radians, creating Cartesian offsets from world center ($x = \text{Center.x} + r \cos(\theta)$, $y = \text{Center.y} + r \sin(\theta)$).

### 3.5 Border-to-Center Radial Placement Strategy (Periphery-Heavy)
* **Purpose:** Spawns cells in an outer ring or donut configuration along the perimeter, keeping the central area clear.
* **Tunable Attributes:** Outer Ring Thickness Ratio.
* **Calculus & Logic:** Radial boundaries are set using inner limit $R_{\min} = R_{\max} \times (1 - \text{RingThicknessRatio})$. Distances are distributed across the ring band:
  $$r = \sqrt{R_{\min}^2 + u \cdot (R_{\max}^2 - R_{\min}^2)}, \quad u \sim \text{Uniform}(0, 1)$$
  Paired with uniform angular distributions $\theta \sim \text{Uniform}(0, 2\pi)$.

### 3.6 Linear Gradient Placement Strategy
* **Purpose:** Applies a directional density bias, scaling cell concentration across world boundaries from one side of the map to the other.
* **Tunable Attributes:** Directional Vector Angle, Bias Curve Strength.
* **Calculus & Logic:** Candidate points projected onto the directional vector yield normalized distance $t \in [0, 1]$. An acceptance-rejection sampling method evaluates candidate validity using linear weight function $P(t) = 1 + \text{BiasStrength} \times (t - 0.5)$.

### 3.7 Resource Gradient Strategy
* **Purpose:** Uses a two-dimensional noise map scaled to world dimensions as a nutrient heatmap, clustering initial beans around environmental hotspots.
* **Tunable Attributes:** Noise Frequency Scale, Baseline Threshold.
* **Calculus & Logic:** Noise values $v \in [0, 1]$ are sampled relative to map size. A dynamic spawn threshold $T$ adjusts based on the selected density tier (e.g., Sparse $T = 0.75$, Average $T = 0.50$, Heavy $T = 0.25$, Super $T = 0.05$). Candidates are accepted where $v \ge T$ until population target $N$ is satisfied.

---

## 4. Gender Balancing & Visual Rendering Metadata

Once raw spatial positions are generated, the Gender Controller processes the coordinate collection to assign biological and visual properties.

### 4.1 Ratio Allocation Rule & Validation
* Gender distributions are defined as percentage allocations across biological types (e.g., Male percentage and Female percentage).
* The system enforces a strict validation rule requiring all configured gender percentages to sum exactly to 100%.

### 4.2 Visual Color Assignment
* Each gender definition incorporates a specific color attribute mapping.
* When the Gender Controller assigns a gender trait to a bean coordinate, it attaches the corresponding visual color metadata, ensuring that the visual representation accurately reflects the biological trait upon instantiation.

### 4.3 Balancing Execution Logic
1. **Quota Calculation:** Given total coordinate count $N$, exact counts for each gender are calculated using the ratio percentages.
2. **Sequential Pool Generation:** A structured list containing the exact required quantities of gender identity and color metadata pairs is generated.
3. **Stochastic Shuffle & Mapping:** The metadata list is randomly shuffled and mapped 1-to-1 onto the coordinate list, producing balanced distributions across spatial locations without clustering identical biological types sequentially.