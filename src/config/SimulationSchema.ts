
export interface WorldConfig {
  seed: number;
  ticksPerYear: number;
  width: number;
  height: number;
  male_bean_color: string  // Color for male beans (rendering).
  female_bean_color: string  // Color for female beans (rendering).
  male_female_ratio: number  // Ratio of males to females in population.
  population_density: number  // Number of beans per area unit.
  placement_strategy: string  // Algorithm for initial bean placement.
  population_estimator: string  // Method for estimating initial population.
  energy_system: string  // Energy system type used in simulation.
  environment: string  // Environment implementation to use (factory name)
  background_color: string  // Background color of the world.
  max_age_years: number  // Maximum bean age in years.
  rounds_per_year: number  // Simulation rounds per year.
}

export interface BeanConfig {

    speed_min: number  // Minimum allowed bean speed (units/step).
    speed_max: number  // Maximum allowed bean speed (units/step).
    max_age_rounds: number  // Maximum bean age in simulation rounds (ticks).
    initial_energy: number  // Starting energy for each bean.
    min_energy_efficiency: number  // Minimum energy efficiency at extreme ages (0-1).
    min_speed_factor: number  // Minimum speed factor at extreme ages (0-1).
    initial_bean_size: number  // Starting size for beans (arbitrary units).
    min_bean_size: number  // Minimum bean size before starvation (units).
    max_bean_size: number  // Maximum possible bean size (units).
    energy_baseline: number  // Neutral metabolism energy line (energy units).
    starvation_base_depletion: number  // Base size units consumed per starvation tick
    starvation_depletion_multiplier: number  // Multiplier applied when energy is <= 0
    obesity_death_probability: number  // Probability of death when above obesity threshold
    obesity_threshold_factor: number  // Threshold relative to max_bean_size to consider obese
    metabolism_base_burn: number  // Basal metabolism burn rate per tick (energy units).
    energy_to_fat_ratio: number  // Energy units required to store 1 unit of fat.
    fat_to_energy_ratio: number  // Energy units recovered per unit of fat burned.
    energy_max_storage: number  // Maximum circulating energy storage (not fat).
    size_penalty_min_above: number  // Minimum speed multiplier when overweight.
    size_penalty_min_below: number  // Minimum speed multiplier when underweight.
    pixels_per_unit_speed: number  // Rendering scale: pixels per unit speed.
    energy_loss_on_bounce: number  // Energy lost when bean bounces off a wall or obstacle.
    collision_base_damage: number
    collision_damage_speed_factor: number
    collision_min_damage: number
    collision_damage_size_exponent: number
    collision_damage_sex_factors: [number, number]  // (FEMALE, MALE)
}
