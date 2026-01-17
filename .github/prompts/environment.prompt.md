---
agent: agent
---
1. Environment Overview
The objective is to build a grid-based world simulation where environmental factors (Temperature, Sunlight, Humidity) are determined by a combination of time (seasons), geography (latitude), and local terrain modifiers (elevation, water).

The architecture must be Provider-based. All providers are owned by the World and instantiated by the World Factory based on a configuration file.

2. Architectural Planning

The diagram illustrates the World as the central owner, injecting providers into the Hemisphere logic hub.

[ Config File ] 
      |
      v
[ World Factory ] --(Instantiates all Providers)--> [ World ]
                                                       |
      +------------------------------------------------+
      |                |                |              |
[ Hemisphere ]   [ Season ]       [ Climate ]    [ Geography ]
 (Manager)       (Provider)       (Provider)     (Provider)
      |                ^                ^              ^
      |                |                |              |
      +----------------+----------------+--------------+
            (Hemisphere coordinates the providers)


3. Structural Hierarchy & Ownership

To facilitate side-by-side comparison of different simulation models, the World owns all provider instances.

World (Unique Wrapper): The ultimate owner. It holds:

GlobalTimeState (The Clock).

IHemisphereProvider (The Logic Hub).

ISeasonProvider (Temporal Logic).

IClimateProvider (Synthesis Logic).

IGeographyProvider (Physical Data).

World Factory: Responsible for reading config.json, instantiating the specific classes for all four providers, and assembling the World object.

Hemisphere Provider (The Logic Hub): While owned by the World, it receives references to the Season, Climate, and Geography providers. It orchestrates their interaction to resolve the climate for a specific point.

4. Detailed Configuration Schema (config.json)

{
  "simulation": {
    "id": "exp_001_standard_earth",
    "version": "1.3.0"
  },
  "time_management": {
    "days_per_year": 365,
    "hours_per_day": 24,
    "ticks_per_hour": 60,
    "initial_day": 1
  },
  "providers": {
    "hemisphere": {
      "type": "StandardDualPoleManager",
      "params": {
        "geometry": {
          "grid_width": 100,
          "grid_height": 100,
          "equator_y": 50,
          "axial_tilt": 23.5
        },
        "offsets": { "north": 0, "south": 182.5 }
      }
    },
    "season": {
      "type": "SinusoidalSeasonProvider",
      "params": { "amplitude": 1.0, "phase_shift": 0 }
    },
    "climate": {
      "type": "LatitudinalGradientProvider",
      "params": {
        "equator_temp": 30.0,
        "polar_drop": 50.0,
        "modifiers": ["altitude", "maritime"]
      }
    },
    "geography": {
      "type": "SquareGridGeography",
      "params": { "seed": "ref_123" }
    }
  }
}


5. Interfaces & Data Models

A. Value Objects (State Objects)

interface GlobalTimeState {
  dayOfYear: number;
  hourOfDay: number;
  totalTicks: number;
}

interface HemisphereState {
  latitude: number;          // Normalized -1.0 to 1.0
  isNorthern: boolean;       
  effectiveDay: number;      
}

interface SeasonState {
  solarIntensity: number;    
  seasonName: string;        
}

interface CellContext {
  x: number;
  y: number;
  elevation: number;         
  isWater: boolean;          
}

interface ClimateState {
  temperature: number;       
  sunlightIntensity: number; 
  humidity: number;          
}


B. Component & Provider Interfaces

/** * Root interface for the World Orchestrator 
 */
interface IWorld {
  time: GlobalTimeState;
  hemisphere: IHemisphereProvider;
  season: ISeasonProvider;
  climate: IClimateProvider;
  geography: IGeographyProvider;
  
  update(x: number, y: number): ClimateState;
  tick(): void;
}

/** * Swappable Logic Hub for Spatial/Temporal Coordination 
 */
interface IHemisphereProvider {
  // Dependency Injection via Init
  init(
    season: ISeasonProvider, 
    climate: IClimateProvider, 
    geo: IGeographyProvider,
    params: any
  ): void;

  resolveClimate(x: number, y: number, time: GlobalTimeState): ClimateState;
  getHemisphereState(y: number, time: GlobalTimeState): HemisphereState;
}

/** * Swappable Temporal/Orbital Logic 
 */
interface ISeasonProvider {
  init(params: any): void;
  getSeasonState(day: number, latitude: number): SeasonState;
}

/** * Swappable Climate Synthesis Engine 
 */
interface IClimateProvider {
  init(params: any): void;
  calculate(
    hemi: HemisphereState, 
    season: SeasonState, 
    ctx: CellContext
  ): ClimateState;
}

/** * Swappable Physical Data Source 
 */
interface IGeographyProvider {
  init(params: any): void;
  getTerrainAt(x: number, y: number): CellContext;
}


6. Component Definitions

Component A: World (The Owner & Master Clock)

Role: Orchestrates high-level simulation ticks and manages provider lifecycle.

Logic:

Time Management: Increments totalTicks and derives dayOfYear and hourOfDay.

Provider Management: Holds instances of all providers.

Interface: Exposes update(x, y) which calls hemisphere.resolveClimate.

Component B: Hemisphere Provider (StandardDualPoleManager)

Role: The spatial-temporal coordinator.

Logic:

Coordinate Translation: $L = (y - EquatorY) / (GridHeight / 2)$.

Temporal Inversion: If $L < 0$, adds south_offset to dayOfYear.

Data Assembly: Calls geo.getTerrainAt, season.getSeasonState, then climate.calculate.

Component C: Season Provider (SinusoidalSeasonProvider)

Role: Translates time and latitude into available solar energy.

Formula: $Intensity = (\sin(2\pi \cdot day / 365) + 1) / 2$.

Component D: Climate Provider (LatitudinalGradientProvider)

Role: Pure mathematical engine for energy-to-temperature synthesis.

Formula: $BaseTemp = EquatorTemp - (|Lat| \cdot PolarDrop)$.

Modifier Chain: Iterates through internal logic (Altitude, Maritime).

Component E: Geography Provider (SquareGridGeography)

Role: The source of truth for physical terrain.

Logic: Retrieves or generates CellContext (Elevation, Water) for (x, y).

7. Data Flow Diagram

World Factory creates SeasonA, ClimateA, GeoA, HemiA.

World Factory calls HemiA.init(SeasonA, ClimateA, GeoA, params).

World calls HemiA.resolveClimate(x, y, time).

HemiA performs the coordination chain and returns the result to World.