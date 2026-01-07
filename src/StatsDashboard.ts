// StatsDashboard module
import { worldWindow } from './worldWindow';

export class StatsDashboard {
  private statsDiv: HTMLDivElement;

  constructor() {
    const statsFrame = document.getElementById('statsFrame');
    this.statsDiv = document.createElement('div');
    this.statsDiv.className = 'dashboard-frame stats-frame';
    statsFrame?.appendChild(this.statsDiv);
  }

  render(): void {
    const { tick, totalTime } = worldWindow.world.state;
    this.statsDiv.innerHTML = `
      <h2>Simulation Stats</h2>
      <div>Ticks: <span id="stat-tick">${tick}</span></div>
      <div>Total Time: <span id="stat-totalTime">${totalTime}</span></div>
    `;
  }

  collapse(): void {
    this.statsDiv.style.display = 'none';
  }

  expand(): void {
    this.statsDiv.style.display = '';
  }
}
