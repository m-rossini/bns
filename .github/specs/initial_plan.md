# Bean World: 250-Step Master Implementation Plan
**Version:** 6.0 (Zero-Gap Implementation)
**Architecture:** Configuration-First / Reactive Sim / Headless Core

---

## Module 1: The Configuration Engine (Steps 1–25)
1. **Step 1:** Initialize Vite/TypeScript project with strict mode enabled.
2. **Step 2:** Create directory structure: `/src/config`, `/src/sim/components`, `/src/sim/systems`, `/src/sim/utils`.
3. **Step 3:** Define `SimulationSchema.ts` (TypeScript interfaces for all world and bean parameters).
4. **Step 4:** Define `BiologicalTradeoffSchema.ts` (Specific ranges and mathematical coefficients for $g_m, g_v, g_w$).
5. **Step 5:** Create `src/config/store/ConfigStore.ts` (The single source of truth for the simulation state).
6. **Step 6:** Implement `ConfigValidator`: Logic to ensure values (like speed or energy) are within physical limits.
7. **Step 7:** Create `DefaultWorldConfig.json` (World Seed, Ticks per Year, Map Boundaries).
8. **Step 8:** Create `DefaultPlacementConfig.json` (Default Strategy, Density settings, Variance types).
9. **Step 9:** Create `DefaultBiologicalConfig.json` (Basal metabolic rates, intake values, sex ratio targets).
10. **Step 10:** Implement `ConfigLoader`: A service to merge local JSON files with runtime overrides.
11. **Step 11:** Implement `ConfigSubscriber`: Pub/Sub pattern to allow Sim Systems to react to "live" knob changes.
12. **Step 12:** Implement **Immutable Snapshots**: Logic to deep-freeze the config state at any tick.
13. **Step 13:** Add `SeededRandomConfig` handling: Support for ZERO, SEEDED, and FULL random variance modes.
14. **Step 14:** Define `EnergyConstants`: $B_0$ (Basal), Brain Tax coefficients, and Movement cost multipliers.
15. **Step 15:** Define `SizeConstants`: Maximum fat storage limits and growth/mass efficiency ratios.
16. **Step 16:** **Verification:** Unit test the ConfigLoader to ensure invalid JSON structures throw caught errors.
17. **Step 17:** Implement `ConfigExporter`: Logic to export current "Knob positions" to a downloadable JSON file.
18. **Step 18:** Create `src/core/Main.ts`: Initialize the Phaser 3 Canvas and Game instance.
19. **Step 19:** Create `src/sim/SimulationCore.ts`: The "Headless" heart that contains the logic loop.
20. **Step 20:** Implement the `step()` heartbeat within `SimulationCore`.
21. **Step 21:** Implement `isPaused` and `timeScale` controls within the Core.
22. **Step 22:** Wire the Phaser `update()` loop to call the `SimulationCore.step()` method.
23. **Step 24:** Setup `SeededRandom.ts`: A deterministic PRNG using the world seed.
24. **Step 24:** Create `src/sim/utils/VectorMath.ts`: Implement Distance, Normalization, and Dot Product helpers.
25. **Step 25:** **Milestone:** The simulation has a "Heartbeat" and a validated "Legal Code" (Config).

---

## Module 2: The Placement Engine (Steps 26–50)
26. **Step 26:** Create `src/sim/components/PlacementComponent.ts`.
27. **Step 27:** Define `Density` Enum: `LOW`, `MEDIUM`, `HIGH`, `EXTREME`.
28. **Step 28:** Define `PlacementStrategy` Enum: `GRID`, `CLUSTER`, `RANDOM`, `DIAGONAL`, `ORTHOGONAL`.
29. **Step 29:** Implement `calculatePopulationCount()`: Logic to map Density Enum to raw counts based on world area.
30. **Step 30:** Create `IPlacementStrategy.ts`: Interface for all spatial point generation patterns.
31. **Step 31:** Implement `GridStrategy.ts`: Generate points in a perfect mathematical lattice.
32. **Step 32:** Implement `ClusterStrategy.ts`: Generate points around multi-point Gaussian "hubs".
33. **Step 33:** Implement `RandomStrategy.ts`: Generate points using seeded uniform distribution.
34. **Step 34:** Implement `DiagonalStrategy.ts`: Generate points on intersecting paths for collision stress testing.
35. **Step 35:** Implement `OrthogonalStrategy.ts`: Generate points in axis-aligned cross patterns.
36. **Step 36:** **Integration:** Implement `PlacementVariance` ($V_p$): Apply jitter to deterministic patterns.
37. **Step 37:** Implement `VarianceType` handling: Switch between Zero Jitter and Seeded Jitter.
38. **Step 38:** Implement `SpawnSafetyChecker`: Logic to ensure no points overlap world borders or static obstacles.
39. **Step 39:** Implement `PlacementManifest`: A generated list of X/Y coordinates ready for the Bean Factory.
40. **Step 40:** **Verification:** Set Strategy to `GRID` and Variance to `ZERO`; verify perfect lattice in logs.
41. **Step 41:** Add `Padding` constants to prevent spawning in the "death zone" near edges.
42. **Step 42:** Implement `ZonalDensity`: Allow specific regions of the map to have higher concentrations.
43. **Step 43:** Create `PlacementExporter`: Save the current layout to JSON for replay fidelity.
44. **Step 44:** Implement `SpawnBatching`: Logic to spread large spawns over multiple ticks to prevent frame-drops.
45. **Step 45:** Add `TopologyValidation`: Check if World Size can actually accommodate the requested Density.
46. **Step 46:** Implement `SpawnAnimationData` hooks: Prepare metadata for Phaser birth effects.
47. **Step 47:** Create `PlacementUI` debug layer: Draw temporary dots where beans will appear.
48. **Step 48:** Implement `CollisionBuffer` logic specifically for the initial spawn points.
49. **Step 49:** Finalize the `PlacementComponent` API for the `SimulationCore`.
50. **Step 50:** **Milestone:** Starting population topologies are deterministic and strategy-based.

---

## Module 3: Genotype & Bean Factory (Steps 51–75)
51. **Step 51:** Create `src/types/Genotype.ts`: Define the 9 Genes as normalized floats [0, 1].
52. **Step 52:** Map genes to specific indices: $g_m$ (Metabolism), $g_v$ (Speed), $g_w$ (Awareness), etc.
53. **Step 53:** Create `src/sim/factories/BeanFactory.ts`.
54. **Step 54:** Implement `determineSex()`: Use `targetRatio` and `variance` from `BiologicalConfig`.
55. **Step 55:** Implement `generateGenotype()`: Assign gene values using controlled stochastic variance.
56. **Step 56:** Add `SexRatioVariance` slider logic to the Config Store.
57. **Step 57:** Create `GenotypeVisualizer`: A helper to generate color DNA strings for debugging.
58. **Step 58:** Implement `MutationNoise`: Controlled random shifts applied during initial creation.
59. **Step 59:** Create `Phenotype.ts`: State container for Energy, Size ($S$), Age ($t$), and Reputation ($R$).
60. **Step 60:** **Integration:** Link Genotype traits to initial Phenotype values (e.g., higher $g_v$ sets higher $v_{max}$).
61. **Step 61:** Implement `TraitClamping`: Prevent "Super-Beans" via hard limits on gene combinations.
62. **Step 62:** Add `InitialEnergyVariance` to the factory logic.
63. **Step 63:** Create `GenotypeManifest`: A telemetry logger that records every bean's birth DNA.
64. **Step 64:** Implement `SterilityProbability`: Rare chance for a bean to be born unable to mate.
65. **Step 65:** Add `BaseMetabolism` scaling function to the factory.
66. **Step 66:** Implement `SizeLimit` logic based on metabolic and dominance genes.
67. **Step 67:** Create the `BiologicalProfile` object for each spawned bean.
68. **Step 68:** **Wiring:** Register all new beans in the `SimulationCore` entity map.
69. **Step 69:** Implement UUID assignment for every bean instance.
70. **Step 70:** **Verification:** Spawn 100 beans and verify the Sex Ratio is within the defined variance.
71. **Step 71:** Add `FertilityGene` ($g_f$) to the Genotype definition.
72. **Step 72:** Add `LongevityGene` ($g_l$) to the Genotype definition.
73. **Step 73:** Implement `InheritanceHooks`: Placeholders for the mating crossover system.
74. **Step 74:** Create `BeanRegistry` service for easy lookups by ID.
75. **Step 75:** **Milestone:** Bean creation is fully decoupled and mathematically initialized.

---

## Module 4: Metabolism & Physical Systems (Steps 76–100)
76. **Step 76:** Create `src/sim/systems/MetabolismSystem.ts`.
77. **Step 77:** **Integration:** Implement Basal Burn: $B = B_0 \cdot (1 + g_m) \cdot (1 + S)$.
78. **Step 78:** **Integration:** Implement Brain Tax: $E_{cost} = g_w \cdot K_{brain}$.
79. **Step 79:** Implement the `EnergyDeduction` loop inside the system.
80. **Step 80:** Create `src/sim/systems/GrowthSystem.ts`.
81. **Step 81:** **Integration:** Implement Life Bell Curve $S^*(t)$ for calculating Target Size.
82. **Step 82:** Implement `Delta_S_Plus`: Logic for converting excess energy to fat storage.
83. **Step 83:** Implement `Delta_S_Minus`: Logic for burning fat storage when energy is low.
84. **Step 84:** Define $P_{death}$ starvation thresholds.
85. **Step 85:** **Wiring:** Link Growth System updates to follow Metabolism System calculations.
86. **Step 86:** Add `GrowthEnergyCost`: The energy "price" of increasing physical mass.
87. **Step 87:** Implement `StarvationStun`: Movement speed drops when energy < 10%.
88. **Step 88:** Add `EnergyBuffering` logic to smooth out energy fluctuations.
89. **Step 89:** **Integration:** Implement the Speed Penalty: $Speed \propto 1/S$.
90. **Step 90:** Add `Metabolism_UI` debug strings to appear over bean sprites.
91. **Step 91:** Implement `NaturalDeathProbability` (Exponentially increases with age $t$).
92. **Step 92:** Add `ImmuneSystem` gene logic to survival probabilities.
93. **Step 93:** Implement `AgeingAcceleration`: Stress/Starvation speeds up the aging process.
94. **Step 94:** Create `HealthSystem.ts` to aggregate overall vitality.
95. **Step 95:** Add `Hibernation` state: Drastic reduction in metabolism at the cost of movement.
96. **Step 96:** Implement `MetabolicEfficiency` curves for gene variations.
97. **Step 97:** Implement `OrganFailure` age checks.
98. **Step 98:** Add `DigestiveCooldown` after eating food.
99. **Step 99:** **Wiring:** Link energy level telemetry to the central Recorder.
100. **Step 100:** **Milestone:** The biological Life Cycle is mathematically complete and stable.

---

## Module 5: Movement & Physics (Steps 101–125)
101. **Step 101:** Create `src/sim/systems/MovementSystem.ts`.
102. **Step 102:** **Integration:** Implement $V_{max} = V_{base} \cdot f_{age} \cdot f_{size}$.
103. **Step 103:** **Integration:** Implement Movement Cost: $M = c_v |\Delta v| + c_t |\Delta \theta| + c_c |v|$.
104. **Step 104:** Implement `KinematicUpdate`: Basic Euler integration for position.
105. **Step 105:** Implement `WallReflection`: Physics bounce logic for map boundaries.
106. **Step 106:** Add `CollisionDamage`: Energy loss incurred when hitting walls.
107. **Step 107:** **Wiring:** Deduct movement cost $M$ from the Bean's Energy pool.
108. **Step 108:** Implement `Friction`: Gradual velocity decay when not accelerating.
109. **Step 109:** Add `TurnRateClamping` to prevent instantaneous 180-degree turns.
110. **Step 110:** Implement `SteeringBehaviors`: Seek, Flee, and Arrive logic.
111. **Step 111:** Add `Momentum`: Mass ($S$) influences inertia and braking distance.
112. **Step 112:** Implement `AvoidanceForce` for map borders.
113. **Step 113:** Add `WanderNoise` to simulate natural exploration.
114. **Step 114:** Implement `VelocityClamping` to stay within world speed limits.
115. **Step 115:** Add `MovementInertiaGene` ($g_i$) implementation.
116. **Step 116:** Implement `TargetTracking`: Smoothly rotate to face movement direction.
117. **Step 117:** Add `CollisionHeat`: Tiny energy loss when beans bump into each other.
118. **Step 118:** Implement `StepAnimationTrigger` for visual feedback.
119. **Step 119:** Add `OrientationSmoothing` for cleaner rendering.
120. **Step 120:** Create `KinematicSnapshot` for the telemetry system.
121. **Step 121:** Implement `TerrainResistance` placeholders.
122. **Step 122:** Add `Dash` mechanic: A high-energy burst of speed.
123. **Step 123:** **Verification:** Ensure movement cost scales with $v^2$ as per formula.
124. **Step 124:** Finalize movement kinematics and collision resolution.
125. **Step 125:** **Milestone:** Physics are energy-constrained and physically plausible.

---

## Module 6: Environment & Intake (Steps 126–150)
126. **Step 126:** Create `src/sim/systems/EnvironmentSystem.ts`.
127. **Step 127:** Implement Food Spawning logic based on Ticks.
128. **Step 128:** Implement `FoodPlacementStrategy` (Random, Clustered, or Zonal).
129. **Step 129:** Define `FoodEnergyValue` in the Config Store.
130. **Step 130:** Implement `detectIntake`: Proximity-based eating detection.
131. **Step 131:** Implement `FoodDepletion`: Removing food entities when consumed.
132. **Step 132:** Implement `RegrowthRate` calculations based on population size.
133. **Step 133:** Add `PoisonFood` variance (Rare).
134. **Step 134:** Implement `FoodDecay`: Food items lose energy over time.
135. **Step 135:** Create `src/render/entities/FoodSprite.ts`.
136. **Step 136:** **Wiring:** Implement `RenderBridge.reconcileFood()` for Phaser.
137. **Step 137:** Implement `SeasonalVariation`: Food spawns less frequently in "Winter".
138. **Step 138:** Implement `SpatialGrid` optimization for food lookups.
139. **Step 139:** Add `MaxFoodDensity` clamping to prevent memory overflows.
140. **Step 140:** Implement `FoodValueVariance`: Nutritious vs. Junk food.
141. **Step 141:** Add `ResourceScarcity` modifiers based on world seed.
142. **Step 142:** Implement `FoodSproutingAnimation` hooks.
143. **Step 143:** Add `NutrientDensity` maps (Heatmap logic).
144. **Step 144:** Implement `FoodPersistence` age limits.
145. **Step 145:** Create `EnvironmentSnapshot` telemetry.
146. **Step 146:** Add `WindEffect` to drift food clusters.
147. **Step 147:** Implement `WaterSource` static entity placeholders.
148. **Step 148:** Implement `FoodType` differentiation (Protein vs. Carb).
149. **Step 149:** Finalize environment tick logic.
150. **Step 150:** **Milestone:** The world provides resources that sustain the beans.

---

## Module 7: Perception (Steps 151–175)
151. **Step 151:** Create `src/sim/systems/PerceptionSystem.ts`.
152. **Step 152:** Implement `SpatialHashing` for fast O(1) neighbor lookups.
153. **Step 153:** **Integration:** Implement Awareness Blur $\epsilon$ based on $g_w$.
154. **Step 154:** Implement `AwarenessRange` limits.
155. **Step 155:** Implement `FieldOfView` (FOV) angular checks.
156. **Step 156:** Create the `MemoryComponent` for the Bean entity.
157. **Step 157:** Implement `ForgetRate`: Older perceived locations are deleted.
158. **Step 158:** Add `IdentificationNoise`: Mistaking a bean for food or vice-versa.
159. **Step 159:** Implement `OcclusionCheck`: Beans blocking the view of food.
160. **Step 160:** Add `Hearing` logic: Non-directional proximity sensing.
161. **Step 161:** Implement `ThreatAssessment`: Classifying neighbors as Threat or Mate.
162. **Step 162:** Add `ReputationSensing`: Seeing the $R$ value of others.
163. **Step 163:** Implement `VisibilityFactors` based on size and current velocity.
164. **Step 164:** **Wiring:** Deduct `PerceptionCost` from Energy pool.
165. **Step 165:** Implement `AttentionLimit`: Max 5 targets tracked at once.
166. **Step 166:** Add `PerceptionCooldown` intervals.
167. **Step 167:** Create `VisionCone` debug visualizer in Phaser.
168. **Step 168:** Implement `ScentTrails` placeholder logic.
169. **Step 169:** Add `SocialPerception`: Sensing group density.
170. **Step 170:** Implement `SpatialUpdateRate` Level-of-Detail (LOD).
171. **Step 171:** Add `AttentionFlicker` noise to perceived coordinates.
172. **Step 172:** Link `MemoryDurationGene` to the Perception System.
173. **Step 173:** Add `SignalToNoiseRatio` math to awareness checks.
174. **Step 174:** Finalize sensing and spatial memory logic.
175. **Step 175:** **Milestone:** Beans can "see" and "remember" their environment.

---

## Module 8: Action Utility & Decision AI (Steps 176–200)
176. **Step 176:** Create `src/sim/systems/ActionSystem.ts`.
177. **Step 177:** Define `ActionType` menu (WANDER, SEEK_FOOD, MATE, ATTACK, IDLE).
178. **Step 178:** **Integration:** Implement Utility: $U(a) = \sum w_i \cdot O_i(a) + \epsilon$.
179. **Step 179:** Map Genotype genes to specific utility weights (e.g., $g_m \to$ SEEK_FOOD).
180. **Step 180:** **Integration:** Implement "Action Inertia": +10% utility to stay on current task.
181. **Step 181:** Implement the `TargetPicker` logic for the highest utility item.
182. **Step 182:** Add `DesperationMultiplier`: Low energy boosts food utility.
183. **Step 183:** Implement `ActionEnergyCosts`: Each action has a flat fee.
184. **Step 184:** Add `FearUtility`: High aggression neighbors boost Flee utility.
185. **Step 185:** Implement `CuriosityBias`: Explore areas with low perception history.
186. **Step 186:** Add `EfficiencyThreshold`: Only seek if distance cost < energy gain.
187. **Step 187:** Implement `SocialBias`: Reputation $R$ influences interaction utility.
188. **Step 188:** Add `AggressionBias` based on dominance gene $g_d$.
189. **Step 189:** Implement `ActionLockTime`: Prevent mid-tick decision jitter.
190. **Step 190:** Add `BoredomCounter`: Increases Wander utility over time.
191. **Step 191:** Implement `EnergySafetyMargin` logic.
192. **Step 192:** Create "Thought Bubble" icon bridge to the Sprite component.
193. **Step 193:** Add `PersonalityVariance` to the weight calculation.
194. **Step 194:** Implement `DecisionCooldown` intervals to save CPU.
195. **Step 195:** Add `StressLevels` impact on decision noise.
196. **Step 196:** Implement `PanicMode` when energy is critical.
197. **Step 197:** Add `AltruismWeight` gene link.
198. **Step 198:** Implement `DeceptionUtility` placeholders.
199. **Step 199:** Finalize the AI decision engine.
200. **Step 200:** **Milestone:** Emergent survival and social behavior observed.

---

## Module 9: Social Interaction & Reproduction (Steps 201–225)
201. **Step 201:** Create `src/sim/systems/SocialSystem.ts`.
202. **Step 202:** **Integration:** Implement Attack Deterrence $D$ formula.
203. **Step 203:** Implement `CombatResolution`: Energy theft logic.
204. **Step 204:** **Integration:** Implement Reputation Decay $\lambda$.
205. **Step 205:** Implement `MatingHandshake`: Two-way attractiveness $A_{mate}$ check.
206. **Step 206:** Create `src/sim/utils/GeneticMixer.ts`.
207. **Step 207:** Implement DNA Crossover logic (Blending + Mutation Noise).
208. **Step 208:** Implement `SpawnOffspring`: Create new bean at parent midpoint.
209. **Step 209:** Deduct `MatingEnergyCost` from both parents.
210. **Step 210:** Implement `MatingCooldown` to prevent population explosions.
211. **Step 211:** Add `ParentalBond` duration timers.
212. **Step 212:** Implement `IncestPenalty` (Genetic damage if too related).
213. **Step 213:** Add `DominanceHierarchies` (Rank tracking).
214. **Step 214:** Implement `GroupFormation`: Clustering based on high $R$.
215. **Step 215:** Add `CooperationBonus`: Shared food intake logic.
216. **Step 216:** Implement `Cannibalism` utility for extreme desperation.
217. **Step 217:** Add `PheromoneMessaging` placeholder.
218. **Step 218:** Implement `SexualDimorphism` visual traits.
219. **Step 219:** Add `MatingDance` movement patterns.
220. **Step 220:** Implement `Territoriality` logic.
221. **Step 221:** Add `Grooming`: Interaction to build reputation $R$.
222. **Step 222:** Implement `Infanticide` aggression logic.
223. **Step 223:** Add `SiblingRivalry` logic.
224. **Step 224:** Finalize social interaction loops.
225. **Step 225:** **Milestone:** Generations evolve through social and sexual selection.

---

## Module 10: Telemetry, Analytics & Replay (Steps 226–250)
226. **Step 226:** Create `src/sim/data/Recorder.ts`.
227. **Step 227:** Implement `CaptureTick`: Full snapshot of all entities.
228. **Step 228:** Implement `DeltaCompression`: Only record changes to save memory.
229. **Step 229:** Create the `HistoryBuffer` (Last 10,000 ticks).
230. **Step 230:** Implement `JSONExporter` for the session log.
231. **Step 231:** Create `src/render/ReplayEngine.ts`.
232. **Step 232:** Implement `ScrubberUI`: Drag the timeline back and forth.
233. **Step 233:** Create `AnalyticsPanel` using Tweakpane.
234. **Step 234:** Implement Real-time Population Graphing.
235. **Step 235:** Implement Gene Dominance Histograms.
236. **Step 236:** Add "AnomalyDetector" to catch logic bugs.
237. **Step 237:** Implement `SeedCloning`: Restart from a specific tick.
238. **Step 238:** Add `ExtinctionPredictor` logic.
239. **Step 239:** Implement `HeatmapExporter`: Death and Birth locations.
240. **Step 240:** Add `LiveConfigHotReload` for all constants.
241. **Step 241:** Implement `FitnessScore` tracking per lineage.
242. **Step 242:** Create `WorldSnapshotExporter`.
243. **Step 243:** Add `PerformanceMonitor` (Logic vs. Render time).
244. **Step 244:** Implement `SnapshotDiffing` for audit logs.
245. **Step 245:** Create `AutomatedTuning` utility for stable populations.
246. **Step 246:** Final UI Polish: Menus, Themes, and Icons.
247. **Step 247:** Code Audit: Full type safety and leak check.
248. **Step 248:** Final Stress Test: Run 1,000 beans for 100k ticks.
249. **Step 249:** Finalize README and Documentation.
250. **Step 250:** **Final Milestone:** The Bean World simulation is complete and verified.