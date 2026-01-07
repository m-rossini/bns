// SimulationStatsDashboard module
export class SimulationStatsDashboard {
  private statsDiv: HTMLDivElement;

  constructor() {
    const statsFrame = document.getElementById('statsFrame');
    this.statsDiv = document.createElement('div');
    this.statsDiv.className = 'dashboard-frame stats-frame';
    statsFrame?.appendChild(this.statsDiv);
  }

  render(): void {
    this.statsDiv.innerHTML = `
      <h2>Simulation Stats</h2>
      <div>Grid lines: enabled</div>
    `;
  }
}
