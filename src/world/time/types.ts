export interface ITimeKeeper {
  /**
   * Increments the internal simulation ticks.
   */
  tick(): void;

  /**
   * Returns the absolute number of ticks since simulation start.
   */
  getTicks(): number;

  /**
   * Returns a normalized value [0.0, 1.0) representing the progress within the current year.
   */
  getYearProgress(): number;

  /**
   * Returns the count of full years passed.
   */
  getTotalYears(): number;

  /**
   * Returns the configured ticks per year.
   */
  getTicksPerYear(): number;
}
