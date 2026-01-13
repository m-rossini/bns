import { RunContext } from '../runContext';
import { UXTracker } from '../observability/uxTracker';

export class DynamicConfigDashboard {
  private container: HTMLElement;
  private collapseButton: HTMLButtonElement;
  private contentWrapper: HTMLDivElement;
  private header: HTMLDivElement;
  public speed: number = 1;
  private runContext?: RunContext;

  constructor(runContext?: RunContext) {
    this.container = document.getElementById('configFrame')!;
    this.runContext = runContext;
    
    // Create header with collapse button
    this.header = document.createElement('div');
    this.header.style.cssText = 'display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 10px;';
    
    const title = document.createElement('h2');
    title.textContent = 'Config';
    title.style.margin = '0';
    title.style.writingMode = 'vertical-rl';
    title.style.transform = 'rotate(180deg)';
    title.style.display = 'none'; // Hidden initially
    title.style.marginTop = '20px'; // Space below button when collapsed
    
    this.collapseButton = document.createElement('button');
    this.collapseButton.textContent = '◀';
    this.collapseButton.className = 'dashboard-collapse-btn';
    this.collapseButton.onclick = () => this.collapse();
    
    this.header.appendChild(this.collapseButton);
    this.header.appendChild(title);
    this.container.appendChild(this.header);
    
    // Create content wrapper
    this.contentWrapper = document.createElement('div');
    this.container.appendChild(this.contentWrapper);
  }

  render(): void {
    this.contentWrapper.innerHTML = `
      <h2>Config</h2>
      <div class='slider-container-bordered'>
        <span>Speed:</span> <input id='simSpeedSlider' type='range' min='1' max='10' value='1' />
      </div>
    `;
    const slider = this.contentWrapper.querySelector('#simSpeedSlider') as HTMLInputElement;
    if (slider) {
      slider.addEventListener('input', (e) => {
        this.speed = Number(slider.value);
        // Debounced: let UXTracker handle debouncing for high-frequency events
        this.runContext?.getTracker(UXTracker).track('speed_change', { component: 'DynamicConfigDashboard', speed: this.speed }, true);
      });
    }
  }

  collapse(): void {
    this.contentWrapper.style.display = 'none';
    this.collapseButton.textContent = '▶';
    this.collapseButton.onclick = () => this.expand();
    // Collapse horizontally
    this.container.style.width = '50px';
    this.container.style.padding = '16px 8px';
    this.header.style.flexDirection = 'column';
    this.header.style.alignItems = 'center';
    this.header.style.justifyContent = 'flex-start';
    this.header.style.height = '100%';
    const title = this.header.querySelector('h2');
    if (title) {
      (title as HTMLElement).style.display = 'block';
      (title as HTMLElement).style.flex = '1';
      (title as HTMLElement).style.display = 'flex';
      (title as HTMLElement).style.alignItems = 'center';
      (title as HTMLElement).style.justifyContent = 'center';
    }
    this.runContext?.getTracker(UXTracker).track('config_collapse', { component: 'DynamicConfigDashboard' });
  }

  expand(): void {
    this.contentWrapper.style.display = 'block';
    this.collapseButton.textContent = '◀';
    this.collapseButton.onclick = () => this.collapse();
    // Restore original width
    this.container.style.width = '';
    this.container.style.padding = '';
    this.header.style.flexDirection = '';
    this.header.style.alignItems = '';
    this.header.style.justifyContent = '';
    this.header.style.height = '';
    const title = this.header.querySelector('h2');
    if (title) {
      (title as HTMLElement).style.display = 'none';
      (title as HTMLElement).style.flex = '';
      (title as HTMLElement).style.alignItems = '';
      (title as HTMLElement).style.justifyContent = '';
    }
    this.render();
    this.runContext?.getTracker(UXTracker).track('config_expand', { component: 'DynamicConfigDashboard' });
  }
}