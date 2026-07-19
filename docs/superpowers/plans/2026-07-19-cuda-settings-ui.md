# CUDA Settings UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose the persistent CUDA pipeline controls in the Settings view without making the safe single-GPU-worker constraint configurable.

**Architecture:** Extend the typed settings contract with the backend's CUDA tuning values. Keep the existing settings form and `SettingField` component, add a responsive CUDA panel visible only for CUDA-capable images, and verify the CPU and CUDA presentation through the existing Vitest app test.

**Tech Stack:** React, TypeScript, Vitest, Testing Library, existing CSS design tokens.

## Global Constraints

- Keep the first release on a trusted LAN without authentication.
- Use German, user-facing explanations with stable backend setting keys.
- Do not change unrelated job-monitor behavior; retain the hanging-job fixes already in this branch.
- Run the focused frontend test and `python scripts/verify.py` before completion.

### Task 1: Type and test fixtures

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/app/App.test.tsx`

- [ ] Add `cpu_workers`, `gpu_workers`, `gpu_batch_size`, and `gpu_queue_size` to `AppSettings.analysis` using the backend's numeric value types.
- [ ] Add those values to the settings fixture so the existing app test represents the complete API response.

### Task 2: Settings presentation

**Files:**
- Modify: `frontend/src/features/settings/SettingsView.tsx`
- Modify: `frontend/src/styles/global.css`

- [ ] Rename the generic worker control to `CPU-Worker` and explain that it controls parallel CPU analysis.
- [ ] Add a CUDA tuning panel shown only when `capabilities.available_compute` contains `cuda`, with a disabled `GPU-Worker` value of 1, a batch-size select for 1/2/4/8, and a queue-size number input from 1 to 256.
- [ ] Use the existing source metadata to disable environment-managed fields and retain the existing form save path.
- [ ] Add responsive styling that visually separates CUDA tuning while matching the existing dark panel and form grid.

### Task 3: Verification and delivery

**Files:**
- No additional source files.

- [ ] Run the focused Settings/App Vitest test.
- [ ] Run the full `python scripts/verify.py` gate.
- [ ] Confirm the hanging-job UI commit remains in the branch and dispatch the CUDA dev-image workflow from the final branch commit.
- [ ] Create and merge the PR, fast-forward the local main worktree, and remove the feature worktree.
