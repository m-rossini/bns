# Configuration and Architecture Reference

This document is the map of every tunable domain in Bean World: what each
configuration field means, how the values relate to each other, and which
abstract interface is fulfilled by which concrete implementation.

The single source of truth is [`sim/config.py`](../sim/config.py). Nothing in the
runtime should hardcode a value that belongs there.

## Mental model

```
SimulationConfig
    -> Container(config)        # wiring + initial state
        -> World                # geometry, cells, barriers
        -> Calendar             # tick -> day / season / year
        -> Environment          # season + day/night + weather + readings
        -> Spawn pipeline       # placement -> gender -> genotype -> beans
        -> strategies           # movement, energy, barrier, weather, ...
    -> GameSession              # mutable runtime state (beans, corpses, clock)
    -> main._step()             # one fixed simulation tick
```

Two layers must stay separate:

* **Abstract layer** (`sim/interfaces/`): what a subsystem must be able to do.
  The engine talks only to these interfaces.
* **Physical layer** (`sim/implementations/` and `sim/domain/`): the concrete
  algorithms and data that currently satisfy the interfaces.

Swapping behaviour means changing a config name or wiring a different class; it
must not require editing the tick loop.

## Top-level configuration

`SimulationConfig` composes the domains below.

| Field | Type | Purpose |
|---|---|---|
| `world` | `WorldConfig` | Arena size, cell grid, gradient orientation, wrapping. |
| `time` | `TimeConfig` | Tick rate, day/season lengths, playback scale, frame cap. |
| `seasons` | `list[SeasonConfig]` | Ordered season definitions; names and count are data. |
| `daynight` | `DayNightConfig` | Sun/moon arcs, sky colours, shading, phase thresholds. |
| `weather` | `WeatherConfig` | Per-cell weather field, fronts, offsets, light factors. |
| `barriers` | `BarrierConfig` | Density-based obstacle coverage, size limits, colour, seed. |
| `bean_placement` | `BeanPlacementConfig` | Position algorithm, density tier, gender split. |
| `creation` | `CreationConfig` | Population size and per-bean genotype draw. |
| `movement` | `MovementConfig` | How beans move and bounce. |
| `energy` | `EnergyConfig` | Passive energy gain strategy and rates. |
| `corpse` | `CorpseConfig` | Dead-bean food, decay, feeding and poisoning. |
| `food` | `FoodConfig` | Renewable morsels, seasonal top-up, appetite, placement. |
| `environment` | `EnvironmentConfig` | Strategy names, climate gradients, microclimate. |
| `logging` | `LoggingConfig` | Console/file logging and event sampling. |
| `persistence` | `PersistenceConfig` | Snapshot save/load and reproducibility. |
| `random` | `RandomConfig` | Global RNG seed (`None` = system entropy). |
| `debug` | `bool` | Enables debug-only behaviour in the container. |
| `tick_rate` | `float` | Simulation ticks per real second (default `30`). |

The shipped defaults live in `DEFAULT_CONFIG` at the bottom of `sim/config.py`.
Notable shipped values: `1200 x 800` world, `10` world-unit cells
(`120 x 80` cells), four seasons, `30` ticks/s, `1280`-ish default population
(density-based), female/male split `90/10`.

## 1. World and geometry

`WorldConfig`

| Field | Default | Meaning |
|---|---|---|
| `width`, `height` | `1200.0`, `800.0` | Arena size in **world units**. |
| `cell_size` | `10.0` | Side of a square weather/light cell in world units. |
| `orientation` | `NORTH_SOUTH` | Default direction for climate gradients. |
| `wrap_around` | `False` | Reserved world-edge behaviour. |

Derived values are `cols = round(width / cell_size)` and
`rows = round(height / cell_size)`. Weather, light, temperature, humidity and
pressure are sampled per cell; the renderer maps world units to pixels with one
uniform scale and never assumes a cell pixel size.

### Gradients

`GradientConfig(start, end, orientation=None)` is used for climate readings.
A position is normalised to `factor` in `[0, 1]`:

```
u = clamp(x / width), v = clamp(y / height)
north_south   -> v          south_north  -> 1 - v
west_east     -> u          east_west    -> 1 - u
diagonal_up   -> (u + v) / 2
diagonal_down -> (u + 1 - v) / 2
centre_out    -> radial distance from centre / sqrt(2)
out_centre    -> 1 - centre_out
value = start + (end - start) * factor
```

If `orientation` is `None`, the world's `orientation` is used. Unknown
orientation strings fall back to `NORTH_SOUTH` with a warning.

## 2. Time and calendar

`TimeConfig`

| Field | Default | Meaning |
|---|---|---|
| `ticks_per_day` | `1200` | Ticks per in-game day (40 s at 30 ticks/s). |
| `ticks_per_season` | `4800` | Ticks per season (4 days by default). |
| `start_tick` | `0` | Calendar offset at construction. |
| `initial_time_scale` | `1.0` | Perceived speed at startup. |
| `time_scale_min`, `time_scale_max` | `0.1`, `4.0` | Playback slider bounds. |
| `max_ticks_per_frame` | `5` | Upper bound on ticks per rendered frame. |

The fixed timestep is `1 / tick_rate` (default `1/30 s`). `time_scale` changes
only perception; it does not change `tick_rate` or the fixed step.

`Calendar` is the only time authority:

```
day           = tick // ticks_per_day + 1          # 1-based
day_fraction  = (tick % ticks_per_day) / ticks_per_day   # 0 midnight, 0.5 noon
season_index  = (tick // ticks_per_season) % season_count
season        = season_names[season_index]
season_progress = (tick % ticks_per_season) / ticks_per_season
year          = tick // (ticks_per_season * season_count) + 1
```

Seasons are siblings of day/night: both read the calendar, neither owns the
other.

## 3. Seasons and solar profile

`SeasonConfig`

| Field | Default | Meaning |
|---|---|---|
| `name` | required | Season name shown in the HUD and used by weather weights. |
| `ground_color` | `(96,170,88)` | Base ground colour. |
| `ground_gradient` | `None` | Optional explicit `(start, end)` colour pair over the season. |
| `detail_colors` | `[]` | Speckle colours used by rendering. |
| `base_temperature` | `14.0` | Seasonal mean temperature (°C). |
| `temperature_swing` | `7.0` | Day/night amplitude (°C). |
| `humidity` | `0.55` | Seasonal baseline relative humidity `0..1`. |
| `pressure_hpa` | `1013.0` | Seasonal baseline pressure. |
| `ground_meaning` | `"growing season"` | Human label for the legend. |
| `sun_intensity` | `1.0` | Peak sun brightness (>1 summer, <1 winter). |
| `daylight_fraction` | `0.5` | Share of the day the sun is above the horizon. |
| `weather_weights` | `{}` | Base weights for `clear/cloudy/rain/storm/snow`. |
| `temperature_variation` | `3.0` | ± °C sampled onto the seasonal mean from year 2 on. |
| `temperature_swing_variation` | `1.0` | ± °C sampled onto the day/night swing from year 2 on. |
| `humidity_variation` | `0.10` | ± baseline relative humidity from year 2 on. |
| `pressure_variation` | `5.0` | ± hPa sampled onto seasonal pressure from year 2 on. |
| `sun_intensity_variation` | `0.10` | ± solar peak sampled from year 2 on. |
| `daylight_variation` | `0.05` | ± day-length share sampled from year 2 on. |
| `weather_weight_variation` | `0.25` | ± fraction re-rolled per weather weight from year 2 on. |

`SeasonStrategy` owns **how much sun** the world gets. It blends the current
season's `sun_intensity` and `daylight_fraction` into the next season during the
last quarter of the season:

```
transition_weight = smoothstep((season_progress - 0.75) / 0.25)  # 0 .. 1
solar.sun_intensity      = lerp(current, next, transition_weight)
solar.daylight_fraction  = clamp(lerp(current, next, transition_weight), 0.05, 0.95)
```

Ground colour also interpolates: first half darkens the base by 12% into the
base; second half blends towards the next season's base.

Year 1 of a run uses the configured values as the baseline. From year 2 on,
every occurrence of a season is re-rolled inside the `*_variation` half-ranges
above, so repeated cycles never repeat exactly. The draw is deterministic per
`(season_seed, year, season_index)`: set `EnvironmentConfig.season_seed` for a
reproducible sequence, or leave it `None` for a fresh one every run. Snapshots
persist the resolved seed, so a resumed run keeps its exact season sequence.
`ISeasonStrategy.weather_weights(season, year)` exposes the varied weights; the
environment passes the current calendar year, and the weather strategy reshapes
them further through `ClimateContext.adjusted_weather_weights()`.

This is also the hook future food systems will read: temperature, sun
(`sun_intensity`, `daylight_fraction`), humidity and pressure already flow
through `SeasonPalette` → `ClimateContext` → weather, so food availability can
derive from the same varied seasonal baselines without new plumbing.

## 4. Day/night and light

`DayNightConfig`

| Field | Default | Meaning |
|---|---|---|
| `sun_speed`, `moon_speed` | `1.0` | Multipliers on the celestial arcs. |
| `moon_phase_offset` | `0.25` | Shifts the moon phase. |
| `local_shading` | `0.10` | Amplitude of terrain/cover shading. |
| `shading_scale_x`, `shading_scale_y` | `190`, `150` | Shading lobe size in world units. |
| `night_threshold` | `0.12` | Below this sun altitude it is night. |
| `twilight_threshold` | `0.45` | Below this it is dawn/dusk. |
| `night_sky`, `day_sky`, `twilight_sky`, `overcast_sky` | colours | Sky blending palette. |
| `sun_color`, `moon_color`, `star_color` | colours | Celestial rendering. |

The sun is placed inside the season's daylight window:

```
start, end = 0.5 - daylight/2, 0.5 + daylight/2
sun_arc = 0 outside [start, end]
sun_arc = sin(pi * (day_fraction - start) / (end - start)) inside
local_shade = 1 - local_shading * (0.5 + 0.5*sin(x/sx)*cos(y/sy))
light = clamp(sun_arc * local_shade * solar.sun_intensity, 0, 1)
```

`night` / `dawn` / `day` / `dusk` are derived from `sun_arc` against the two
thresholds.

## 5. Weather

`WeatherConfig`

| Field | Default | Meaning |
|---|---|---|
| `change_interval` | `600` | Ticks between weather-field rebuilds. |
| `seed` | `1337` | Deterministic seed. |
| `front_count` | `3` | Number of moving weather fronts. |
| `background_coverage` | `0.6` | Share of cells under the background condition. |
| `front_radius_min_cells`, `front_radius_max_cells` | `0` | `0` = derive from grid size. |
| `front_drift_cells` | `0.0` | Optional drift per rebuild. |
| `background_patch_scale` | `1.0` | >1 creates smaller, more frequent patches. |
| `conditions` | `clear, cloudy, rain, storm, snow` | Allowed conditions. |
| `temperature_offsets` | clear +2, cloudy 0, rain -2, storm -4, snow -5 | Added to temperature. |
| `humidity_offsets` | clear -0.10, cloudy +0.02, rain +0.20, storm +0.25, snow +0.08 | Added to humidity. |
| `pressure_offsets` | clear +4, cloudy -3, rain -8, storm -18, snow -5 | Added to pressure. |
| `light_factors` | clear 1.0, cloudy 0.82, rain 0.68, storm 0.5, snow 0.85 | Multiplies light. |

`WeatherStrategy` builds a per-cell field as the union of:

1. a background condition drawn from the season's adjusted weights, applied to
   a deterministic patchy mask (`background_coverage`), and
2. `front_count` discs of different conditions.

The field is rebuilt every `change_interval` ticks with
`random.Random(f"{seed}-{interval}-{season}")`. A cell takes the most severe
condition among background and covering fronts (`clear < cloudy < rain/snow <
storm`). The aggregate `weather` reading is the background condition.

### Climate-adjusted weather weights

`ClimateContext.adjusted_weather_weights()` reshapes the season's weights:

```
rain   *= ramp(temp, 1..8) * (0.55 + 0.9*humidity)
snow   *= (1 - ramp(temp, 1..6)) * (0.7 + 0.6*humidity)
storm  *= (0.5 + 0.5*ramp(temp, 6..20))
          * (0.5 + humidity)
          * (0.75 + 0.25*(1 - ramp(pressure, 995..1015)))
clear  *= 1.2 - 0.5*humidity
cloudy *= 0.9 + 0.4*humidity
if temp <= 1: move rain weight into snow
```

If every weight becomes zero, the field falls back to `clear`.

## 6. Environment readings

`EnvironmentConfig`

| Field | Default | Meaning |
|---|---|---|
| `weather_strategy` | `"WeatherStrategy"` in `DEFAULT_CONFIG` | `None` = static clear weather. |
| `season_strategy` | `"SeasonStrategy"` | `None` = static palette/solar. |
| `daynight_strategy` | `"DayNightStrategy"` | `None` = static daytime light. |
| `season_seed` | `None` | Seed for year-to-year season variation (`None` = fresh each run). |
| `temperature_gradient` | `(-4, +4)` | Added to seasonal temperature. |
| `humidity_gradient` | `(-0.12, +0.12)` | Added to seasonal humidity. |
| `pressure_gradient` | `(-6, +6)` | Added to seasonal pressure. |
| `light_gradient` | `(0.88, 1.08)` | Multiplies light. |
| `microclimate` | `1.0` | Scales fine spatial noise (`0` disables). |

Readings at a position (`Environment`):

```
light       = clamp(daynight_light * light_gradient * weather_light_factor, 0, 1)
temperature = season.base_temperature + season.temperature_swing*(2*light - 1)
              + weather.temperature_offset + temperature_gradient
              + 2.2*micro*sin(x/210)*cos(y/170)
              + 0.8*micro*sin((x+y)/95)
humidity    = clamp(season.humidity + weather.humidity_offset
              + humidity_gradient
              + 0.05*micro*sin(x/130)*cos(y/110), 0, 1)
pressure    = round(season.pressure_hpa + weather.pressure_offset
              + pressure_gradient
              + 1.5*micro*sin(x/140)*cos(y/120), 1)
```

`light` therefore drives temperature; weather drives light, temperature,
humidity and pressure; season sets the baselines; gradients and microclimate add
spatial variation. This is the main correlation to remember when tuning a
biome.

`Environment.snapshot_state()` saves `calendar_tick` and the weather field.
Derived caches (palette/solar) are intentionally recomputed on load.

## 7. Barriers

`BarrierConfig`

| Field | Default | Meaning |
|---|---|---|
| `color` | `(255,208,64)` | Fill colour for every barrier. |
| `density` | `0.01` | Target share of grid cells covered by barriers (1%). |
| `min_span_cells` | `3` | Minimum cells per axis; avoids tiny, hard-to-see specks. |
| `max_span_cells` | `8` | Maximum cells per axis. |
| `seed` | `None` | `None` = fresh layout every run; int = reproducible. |
| `margin_cells` | `2` | Keep barriers away from the border. |

Barriers are axis-aligned rectangles snapped to the cell grid. The generator
computes a target area rather than a fixed count:

```
target_cells = round(world.cols * world.rows * density)
```

It keeps adding non-overlapping obstacles with spans drawn from
`[min_span_cells, max_span_cells]` until the covered area reaches
`target_cells` (or placement attempts run out). With the default `120 x 80`
grid and density `0.01`, the target is 96 cells; uniform spans `3..8` average
about 30 cells each, so a run usually produces 3–4 large barriers. Set
`density=0` to remove barriers entirely.

Placement is non-deterministic by default (`seed=None`). Set an integer seed
for a reproducible layout; snapshots always store the generated barriers, so a
resumed game keeps its exact obstacle map. `BarrierStrategy` validates maximum
span and world bounds. Movement reflects a bean that touches a barrier and
pushes it out; beans cannot spawn overlapping one.

## 8. Bean placement and gender

`BeanPlacementConfig`

| Field | Default | Meaning |
|---|---|---|
| `strategy_name` | `"poisson_disc"` | One of `PLACEMENT_STRATEGY_NAMES`. |
| `density_tier` | `"average"` | `sparse`, `average`, `heavy`, `super`. |
| `variance` | `0.10` | Population-count variation in `[0, 1]`. |
| `seed` | `1337` | Deterministic placement seed. |
| `gender_ratios` | `{male:50, female:50}` | Must sum to 100. |
| `gender_colors` | blue/red | Per-gender RGB. |
| `bean_radius` | `5.0` | Collision radius used by placement and feeding. |

Density coefficients (beans per world-unit²) and resource thresholds:

| Tier | Density | Noise threshold |
|---|---|---|
| `sparse` | `0.0005` | `0.75` |
| `average` | `0.0020` | `0.50` |
| `heavy` | `0.0060` | `0.25` |
| `super` | `0.0150` | `0.05` |

Placement strategies all return collision-free positions inside the world,
rejecting overlaps with barriers, borders and already-placed beans:

| Name | Config | Algorithm |
|---|---|---|
| `poisson_disc` | `PoissonDiscConfig` | Minimum spacing `r = sqrt(area/N) * base_spacing_scale`; candidates sampled around existing points; `max_retry_limit` attempts. |
| `symmetrical` | `SymmetricalConfig` | Generates one slice and rotates it across `symmetry_axes`. |
| `colony_cluster` | `ColonyClusterConfig` | `clusters = round(area / area_per_cluster)`; Gaussian spread around mother centroids (`sigma`). |
| `center_to_border` | `CenterToBorderConfig` | `r = R_max * u^falloff_exponent`; higher exponent concentrates at the centre. |
| `border_to_center` | `BorderToCenterConfig` | Outer ring: `R_min = R_max*(1 - ring_thickness_ratio)`; `r = sqrt(R_min² + u*(R_max² - R_min²))`. |
| `linear_gradient` | `LinearGradientConfig` | Acceptance weight `P(t) = 1 + bias_strength*(t - 0.5)` along `direction_angle`. |
| `resource_gradient` | `ResourceGradientConfig` | Noise field `noise_frequency`; accept cells above the tier threshold (or configured `threshold`). |

`GenderController` uses the largest-remainder method to assign exact counts
whose sum is the population, then shuffles the assignment so genders are
spread across positions.

## 9. Bean creation and genotype

`CreationConfig`

| Field | Default | Meaning |
|---|---|---|
| `strategy_name` | `"density_based"` | `density_based` or `fixed_amount`. |
| `fixed_amount` | `FixedAmountCreationConfig` | Config for the fixed strategy. |
| `genotype_ranges` | `GenotypeConfig` | Per-gene draw ranges. |
| `genotype_seed` | `1337` | Seed for the per-bean genotype draw. |

`FixedAmountCreationConfig`: `total_beans` (default `1000`), `max_batches`,
`placement_overshoot`. It asks for extra candidates and trims to the exact
total.

Population formulas:

```
density_based: N = max(0, round(world_area * density_tier
                                * (1 + U(-variance, +variance))))
fixed_amount:  N = total_beans
```

Each bean then receives a genotype drawn from `GenotypeConfig`:

| Gene | Range | Effect |
|---|---|---|
| `energy_capacity` | `(800, 1200)` | Maximum stored energy. |
| `metabolic_rate` | `(0.5, 2.0)` | Passive energy cost per second. |
| `drag_coefficient` | `(0.005, 0.02)` | Quadratic movement cost. |
| `max_speed` | `(40, 80)` | Speed ceiling (world units/s). |
| `acceleration` | `(15, 45)` | Speed-change capability. |
| `digestion_efficiency` | `(0.35, 0.75)` | Fraction of corpse energy converted. |
| `digestion_capacity` | `(40.0, 120.0)` | Max food energy taken per contact (appetite). |
| `max_age_ticks` | species cap `3120` | Hard species ceiling. |
| `lifespan_fraction_floor` | `0.50` | Lower clamp for the inherited fraction. |
| `lifespan_tiers` | `0.70..1.00` by `0.05` | Discrete lifespan cohorts. |
| `lifespan_jitter` | `0.02` | Uniform noise added to the chosen tier. |
| `senescence_start_fraction` | `0.70` | Share of own lifespan before decline. |

Lifespan draw (two-stage, so cohorts are visible):

```
fraction = choice(lifespan_tiers) + U(-jitter, +jitter)
fraction = clamp(fraction, lifespan_fraction_floor, 1.0)
genotype.max_age_ticks = max(1, round(species_cap * fraction))
```

## 10. Lifespan, senescence and death

`Phenotype` carries mutable state: `current_energy`, `current_speed`,
`velocity`, `age`, `is_dormant`, `condition`, `efficiency`,
`digestion_capacity` (copied from the gene at creation),
`energy_eaten_total`, `energy_absorbed_total`, `color`. The two lifetime
counters accumulate food taken vs food converted and are the substrate future
evolution will select on.

Every simulation tick, `main._advance_life()`:

1. increments `phenotype.age` exactly once for every bean with a phenotype
   (movement no longer ages beans);
2. marks a bean dead when `age >= genotype.max_age_ticks` **or**
   `current_energy <= 0`;
3. takes old age before starvation when both are true;
4. turns the bean into a corpse, increments `deaths_old_age` or
   `deaths_starvation`, and logs `bean.died` with `cause` and `age`;
5. for survivors, applies senescence.

Senescence:

```
start = senescence_start_fraction * genotype.max_age_ticks
condition = 1.0                                        if age < start
condition = 1 - (age - start) / (max_age_ticks - start) otherwise
efficiency = clamp(genotype.digestion_efficiency * condition, 0, 1)
```

So old beans digest corpses less efficiently. If the last living bean dies,
`_step` sets `state = END`, `end_reason = "extinction"`, pauses the clock and
stops the rest of the frame. Corpses are left untouched.

## 11. Movement and energy

`MovementConfig`

| Field | Default | Meaning |
|---|---|---|
| `strategy_name` | `"straight_line"` | Current movement implementation. |
| `speed` | `60.0` | Initial speed in world units/s. |
| `random_initial_direction` | `True` | Random direction per bean. |
| `direction` | `(1,0)` | Global direction when random is off. |
| `bounce_on_edges` | `True` | Reflect at world edges. |

`StraightLineMovementStrategy` seeds `vx/vy` from the global RNG on first move,
then applies constant velocity with edge/barrier reflection. Each bounce costs
`10` energy. Per-tick cost:

```
metabolic = metabolic_rate * dt
drag      = drag_coefficient * speed² * dt
accel     = abs(acceleration) * dt * 0.5
total     = metabolic + drag + accel
```

At zero energy the bean becomes dormant (brown, no movement) until it recovers.

`EnergyConfig`

| Field | Default | Meaning |
|---|---|---|
| `strategy_name` | `"fixed"` | `fixed` or `per_day`. |
| `energy_per_tick` | `0.5` | Fixed gain per tick for non-dormant beans. |
| `energy_per_day` | `50.0` | Lump sum at each day boundary. |
| `resource_energy_factor` | `1.0` | Reserved for environmental gain. |

Fixed gain is `energy_per_tick * dt`; per-day gain is `energy_per_day` once per
calendar day. Gain is capped by `energy_capacity`.

## 12. Corpses and feeding

`CorpseConfig`

| Field | Default | Meaning |
|---|---|---|
| `basal_energy` | `200.0` | Initial food energy in a corpse. |
| `decay_per_tick` | `0.05` | Passive loss every tick. |
| `collision_loss_fraction` | `0.5` | Share of remaining energy transferred per contact. |
| `rotten_fraction` | `0.2` | At/below this share the next contact is rotten. |
| `poison_gain_fraction` | `0.5` | Fraction of the would-be gain lost when rotten. |
| `poison_energy_floor` | `1.0` | Poisoning can never take a bean below this. |

A dead bean becomes a `Corpse` immediately (no dormancy). Each tick corpses
decay, then living beans within `bean_radius` collide:

```
lost = corpse.energy * collision_loss_fraction
bean.current_energy += lost * phenotype.efficiency   # capped by capacity
corpse.energy -= lost
```

If the corpse is at or below `rotten_fraction` of its **initial** energy, the
next contact is rotten:

```
would_gain = corpse.energy * collision_loss_fraction * efficiency
bean.current_energy = max(poison_energy_floor, current_energy - would_gain * poison_gain_fraction)
corpse removed
```

## 13. Renewable food

`FoodConfig`

| Field | Default | Meaning |
|---|---|---|
| `strategy_name` | `"random"` | `None` disables food; `"random"` = `RandomFoodSpawnStrategy`. |
| `seed` | `None` | `None` = fresh morsels every run; int = reproducible. |
| `initial_total_energy` | `20000.0` | Food energy seeded at tick 0. |
| `target_total_energy` | `20000.0` | Level the top-up steers towards. |
| `top_up_interval_ticks` | `300` | Ticks between top-ups (10 s at 30 Hz). |
| `min_morsel_energy`, `max_morsel_energy` | `20.0`, `200.0` | Per-morsel energy draw range. |
| `food_radius` | `4.0` | Morsel radius (energy density varies, size does not). |
| `color` | `(200,80,220)` | Magenta-purple base; view brightens with remaining energy. |
| `margin_cells` | `1` | Keep morsels away from the border. |
| `max_items` | `600` | Cap on live morsels (perf guard). |
| `placement` | `FoodPlacementConfig` | Placement strategy and per-strategy config for morsel positions. |

`FoodPlacementConfig` mirrors `BeanPlacementConfig`: `strategy_name` selects
one of `PLACEMENT_STRATEGY_NAMES`, `seed` drives deterministic placement, and
each strategy has its own config object (`poisson_disc`, `symmetrical`,
`colony_cluster`, `center_to_border`, `border_to_center`, `linear_gradient`,
`resource_gradient`). The default is `poisson_disc` with
`base_spacing_scale=0.5`, which keeps morsels as dense as the old
uniform-random layout while guaranteeing they never overlap a barrier, the
world border, or another morsel.

Seeding sums to `initial_total_energy`; every `top_up_interval_ticks` the
strategy spawns the deficit to `target_total_energy × abundance`:

```
abundance = clamp(sun_intensity * (0.4 + daylight_fraction), 0.15, 1.6)
effective_target = target_total_energy * abundance
deficit = max(0, effective_target - current_total_energy)
```

`abundance` comes from the already-varied seasonal sun profile, so spring
grows ~0.85×, summer ~1.15×, autumn ~0.7× and winter ~0.4× — the level breathes
around the target instead of drifting, and future food systems can reuse the
same seasonal hook. The initial seeding asks the configured placement strategy
for the whole morsel set, so the starting distribution follows that strategy
and is collision-free. Later top-ups use uniform random positions validated
against the same constraints (a one-shot blue-noise layout cannot be extended
incrementally without over-spacing the new morsels). Snapshots store the
morsels, so a resumed run keeps its exact morsels. The view draws them in
poor/mid/rich size tiers (three batched draw calls) with brightness floored
so they read against any ground; the sidebar Food box shows morsel count,
average energy, total energy vs the seasonal target (`target × abundance`)
and the top-up interval.

Eating (`feed_beans_on_food`, runs in the lifecycle next to corpse feeding):

```
intake   = min(food.energy, phenotype.digestion_capacity, capacity_room)
absorbed = intake * phenotype.efficiency
food.energy -= intake   # remainder stays for later visits
phenotype.energy_eaten_total += intake
phenotype.energy_absorbed_total += absorbed
```

Depleted morsels are removed. Old beans with low `condition` absorb less, just
like with corpses.

## 14. Logging

`LoggingConfig`

| Field | Default | Meaning |
|---|---|---|
| `level` | `"INFO"` | Default log level. |
| `format`, `date_format` | see config | Console format. |
| `business` | `True` | Emit gameplay/business events. |
| `readings` | `True` | Emit per-cell DEBUG readings. |
| `readings_interval` | `60` | Ticks between reading samples. |
| `file_enabled` | `True` | Write a rotating per-run file. |
| `directory` | `"logs"` | Log directory. |
| `filename_prefix` | `"bean"` | File name prefix. |
| `max_bytes` | `10 MiB` | Rotation size. |
| `backup_count` | `5` | Rotated files kept. |

Runtime overrides: `BEAN_LOG_LEVEL` (or Makefile `LOG_LEVEL`), `BEAN_LOG_DIR`,
and `BEAN_LOG_FILE`. The active file is `logs/bean-<timestamp>-<pid>.log`.

## 15. Persistence and reproducibility

`PersistenceConfig`

| Field | Default | Meaning |
|---|---|---|
| `enabled` | `True` | Master switch for snapshots. |
| `directory` | `"saves"` | Default save directory. |
| `filename_prefix` | `"bean"` | File name prefix. |
| `autosave_initial` | `True` | Save the tick-0 state after spawning. |
| `save_on_exit` | `False` | Write a final snapshot when the process exits. |
| `save_path` | `None` | Explicit initial save path. |
| `load_path` | `None` | Explicit load path. |
| `schema_version` | `1` | Snapshot format version. |

Runtime variables:

* `BEAN_SAVE=<path>` — write the initial snapshot to exactly this path.
* `BEAN_LOAD=<path>` — restore this snapshot instead of creating beans.
* Empty, `0`, `false`, `no`, `off`, `none` mean "disabled".

A snapshot contains: the full encoded config, global RNG state, session state
and clock, death counters, world barriers, environment/calendar/weather state,
every bean (genotype + phenotype + velocity), every corpse, and every food
morsel. Loading rebuilds
the `Container` from the saved config and then overwrites its state, so the
same file reproduces the same run given the same code. Movement uses the global
RNG; the snapshot restores its state.

The Makefile mounts `SAVE_DIR` (default `./saves`) into the container and passes
`BEAN_SAVE`/`BEAN_LOAD` through. `make saves` lists snapshots.

## 16. Interfaces and their implementations

Every interface below lives in `sim/interfaces/`; each concrete implementation
follows it. `None` for a season/daynight/weather strategy means static fallback
values; the environment still runs its calendar and other strategy.

### `IWorld` (`sim/interfaces/world.py`)

- `domain/world.py:World` — the single implementation: bounds, cell grid,
  orientation, wrap/clamp, barrier storage, validation against the active
  barrier strategy. Selected by `WorldConfig`.

### `IBarrierStrategy` (`sim/interfaces/barrier.py`)

- `implementations/barrier/__init__.py:BarrierStrategy` — single
  implementation: colour, min/max span rules, density-based non-overlapping
  placement. Configured by `BarrierConfig`.

### `IPlacementStrategy` (`sim/interfaces/placement.py`)

- `implementations/placement/poisson_disc.py:PoissonDiscStrategy`
- `implementations/placement/symmetrical.py:SymmetricalStrategy`
- `implementations/placement/colony_cluster.py:ColonyClusterStrategy`
- `implementations/placement/center_to_border.py:CenterToBorderStrategy`
- `implementations/placement/border_to_center.py:BorderToCenterStrategy`
- `implementations/placement/linear_gradient.py:LinearGradientStrategy`
- `implementations/placement/resource_gradient.py:ResourceGradientStrategy`

Selected by `BeanPlacementConfig.strategy_name` or
`FoodPlacementConfig.strategy_name` (see `PLACEMENT_STRATEGY_NAMES`). The same
strategies position beans and food morsels; the caller passes its own
collision radius (bean radius or morsel radius).

### `IGenderController` (`sim/interfaces/gender.py`)

- `implementations/gender.py:GenderController` — single implementation:
  ratio-balanced, shuffled gender + colour assignment. Configured by
  `BeanPlacementConfig.gender_ratios` / `gender_colors`.

### `ISpawnController` (`sim/interfaces/placement.py`)

- `domain/spawn_controller.py:SpawnController` — single implementation:
  population sizing, placement strategy, gender controller orchestration.
  Compositional (no strategy-name selector).

### `IBeanCreationStrategy` (`sim/interfaces/creation.py`)

- `implementations/creation/density_based.py:DensityBasedCreationStrategy`
- `implementations/creation/fixed_amount.py:FixedAmountCreationStrategy`

Selected by `CreationConfig.strategy_name`.

### `IMovementStrategy` (`sim/interfaces/movement.py`)

- `implementations/movement/straight_line.py:StraightLineMovementStrategy` —
  single implementation (numba-accelerated collision helpers in
  `implementations/movement/numba_collisions.py`). Selected by
  `MovementConfig.strategy_name`.

### `IEnergyStrategy` (`sim/interfaces/energy.py`)

- `implementations/energy/fixed_energy.py:FixedEnergyStrategy`
- `implementations/energy/fixed_energy.py:PerDayEnergyStrategy`

Selected by `EnergyConfig.strategy_name`.

### `IFoodSpawnStrategy` (`sim/interfaces/food.py`)

- `implementations/food/random_food.py:RandomFoodSpawnStrategy` — single
  implementation: strategy-placed initial morsels, ranged morsel energies,
  interval top-up toward `target × abundance` (top-ups use uniform random
  collision-free positions).

Selected by `FoodConfig.strategy_name` (`None` disables food). Positions come
from `FoodConfig.placement`.

### `ISeasonStrategy` (`sim/interfaces/environment.py`)

- `implementations/season/__init__.py:SeasonStrategy` — single implementation:
  sun ownership via `solar_profile()`, palette, year-to-year variation, weather
  weights. Selected by `EnvironmentConfig.season_strategy`.

### `IDayNightStrategy` (`sim/interfaces/environment.py`)

- `implementations/daynight/__init__.py:DayNightStrategy` — single
  implementation: sun/moon arcs, light curve, phase, sky palette. Selected by
  `EnvironmentConfig.daynight_strategy`.

### `IWeatherStrategy` (`sim/interfaces/environment.py`)

- `implementations/weather/__init__.py:WeatherStrategy` — single
  implementation: patchy background + moving fronts from a per-interval seed.
  Selected by `EnvironmentConfig.weather_strategy`.

### `ICalendar` (`sim/interfaces/environment.py`)

- `domain/calendar.py:Calendar` — structural implementation (does not inherit
  the ABC, but satisfies it): tick → day / clock / season / year. Driven by
  `TimeConfig`.

### `IEnvironment` (`sim/interfaces/environment.py`)

- `domain/environment.py:Environment` — single implementation composing
  calendar + world + the three strategies into positional readings.
  Compositional (no single selector).

### `IRenderer` (`sim/interfaces/renderer.py`, `Protocol`)

- `rendering/arcade_view.py:ArcadeView` — structural implementation (satisfies
  the runtime-checkable `Protocol` without inheriting it): start/playing/
  paused/end screens + `flip()`. Used by the windowed path in `main.py`.

### Persistence (module functions, no interface)

- `sim/persistence.py`: `save_snapshot`, `load_snapshot`,
  `config_from_snapshot`, `restore_snapshot`, snapshot path helpers.
  Configured by `PersistenceConfig`.

## 17. Tick order

While the session is `PLAYING`, each fixed tick executes in this order:

1. `advance_clock()` decides how many ticks this frame may run.
2. `environment.advance_tick()` advances the calendar and rebuilds weather.
3. Energy strategy applies passive gains.
4. Movement strategy moves beans, applies movement costs and bounces.
5. `_advance_life()` ages beans, creates corpses, applies senescence, decays
   and feeds corpses, feeds beans on food morsels, tops food up toward the
   seasonal target, and detects extinction.
6. If extinction happened, state becomes `END` and the remaining ticks in the
   frame are skipped.

Once `END`, `_step` returns `0` immediately: the clock, environment, corpses and
beans are all frozen.

## 18. Correlation cheat sheet

* **Season → solar → day/night light → temperature.** `sun_intensity` and
  `daylight_fraction` set the light curve; temperature uses `2*light - 1`.
* **Weather → light, temperature, humidity, pressure.** Each condition has
  offsets/factors; the field chooses the condition per cell.
* **Gradients + microclimate → spatial variation.** They are added or
  multiplied on top of the seasonal/weather baseline.
* **Density/creation → population; genotype → individual capability.**
  Placement decides positions; genotype ranges decide speed, metabolism,
  capacity, digestion, appetite and lifespan.
* **Movement → energy cost; energy → dormancy/death.** Faster or heavier beans
  pay more; zero energy makes a corpse.
* **Age → condition → efficiency → feeding.** Old beans digest less.
* **Corpse energy → feeding → bean energy → survival.** Corpses decay and can
  poison when rotten.
* **Calendar → season/day → weather weights → field → readings.** Changing
  `ticks_per_day`/`ticks_per_season` changes how fast all of this evolves.
* **Policy speed vs move speed.** `MovementConfig.speed` is a physical
  velocity preset; `TimeConfig.time_scale` is playback perception only.

## 19. Common configuration recipes

**One permanent cold season**

```python
from dataclasses import replace
from sim.config import DEFAULT_CONFIG, SeasonConfig

config = replace(DEFAULT_CONFIG, seasons=[
    SeasonConfig(name="Permafrost", base_temperature=-8.0,
                 weather_weights={"snow": 70, "cloudy": 30}),
])
```

**Exact population and reproducible seed**

```python
config = replace(
    DEFAULT_CONFIG,
    creation=replace(
        DEFAULT_CONFIG.creation,
        strategy_name="fixed_amount",
        fixed_amount=replace(DEFAULT_CONFIG.creation.fixed_amount, total_beans=500),
    ),
    random=replace(DEFAULT_CONFIG.random, seed=42),
)
```

**Shorter-lived species**

```python
config = replace(
    DEFAULT_CONFIG,
    creation=replace(
        DEFAULT_CONFIG.creation,
        genotype_ranges=replace(
            DEFAULT_CONFIG.creation.genotype_ranges,
            max_age_ticks=1200,
        ),
    ),
)
```

**Replay a snapshot**

```bash
make run-local BEAN_LOAD=saves/bean-20260101-120000-12345.json
```

The loaded file supplies the config; `BEAN_LOAD` must point to a version-1
snapshot produced by the same code generation.
