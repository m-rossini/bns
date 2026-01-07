// StatsDashboard module
import { worldWindow } from '../worldWindow';
export class StatsDashboard {
  private statsDiv: HTMLDivElement;

  constructor(container?: HTMLElement) {
    const target = container ?? document.getElementById('statsFrame');
    this.statsDiv = document.createElement('div');
    this.statsDiv.className = 'dashboard-frame stats-frame';
    target?.appendChild(this.statsDiv);
  }

  render(): void {
    const { tick, totalTime } = worldWindow.world.state;
    this.statsDiv.innerHTML = `
      <h2>Simulation Stats</h2>
      <div>Total Ticks: <span id="stat-tick">${tick}</span></div>
      <div>Total Time: <span id="stat-totalTime">${totalTime}</span></div>
    `;
  }
}
