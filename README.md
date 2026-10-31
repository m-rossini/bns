# Bean World Simulation - Project Documentation

## Overview

The Bean World simulation is a **pause-aware 2D simulation** where beans live in a bounded arena with **day/night cycles, seasons, and dynamic weather systems**. The project emphasizes a **clean separation between domain logic and physical presentation**, with a **pure-Python configuration system** and **dependency injection** for flexibility.

## 🚀 Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/m-rossini/bns.git

# Set up development environment
make venv
make install
```

### Running the Simulation
```bash
# Headless mode (for testing and CI)
BEAN_HEADLESS=1 python -m sim.main

# Windowed mode (for local development)
python -m sim.main
```

### Documentation
- **Architecture**: `CLAUDE.md` - Complete project architecture and technical details
- **Agent Documentation**: `AGENTS.md` - Detailed agent roles and responsibilities
- **API Reference**: `sim/` directory - Complete API documentation

## 🏗️ **PROJECT STRUCTURE**

```
sim/
├── config.py                    # Unified configuration module
├── components.py               # Data components (GameState, GameClock, etc.)
├── container.py                 # DI container wiring
├── domain/                      # Core domain logic
│   ├── calendar.py            # Calendar system
│   ├── environment.py         # Environment aggregator
│   ├── session.py             # GameSession
│   └── world.py              # World definition
├── implementations/            # Strategy implementations
│   ├── daynight/              # DayNightStrategy
│   ├── season/               # SeasonStrategy  
│   └── weather/             # WeatherStrategy
├── interfaces/                # Protocol definitions
│   ├── environment.py        # ISeasonStrategy, IDayNightStrategy, IWeatherStrategy
│   └── world.py             # IWorld
├── input/                     # Input handling
│   └── keyboard.py           → KeyboardInput
├── rendering/                 # Visualization
│   └── arcade_view.py        → ArcadeView with sidebar layout
└── main.py                   → Entry point
```

## ⚙️ **CONFIGURATION**

The Bean World simulation uses **pure-Python dataclasses** for configuration. All tunable values are defined in a single module (`sim/config.py`).

### Key Configuration Areas

#### World Configuration
```python
WorldConfig(
    width: float = 1200.0           # World dimensions
    height: float = 800.0          # World dimensions
    cell_size: float = 50.0        # Cell size for weather/environment sampling
    orientation: str = "north_south"
    wrap_around: bool = False
)
```

#### Season Configuration
```python
SeasonConfig(
    name: str = "Spring"                     # Season name
    ground_color: Color = (96, 170, 88)      # Ground color
    detail_colors: List[Color] = []         # Ground details
    base_temperature: float = 14.0           # Seasonal mean temperature
    temperature_swing: float = 7.0           # Day/night temperature variation
    humidity: float = 0.55                   # Seasonal baseline humidity
    pressure_hpa: float = 1013.0             # Seasonal baseline pressure
    weather_weights: Dict[str, float] = {}   # Weather weights for this season
)
```

#### Weather Configuration
```python
WeatherConfig(
    change_interval: int = 600              # Ticks between weather system updates
    seed: int = 1337                        # Random seed for deterministic weather
    front_count: int = 3                    # Number of moving weather fronts
    background_coverage: float = 0.6        # Fraction of cells under background weather
    conditions: Tuple[str, ...] = ("clear", "cloudy", "rain", "storm", "snow")
)
```

#### Environment Configuration
```python
EnvironmentConfig(
    weather_strategy: Optional[str] = None    # Weather strategy class name
    season_strategy: Optional[str] = None    # Season strategy class name
    daynight_strategy: Optional[str] = None  # Day/night strategy class name
)
```

### Default Configuration

```python
DEFAULT_CONFIG = SimulationConfig(
    world=WorldConfig(
        width=1200.0,
        height=800.0,
        cell_size=50.0,
        orientation="north_south",
        wrap_around=False,
    ),
    time=TimeConfig(
        ticks_per_day=1200,
        ticks_per_season=4800,
    ),
    seasons=[
        SeasonConfig(
            name="Spring",
            ground_color=(96, 170, 88),
            detail_colors=[(250, 246, 180), (248, 186, 214), (232, 248, 236)],
            base_temperature=14.0,
            temperature_swing=7.0,
            humidity=0.55,
            pressure_hpa=1012.0,
            weather_weights={
                "clear": 30, "cloudy": 30, "rain": 30, "storm": 10, "snow": 0,
            },
        ),
        SeasonConfig(
            name="Summer",
            ground_color=(68, 146, 72),
            detail_colors=[(52, 122, 58), (92, 168, 84), (38, 110, 54)],\n            base_temperature=25.0,
            temperature_swing=6.0,
            humidity=0.40,
            pressure_hpa=1015.0,
            weather_weights={
                "clear": 50, "cloudy": 25, "rain": 17, "storm": 8, "snow": 0,
            },
        ),
        SeasonConfig(
            name="Autumn",
            ground_color=(178, 128, 62),
            detail_colors=[(214, 124, 52), (166, 92, 42), (206, 168, 70)],
            base_temperature=13.0,
            temperature_swing=7.0,
            humidity=0.60,
            pressure_hpa=1010.0,
            weather_weights={
                "clear": 30, "cloudy": 35, "rain": 25, "storm": 10, "snow": 0,
            },
        ),
        SeasonConfig(
            name="Winter",
            ground_color=(222, 230, 236),
            detail_colors=[(246, 250, 255), (206, 222, 238), (232, 240, 248)],
            base_temperature=3.0,
            temperature_swing=5.0,
            humidity=0.70,
            pressure_hpa=1008.0,
            weather_weights={
                "clear": 25, "cloudy": 35, "rain": 0, "storm": 5, "snow": 35,
            },
        ),
    ],
    daynight=DayNightConfig(
        sun_speed=1.0,
        moon_speed=1.0,
        moon_phase_offset=0.25,
    ),
    weather=WeatherConfig(
        change_interval=600,
        seed=1337,
        front_count=3,
    ),
    environment=EnvironmentConfig(
        weather_strategy="WeatherStrategy",
        season_strategy="SeasonStrategy",
        daynight_strategy="DayNightStrategy",
    ),
    debug=False,
    tick_rate=30.0,
)
```

## 📚 **USAGE EXAMPLES**

### Basic Usage
```python
from sim.container import Container
from sim.config import DEFAULT_CONFIG

# Create the simulation container
container = Container(DEFAULT_CONFIG)

# Access core components
session = container.session
environment = container.environment
world = container.world
calendar = container.calendar

# Check current state
print(f"Season: {environment.season}")
print(f"Time: {calendar.clock}")
print(f"Weather: {environment.weather}")
```

### Custom Configuration
```python
from sim.config import SimulationConfig, WorldConfig, SeasonConfig, WeatherConfig

# Create custom configuration
custom_config = SimulationConfig(
    world=WorldConfig(
        width=800.0,
        height=600.0,
        cell_size=40.ikein310.09:53
    ),
    seasons=[
        SeasonConfig(
            name="Tropical Summer",
            ground_color=(60, 140, 80),
            base_temperature=28.0,
            temperature_swing=5.0,
            humidity=0.75,
            pressure_hpa=1015.0,
            weather_weights={
                "clear": 80, "cloudy": 15, "rain": 5, "storm": 0, "snow": 0,
            },
        ),
    ],\n    # ... other configurations
)
```

### Running the Simulation
```bash
# Headless mode (for testing and CI)
BEAN_HEADLESS=1 python -m sim.main

# Windowed mode (for local development)
python -m sim.main
```

## 📚 **DEVELOPMENT GUIDELINES**

### Adding New Seasons
```python
# Add a new season to DEFAULT_CONFIG.seasons
DEFAULT_CONFIG.seasons.append(
    SeasonConfig(
        name="Desert",
        ground_color=(240, 220, 100),
        base_temperature=35.0,
        temperature_swing=10.0,
        humidity=0.20,
        pressure_hpa=1005.0,
        weather_weights={
            "clear": 80, "cloudy": 15, "rain": 5, "storm": 0, "snow": 0,
        },
    )
)
```

### Custom Weather Systems
```python
# Create custom weather configuration
custom_weather = WeatherConfig(
    change_interval=300,           # Update every 10 seconds
    seed=12345,                    # Different random seed
    front_count=5,                 # More weather systems
    background_coverage=0.8,       # Most cells affected by background weather
)

# Use in custom config
custom_config = SimulationConfig(
    weather=custom_weather,
    # ... other settings
)
```

### Performance Optimization
```python
# For high-performance systems
high_perf_config = SimulationConfig(
    world=WorldConfig(
        cell_size=80.0,           # Larger cells = fewer calculations
        width=1600.0,            # Larger world
        height=900.0,           # Larger world
    ),
    weather=WeatherConfig(
        front_count=2,           # Fewer weather systems
        change_interval=600,     # Less frequent updates
    ),
    # ... other optimizations
)
```

## 📖 **REFERENCES**

### Documentation
- **Project Architecture**: This README.md - High-level project overview
- **Technical Details**: `CLAUDE.md` - Detailed technical specifications
- **Agent Documentation**: `AGENTS.md` - Agent roles and interactions
- **API Reference**: `sim/interfaces/` - Complete protocol definitions

### Code Examples
- **Configuration Examples**: This README.md - Practical usage patterns
- **Implementation Details**: `sim/` directory - Complete source code
- **Testing**: `tests/` directory - Automated tests

### Development Tools
- **Code Quality**: `Makefile` - Build and test automation
- **Containerization**: `Containerfile` - Docker deployment
- **Documentation**: `spec.md` - Technical specification document

---

## 🎯 **PROJECT STATUS**

The Bean World simulation project is **complete and ready for production**:

### ✅ **Requirements Implemented**
- [x] Configuration consolidation
- [x] Season strategy controls season names
- [x] Per-cell weather systems
- [x] P pause/resume functionality
- [x] Atmospheric pressure included
- [x] Day & season bars separate
- [x] HUD layout fixed
- [x] Weather_at_cell functionality resolved
- [x] All documentation provided

### 📊 **Key Features**
- **Pure-Python configuration**: No external dependencies
- **Modular architecture**: Clean separation of concerns
- **Flexible system**: Configurable behavior and parameters
- **Performance optimized**: Efficient simulation with minimal overhead
- **Well documented**: Comprehensive documentation and examples

### 🛠️ **Technical Excellence**
- **Type Safety**: Complete type annotations
- **Error Handling**: Robust exception management
- **Documentation**: Comprehensive API references
- **Testing**: Extensive test coverage
- **Code Quality**: Adherence to best practices

### 🎯 **GETTING STARTED**

#### Quick Start
```bash
# Clone the project
 git clone https://github.com/m-rossini/bns.git

# Set up environment
 make venv
 make install

# Run the simulation
 make run
```

#### Development
```bash
# Run tests
 pytest tests/

# Code quality checks
 black sim/
 isort sim/
 mypy sim/
```

---

## 📝 **ACKNOWLEDGMENTS**

The Bean World simulation refactoring was a collaborative effort involving:
- **Architecture design**: System design and component separation
- **Implementation**: Core logic and strategy implementations
- **Documentation**: Comprehensive API documentation
- **Testing**: Verification and validation of all features
- **Integration**: End-to -to-end system testing

This project represents a significant milestone in the Bean World simulation development, providing a robust, configurable, and maintainable codebase for future enhancements.

---

**🏆 PROJECT STATUS: READY FOR PRODUCTION**

The Bean World simulation is now a **production-ready** system with:
- ✅ All requirements implemented
- ✅ Comprehensive documentation
- **Code quality maintained**
- ✅ Testing coverage
- ✅ Configuration consolidation
- ✅ Architecture improvements

**The simulation is now ready for deployment and further development!** 🚀