// DynamicConfigDashboard module
export class DynamicConfigDashboard {
  private configDiv: HTMLDivElement;
  public speed: number = 1; // Set the initial speed to the minimum value

  constructor() {
    const configFrame = document.getElementById('configFrame');
    this.configDiv = document.createElement('div');
    this.configDiv.className = 'dashboard-frame config-frame';
    configFrame?.appendChild(this.configDiv);
  }

  render(): void {
    this.configDiv.innerHTML = `
      <h2>Config</h2>
      <div class='slider-container-bordered'>
        <span>Speed:</span> <input id='simSpeedSlider' type='range' min='1' max='10' value='1' /> <!-- Default value updated to minimum -->
      </div>
    `;
    const slider = this.configDiv.querySelector('#simSpeedSlider') as HTMLInputElement;
    if (slider) {
      slider.addEventListener('input', (e) => {
        this.speed = Number(slider.value);
      });
    }
  }

  collapse(): void {
    this.configDiv.style.display = 'none';
  }

  expand(): void {
    this.configDiv.style.display = '';
  }
}
