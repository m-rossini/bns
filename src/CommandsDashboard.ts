// CommandsDashboard module
export class CommandsDashboard {
  private gridToggleButton: HTMLButtonElement;
  private isGridVisible: boolean;
  private onToggleGrid: (visible: boolean) => void;
  private container: HTMLElement;

  constructor(container: HTMLElement, initialGridState: boolean, onToggleGrid: (visible: boolean) => void) {
    this.container = container;
    this.isGridVisible = initialGridState;
    this.onToggleGrid = onToggleGrid;
    this.gridToggleButton = document.createElement('button');
  }

  render(): void {
    this.gridToggleButton.textContent = this.isGridVisible ? 'Hide Grid' : 'Show Grid';
    this.gridToggleButton.onclick = () => {
      this.isGridVisible = !this.isGridVisible;
      this.gridToggleButton.textContent = this.isGridVisible ? 'Hide Grid' : 'Show Grid';
      this.onToggleGrid(this.isGridVisible);
    };
    this.container.appendChild(this.gridToggleButton);
  }
}
