import '@testing-library/jest-dom/vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Capability, CapabilityFieldset, Inspector, mergeActionCapabilities } from './ui';

describe('accessible domain primitives', () => {
  it('moves focus into and back from the responsive inspector', async () => {
    const user = userEvent.setup();
    render(
      <Inspector title="Validation inspector" trigger={<button>Open inspector</button>}>
        <p>Immutable failure evidence</p>
      </Inspector>,
    );
    const trigger = screen.getByRole('button', { name: 'Open inspector' });
    await user.click(trigger);
    expect(screen.getByRole('dialog', { name: 'Validation inspector' })).toBeVisible();
    await user.keyboard('{Escape}');
    expect(trigger).toHaveFocus();
  });

  it('exposes server-denied capability detail without enabling the action', () => {
    render(
      <Capability
        item={{
          action: 'run_holdout',
          visibility: 'SHOW',
          allowed: false,
          reason_code: 'HOLDOUT_LOCKED',
          reason_detail: 'Protected until approval.',
          requires_confirmation: true,
          idempotency_required: true,
          if_match_required: true,
          result_mode: 'JOB',
          danger_level: 'IRREVERSIBLE',
        }}
      />,
    );
    expect(screen.getByTestId('capability-action-run_holdout')).toBeDisabled();
    expect(screen.getByTestId('capability-action-run_holdout')).toHaveAttribute(
      'title',
      'Protected until approval.',
    );
  });

  it('never enables a visible capability without an executable handler', () => {
    render(
      <Capability
        item={{
          action: 'future_action',
          visibility: 'SHOW',
          allowed: true,
          reason_code: null,
          reason_detail: null,
          requires_confirmation: false,
          idempotency_required: false,
          if_match_required: false,
          result_mode: 'IMMEDIATE',
          danger_level: 'NORMAL',
        }}
      />,
    );
    expect(screen.getByRole('button', { name: 'future_action' })).toBeDisabled();
  });

  it('renders SHOW capability inputs with server allowed controlling enabled state', () => {
    const capability = {
      action: 'run_fast_backtest',
      visibility: 'SHOW',
      allowed: false,
      reason_code: 'STRATEGY_NOT_FROZEN',
      reason_detail: 'Freeze the strategy first.',
      requires_confirmation: false,
      idempotency_required: true,
      if_match_required: false,
      result_mode: 'JOB',
      danger_level: 'NORMAL',
    } as const;
    const { rerender } = render(
      <CapabilityFieldset item={capability} legend="Fast backtest inputs">
        <label>
          Snapshot ID
          <input />
        </label>
      </CapabilityFieldset>,
    );
    expect(screen.getByLabelText('Snapshot ID')).toBeDisabled();
    expect(screen.getByText('Freeze the strategy first.')).toBeVisible();

    rerender(
      <CapabilityFieldset item={{ ...capability, allowed: true }} legend="Fast backtest inputs">
        <label>
          Snapshot ID
          <input />
        </label>
      </CapabilityFieldset>,
    );
    expect(screen.getByLabelText('Snapshot ID')).toBeEnabled();
  });

  it('does not render inputs for a HIDE capability', () => {
    render(
      <CapabilityFieldset
        item={{
          action: 'start_validation',
          visibility: 'HIDE',
          allowed: true,
          reason_code: null,
          reason_detail: null,
          requires_confirmation: false,
          idempotency_required: true,
          if_match_required: false,
          result_mode: 'JOB',
          danger_level: 'NORMAL',
        }}
        legend="Strict validation inputs"
      >
        <input aria-label="Validation policy ID" />
      </CapabilityFieldset>,
    );
    expect(screen.queryByLabelText('Validation policy ID')).not.toBeInTheDocument();
  });

  it('requires capability-declared confirmation before invoking a handler', async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    render(
      <Capability
        item={{
          action: 'freeze',
          visibility: 'SHOW',
          allowed: true,
          reason_code: null,
          reason_detail: null,
          requires_confirmation: true,
          idempotency_required: true,
          if_match_required: true,
          result_mode: 'IMMEDIATE',
          danger_level: 'STATE_CHANGE',
        }}
        onClick={handler}
      />,
    );
    const trigger = screen.getByTestId('capability-action-freeze');
    expect(trigger).toHaveAccessibleName(/冻结策略|Freeze strategy/);
    expect(trigger).toHaveAttribute('data-requires-confirmation', 'true');
    await user.click(trigger);
    expect(handler).not.toHaveBeenCalled();
    await user.click(screen.getByTestId('capability-confirm-freeze'));
    expect(handler).toHaveBeenCalledOnce();
  });

  it('executes directly when the server capability does not require confirmation', async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    render(
      <Capability
        item={{
          action: 'start',
          visibility: 'SHOW',
          allowed: true,
          reason_code: null,
          reason_detail: null,
          requires_confirmation: false,
          idempotency_required: true,
          if_match_required: true,
          result_mode: 'JOB',
          danger_level: 'STATE_CHANGE',
        }}
        onClick={handler}
      />,
    );
    const trigger = screen.getByTestId('capability-action-start');
    expect(trigger).toHaveAttribute('data-requires-confirmation', 'false');
    await user.click(trigger);
    expect(handler).toHaveBeenCalledOnce();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('deduplicates capabilities by action with the specialized server projection authoritative', () => {
    const detailCapability = {
      action: 'run_holdout',
      visibility: 'SHOW',
      allowed: true,
      reason_code: null,
      reason_detail: null,
      requires_confirmation: true,
      idempotency_required: true,
      if_match_required: true,
      result_mode: 'JOB',
      danger_level: 'IRREVERSIBLE',
    } as const;
    const gateCapability = {
      ...detailCapability,
      allowed: false,
      reason_code: 'HOLDOUT_APPROVAL_REQUIRED',
      reason_detail: 'Owner approval is required.',
    } as const;
    const merged = mergeActionCapabilities(
      [detailCapability, { ...detailCapability, action: 'request_holdout_approval' }],
      [gateCapability],
    );
    expect(merged.map(({ action }) => action)).toEqual(['run_holdout', 'request_holdout_approval']);
    expect(merged[0]).toBe(gateCapability);
  });
});
