# CommandsDashboard Pause/Unpause Toggle Implementation Plan

This plan describes how to add a pause/unpause toggle action to the CommandsDashboard, ensuring proper UX/UI, TDD, and clean git workflow for intern implementation.

---

## 1. Create a New Feature Branch
- Branch name: `feature/commands-dashboard-pause-toggle`
- Command:
  ```bash
  git checkout -b feature/commands-dashboard-pause-toggle
  ```
- **Commit after branch creation.**

---

## 2. Add Pause/Unpause Button to CommandsDashboard (UX/UI)
- **File:** `src/dashboards/CommandsDashboard.ts`
  - Add a private property: `isPaused: boolean`.
  - Add a new `pauseButton` to the dashboard UI, styled and positioned consistently with other controls.
  - Button label: "Pause" when running, "Resume" when paused.
  - Accept `onTogglePause: (paused: boolean) => void` in constructor.
  - Wire button to toggle pause state and call callback.
  - Ensure the button is visible and accessible in both collapsed and expanded states.
- **Tests:** `tests/CommandsDashboard.test.ts`
  - Test button toggles state and label.
  - Test callback is called with correct state.
  - Test button is visible and accessible in both dashboard states.
- **Commit after UI and test changes.**

---

## 3. Integrate Pause State in Simulation Logic
- **File:** `src/index.ts`
  - Add `let isPaused = false;`
  - Pass pause callback to CommandsDashboard.
  - In Phaser `update()`, skip `worldWindow.update()` if paused.
- **Tests:**
  - Add/fix tests (if possible) to verify simulation update is skipped when paused.
- **Commit after simulation and test changes.**

---

## 4. Final Review and Documentation
- Review all changes for completeness.
- Update documentation if needed (README, comments).
- **Commit after documentation and final review.**

---

**At each phase, commit before proceeding. If code changes, add or update tests before the commit. UX/UI must be fully addressed in phase 2.**
