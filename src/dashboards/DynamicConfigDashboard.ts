export class DynamicConfigDashboard {
  private container: HTMLElement;
  private collapseButton: HTMLButtonElement;
  private contentWrapper: HTMLDivElement;
  private header: HTMLDivElement;
  public speed: number = 1;

  constructor() {
    this.container = document.getElementById('configFrame')!;
    
    // Create header with collapse button
    this.header = document.createElement('div');
    this.header.style.cssText = 'display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;';
    
    const title = document.createElement('h2');
    title.textContent = 'Config';
    title.style.margin = '0';
    
    this.collapseButton = document.createElement('button');
    this.collapseButton.textContent = '−';
    this.collapseButton.className = 'dashboard-collapse-btn';
    this.collapseButton.onclick = () => this.collapse();
    
    this.header.appendChild(title);
    this.header.appendChild(this.collapseButton);
    this.container.appendChild(this.header);
    
    // Create content wrapper
    this.contentWrapper = document.createElement('div');
    this.container.appendChild(this.contentWrapper);
  }

  render(): void {
    this.contentWrapper.innerHTML = `
      <div class='slider-container-bordered'>
        <span>Speed:</span> <input id='simSpeedSlider' type='range' min='1' max='10' value='1' />
      </div>
    `;
    const slider = this.contentWrapper.querySelector('#simSpeedSlider') as HTMLInputElement;
    if (slider) {
      slider.addEventListener('input', (e) => {
        this.speed = Number(slider.value);
      });
    }
  }

  collapse(): void {
    this.contentWrapper.style.display = 'none';
    this.collapseButton.textContent = '+';
    this.collapseButton.onclick = () => this.expand();
    // Collapse the container
    this.container.style.height = 'auto';
    this.container.style.minHeight = '0';
  }

  expand(): void {
    this.contentWrapper.style.display = 'block';
    this.collapseButton.textContent = '−';
    this.collapseButton.onclick = () => this.collapse();
    // Restore original height
    this.container.style.height = '';
    this.container.style.minHeight = '';
    this.render();
  }
}