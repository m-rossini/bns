// StatsDashboard module
export class StatsDashboard {
  private statsDiv: HTMLDivElement;

  constructor(container?: HTMLElement) {
    const target = container ?? document.getElementById('statsFrame');
    this.statsDiv = document.createElement('div');
    this.statsDiv.className = 'dashboard-frame stats-frame';
    target?.appendChild(this.statsDiv);
  }

  render(): void {
    this.statsDiv.innerHTML = `
      <h2>Stats</h2>
      <div>Simulation running...</div>
    `;
  }
}
