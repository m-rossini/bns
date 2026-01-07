// CommandsDashboard module
export class CommandsDashboard {
  private gridToggleButton: HTMLButtonElement;
  private isGridVisible: boolean;
  private onToggleGrid: (visible: boolean) => void;
  private container: HTMLElement;

  constructor(initialGridState: boolean, onToggleGrid: (visible: boolean) => void) {
    const actionsFrame = document.getElementById('actionsFrame');
    this.container = actionsFrame!;
    this.isGridVisible = initialGridState;
    this.onToggleGrid = onToggleGrid;
    this.gridToggleButton = document.getElementById('toggleGridBtn') as HTMLButtonElement;
    if (!this.gridToggleButton) {
      this.gridToggleButton = document.createElement('button');
      this.gridToggleButton.id = 'toggleGridBtn';
      this.container.appendChild(this.gridToggleButton);
    }
  }

  render(): void {
    this.gridToggleButton.textContent = this.isGridVisible ? 'Hide Grid' : 'Show Grid';
    this.gridToggleButton.onclick = () => {
      this.isGridVisible = !this.isGridVisible;
      this.gridToggleButton.textContent = this.isGridVisible ? 'Hide Grid' : 'Show Grid';
      this.onToggleGrid(this.isGridVisible);
    };
    // Only append if we created a new button (handled above)
  }
}
